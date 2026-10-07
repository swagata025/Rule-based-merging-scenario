import argparse
import csv
import os
import sys

# Compute paths relative to project root
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "merge.config.xml")

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

# Ensure SUMO_HOME binaries and tools are in PATH and sys.path if specified
sumo_home = os.environ.get("SUMO_HOME")
if sumo_home and os.path.isdir(sumo_home):
    tools = os.path.join(sumo_home, "tools")
    bin_dir = os.path.join(sumo_home, "bin")
    if tools not in sys.path:
        sys.path.append(tools)
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

import traci

from real_comm.agent import VehicleAgent
from real_comm.infrastructure import InfrastructureCoordinator
from real_comm.channel import Channel

DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz, paper: "low frequency" vs 10 Hz control)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe

LOG_HEADER = ["t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
              "seq", "pred", "failsafe", "pred_age", "v_m_known"]


# def save_log(log, log_path):
#     with open(log_path, "w", newline="") as f:
#         w = csv.writer(f)
#         w.writerow(LOG_HEADER)
#         w.writerows(log)
#     print(f"Log saved to {log_path} ({len(log)} rows)")


def run(gui=True, sim_time=None, log_path=None, config_path=None,
        loss=0.0, delay=0.0, jitter=0.0, seed=1):
    cfg = config_path or os.environ.get("SUMO_CONFIG_PATH") or DEFAULT_CONFIG
    if not os.path.isabs(cfg):
        cfg = os.path.normpath(os.path.join(PROJECT_ROOT, cfg))

    if not os.path.isfile(cfg):
        raise FileNotFoundError(f"SUMO config file not found: {cfg}")

    sumo_binary = "sumo-gui" if gui else "sumo"
    traci.start([sumo_binary, "-c", cfg, "--step-length", str(DT),
                 "--no-warnings", "true"] + (["--start", "--quit-on-end"] if gui else []))

    ramp_len = traci.lane.getLength("ramp_in_0")
    coordinator = InfrastructureCoordinator(ramp_len=ramp_len)

    # One channel per link, each with its own random stream (separate seeds).
    # loss=0, delay=0, jitter=0 reproduces the perfect-communication behaviour.
    v2i = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed)       # vehicle -> RSU
    i2v = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed + 1)   # RSU -> vehicle
    v2v = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed + 2)   # vehicle -> vehicle

    agents = {}
    collisions = 0
    log = []
    sort_steps = int(round(SORT_PERIOD / DT))

    step = 0
    t = 0.0
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
            traci.simulationStep()
            step += 1
            t = traci.simulation.getTime()
            collisions += traci.simulation.getCollidingVehiclesNumber()

            # ---- 1. read own state (local sensors, perfect) and SEND messages ---------------
            states = {}
            for vid in traci.vehicle.getIDList():
                if vid not in agents:
                    agents[vid] = VehicleAgent(vid, DT)
                    traci.vehicle.setSpeedMode(vid, 0)      # obey our speed command (only 'safe speed' kept)
                ag = agents[vid]
                st = ag.update_state()
                states[vid] = st

                # V2I uplink: keep reporting every step until the first downlink arrives (= implicit ack)
                if st["lane"] in ("main", "ramp") and not ag.sequenced:
                    v2i.send({"id": vid, "lane": st["lane"], "speed": st["speed"],
                              "dist": st["dist_to_merge"], "ts": t}, t)

            # V2V beacons: the predecessor's state is sent to the follower that needs it.
            for vid, ag in agents.items():
                p = states.get(ag.pred_id) if ag.pred_id else None
                if p:
                    v2v.send({"to": vid, "from": ag.pred_id, "ts": t, "speed": p["speed"],
                              "dist_to_merge": p["dist_to_merge"], "length": p["length"]}, t)

            # ---- 2. clean up vehicles that left the network ----------------------------------
            for vid in traci.simulation.getArrivedIDList():
                agents.pop(vid, None)
                states.pop(vid, None)
                coordinator.remove_vehicle(vid)

            # ---- 2b. DELIVER messages whose delivery time has arrived ------------------------
            # (the 'in agents' checks stop a late packet from reviving a vehicle that already left)
            for m in v2i.receive(t):
                if m["id"] in agents:
                    coordinator.receive_vehicle_data(m["id"], m["lane"], m["speed"], m["dist"], m["ts"])
            for m in i2v.receive(t):
                if m["to"] in agents:
                    agents[m["to"]].on_downlink(m)
            for m in v2v.receive(t):
                if m["to"] in agents:
                    agents[m["to"]].on_v2v(m)

            # ---- 3. low-frequency sequencing, then broadcast the result over I2V -------------
            if step % sort_steps == 0:
                coordinator.run_sorting_algorithm(t)
                for m in coordinator.downlink_messages(t):
                    i2v.send(m, t)

            # ---- 4. 10 Hz longitudinal control: each vehicle uses ONLY what it knows ---------
            for vid, ego in states.items():
                ag = agents[vid]
                pred_id = ag.pred_id                      # as last told by the RSU
                pred = ag.predecessor_estimate(t)         # last V2V snapshot, extrapolated; None if missing/stale
                pred_age = (t - ag.pred_msg["ts"]) if ag.pred_msg else float("nan")

                # Physical leader from onboard radar: stays perfect, it is the safety net
                leader = None
                info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
                if info:
                    lid, gap = info
                    if lid in states:
                        leader = {"speed": states[lid]["speed"], "gap": gap}

                ctrl = ag.controller                      # each vehicle owns its controller
                if ctrl.failsafe_active(ego, leader):
                    # paper: consensus control is deactivated, internal car-following takes over
                    traci.vehicle.setSpeedMode(vid, 31)
                    traci.vehicle.setSpeed(vid, -1)
                    ctrl.prev_a = ego["accel"]
                    a_cmd = float("nan")
                else:
                    a_cmd = ctrl.compute_acceleration(ego, pred, ag.v_m)   # ag.v_m = last RECEIVED v_m
                    traci.vehicle.setSpeedMode(vid, 1)
                    traci.vehicle.setSpeed(vid, max(0.0, ego["speed"] + a_cmd * DT))

                log.append((round(t, 1), vid, ego["origin"], ego["lane"], round(ego["dist_to_merge"], 2),
                            round(ego["speed"], 3), round(ego["accel"], 3), a_cmd,
                            coordinator.get_sequence_id(vid), pred_id, int(ctrl.failsafe),
                            round(pred_age, 2), round(ag.v_m, 2)))

                if step % 20 == 0:
                    d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                    print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                          f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}, age={pred_age:.2f}) "
                          f"a={a_cmd:5.2f} v_m={ag.v_m:.1f}")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        # Runs on normal end, Ctrl+C, or a crash: always close SUMO quietly and save the log.
        try:
            traci.close()
        except Exception:
            pass      # SUMO may already be gone (it receives the same Ctrl+C)

        print(f"\nDone. t={t:.0f}s  collisions={collisions}")
        for name, ch in (("v2i", v2i), ("i2v", i2v), ("v2v", v2v)):
            rate = ch.dropped / ch.sent if ch.sent else 0.0
            print(f"  {name}: sent={ch.sent} dropped={ch.dropped} ({rate:.1%})")

        # if log_path:
        #     save_log(log, log_path)

    return collisions


if __name__ == "__main__":
    env_gui = os.environ.get("SUMO_GUI", "true").lower() in ("true", "1", "yes")
    env_time = os.environ.get("SIM_TIME")
    default_time = float(env_time) if env_time else None
    default_log = os.environ.get("SIM_LOG_PATH", os.path.join(PROJECT_ROOT, "sim_log.csv"))

    ap = argparse.ArgumentParser(description="Run CAV cooperative merge simulation.")
    ap.add_argument("--nogui", action="store_true", help="run headless (much faster)")
    ap.add_argument("--gui", action="store_true", help="force run with GUI")
    ap.add_argument("--time", type=float, default=default_time, help="stop after this many sim seconds")
    ap.add_argument("--config", type=str, default=None, help="path to custom SUMO config file")
    ap.add_argument("--log", default=default_log, help="CSV output log path")
    ap.add_argument("--loss", type=float, default=0.0, help="packet loss probability per message (0-1)")
    ap.add_argument("--delay", type=float, default=0.0, help="base one-way delay [s]")
    ap.add_argument("--jitter", type=float, default=0.0, help="extra uniform random delay up to this [s]")
    ap.add_argument("--seed", type=int, default=1, help="base RNG seed for the channels")
    args = ap.parse_args()

    use_gui = True if args.gui else (False if args.nogui else env_gui)
    run(gui=use_gui, sim_time=args.time, log_path=args.log, config_path=args.config,
        loss=args.loss, delay=args.delay, jitter=args.jitter, seed=args.seed)
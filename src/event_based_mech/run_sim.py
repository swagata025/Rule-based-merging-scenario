import argparse
import csv
import os
import sys

import traci

from agent import VehicleAgent
from infrastructure import InfrastructureCoordinator
from controller import LongitudinalController

HERE = os.path.dirname(os.path.abspath(__file__))
DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe

# ---- Event-Based V2V Default Thresholds ----
DEFAULT_V_TH = 0.3         # [m/s] speed change threshold to trigger V2V packet
DEFAULT_D_TH = 0.5         # [m]   position drift threshold to trigger V2V packet
DEFAULT_MAX_SILENCE = 1.0  # [s]   maximum time between V2V heartbeat packets


def run(gui=True, sim_time=None, log_path=None, v_th=DEFAULT_V_TH, d_th=DEFAULT_D_TH,
        max_silence=DEFAULT_MAX_SILENCE, dead_reckoning=True):
    local_cfg = os.path.join(HERE, "config", "merge.config.xml")
    fallback_cfg = r"C:\Users\Swagata\OneDrive\Desktop\documents\minor-sem5-project\config\merge.config.xml"
    cfg = local_cfg if os.path.exists(local_cfg) else fallback_cfg

    traci.start(["sumo-gui" if gui else "sumo", "-c", cfg, "--step-length", str(DT),
                 "--no-warnings", "true"] + (["--start", "--quit-on-end"] if gui else []))

    ramp_len = traci.lane.getLength("ramp_in_0")
    coordinator = InfrastructureCoordinator(ramp_len=ramp_len)
    controller = LongitudinalController(dt=DT)
    agents = {}
    collisions = 0
    log = []
    sort_steps = int(round(SORT_PERIOD / DT))

    # Communication statistics counters
    total_possible_v2v = 0
    total_sent_v2v = 0

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
        traci.simulationStep()
        step += 1
        t = traci.simulation.getTime()
        collisions += traci.simulation.getCollidingVehiclesNumber()

        # ---- 1. Every vehicle reads its onboard state (10 Hz) & evaluates V2V Event Trigger ----
        states = {}          # True local onboard states (only accessible by the ego vehicle itself)
        v2v_tx_flags = {}    # Did vehicle `vid` broadcast a V2V packet at this step? (1 or 0)

        for vid in traci.vehicle.getIDList():
            if vid not in agents:
                agents[vid] = VehicleAgent(vid)
                traci.vehicle.setSpeedMode(vid, 1)      # obey our speed command (only 'safe speed' kept)
            ag = agents[vid]
            st = ag.update_state()
            states[vid] = st

            # Check Event-Based V2V Trigger: only updates `ag.last_broadcast_state` if event occurs!
            triggered = ag.check_and_broadcast_v2v(
                current_time=t, current_state=st,
                v_th=v_th, d_th=d_th, max_silence=max_silence
            )
            v2v_tx_flags[vid] = int(triggered)
            total_possible_v2v += 1
            if triggered:
                total_sent_v2v += 1

            # V2I Uplink (for unsequenced vehicles on main or ramp)
            if st["lane"] in ("main", "ramp"):
                coordinator.receive_vehicle_data(vid, st["lane"], st["speed"], st["dist_to_merge"],
                                                 t, first_contact=not ag.entered_v2i)
                ag.entered_v2i = True

        # ---- 2. Clean up vehicles that left the network --------------------------------------
        for vid in traci.simulation.getArrivedIDList():
            agents.pop(vid, None)
            states.pop(vid, None)
            coordinator.remove_vehicle(vid)
            controller.forget(vid)

        # ---- 3. Low-frequency RSU sequencing (0.5 Hz) ----------------------------------------
        if step % sort_steps == 0:
            coordinator.run_sorting_algorithm(t)

        # ---- 4. 10 Hz Longitudinal Control (using EVENT-TRIGGERED V2V predecessor state) -----
        for vid, ego in states.items():
            pred_id = coordinator.get_predecessor(vid)

            # Follower gets predecessor's last broadcasted state + dead-reckoning extrapolation
            pred = None
            if pred_id and pred_id in agents:
                pred = agents[pred_id].get_broadcasted_state(t, use_dead_reckoning=dead_reckoning)

            # Physical radar for onboard TTC fail-safe (local sensor, unaffected by V2V events)
            leader = None
            info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
            if info:
                lid, gap = info
                if lid in states:
                    leader = {"speed": states[lid]["speed"], "gap": gap}

            if controller.failsafe_active(ego, leader):
                traci.vehicle.setSpeedMode(vid, 31)
                traci.vehicle.setSpeed(vid, -1)
                controller.prev_a[vid] = ego["accel"]
                a_cmd = float("nan")
            else:
                a_cmd = controller.compute_acceleration(ego, pred, coordinator.v_m)
                traci.vehicle.setSpeedMode(vid, 1)
                traci.vehicle.setSpeed(vid, max(0.0, ego["speed"] + a_cmd * DT))

            log.append((round(t, 1), vid, ego["origin"], ego["lane"], round(ego["dist_to_merge"], 2),
                        round(ego["speed"], 3), round(ego["accel"], 3), a_cmd,
                        coordinator.get_sequence_id(vid), pred_id, int(vid in controller.failsafe),
                        v2v_tx_flags.get(vid, 0)))

            if step % 20 == 0:
                d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                      f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}) a={a_cmd:5.2f} "
                      f"v_m={coordinator.v_m:.1f} tx={v2v_tx_flags.get(vid, 0)}")

    traci.close()

    saved_pct = 100.0 * (1.0 - total_sent_v2v / max(total_possible_v2v, 1))
    print(f"\nDone. t={t:.0f}s  collisions={collisions}")
    print(f"V2V Communication Summary (v_th={v_th} m/s, d_th={d_th} m, max_silence={max_silence} s, dead_reckoning={dead_reckoning}):")
    print(f"  10 Hz Baseline Packets : {total_possible_v2v}")
    print(f"  Event-Triggered Packets: {total_sent_v2v}")
    print(f"  Channel Load Reduction : {saved_pct:.1f}%")

    if log_path:
        with open(log_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
                        "seq", "pred", "failsafe", "v2v_tx"])
            w.writerows(log)
    return collisions


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nogui", action="store_true", help="run headless (much faster)")
    ap.add_argument("--time", type=float, default=None, help="stop after this many sim seconds")
    ap.add_argument("--log", default=os.path.join(HERE, "sim_log_event.csv"), help="CSV output")
    ap.add_argument("--v-th", type=float, default=DEFAULT_V_TH, help="V2V speed change threshold [m/s]")
    ap.add_argument("--d-th", type=float, default=DEFAULT_D_TH, help="V2V position drift threshold [m]")
    ap.add_argument("--max-silence", type=float, default=DEFAULT_MAX_SILENCE, help="Max silence heartbeat [s]")
    ap.add_argument("--no-dead-reckoning", action="store_true", help="Disable dead reckoning (use Zero-Order Hold)")
    args = ap.parse_args()
    run(gui=not args.nogui, sim_time=args.time, log_path=args.log,
        v_th=args.v_th, d_th=args.d_th, max_silence=args.max_silence,
        dead_reckoning=not args.no_dead_reckoning)
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

from agent import VehicleAgent
from infrastructure import InfrastructureCoordinator
from controller import LongitudinalController

DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz, paper: "low frequency" vs 10 Hz control)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe


def run(gui=True, sim_time=None, log_path=None, config_path=None):
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
    controller = LongitudinalController(dt=DT)
    agents = {}
    collisions = 0
    log = []
    sort_steps = int(round(SORT_PERIOD / DT))

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
        traci.simulationStep()
        step += 1
        t = traci.simulation.getTime()
        collisions += traci.simulation.getCollidingVehiclesNumber()

        # ---- 1. every vehicle reads its state ONCE and (first time only) reports to the RSU ----
        states = {}
        for vid in traci.vehicle.getIDList():
            if vid not in agents:
                agents[vid] = VehicleAgent(vid)
                traci.vehicle.setSpeedMode(vid, 1)      # obey our speed command (only 'safe speed' kept)
            ag = agents[vid]
            st = ag.update_state()
            states[vid] = st
            if st["lane"] in ("main", "ramp"):
                coordinator.receive_vehicle_data(vid, st["lane"], st["speed"], st["dist_to_merge"],
                                                 t, first_contact=not ag.entered_v2i)
                ag.entered_v2i = True

        # ---- 2. clean up vehicles that left the network --------------------------------------
        for vid in traci.simulation.getArrivedIDList():
            agents.pop(vid, None)
            states.pop(vid, None)
            coordinator.remove_vehicle(vid)
            controller.forget(vid)

        # ---- 3. low-frequency sequencing (results become visible to vehicles next step) ------
        if step % sort_steps == 0:
            coordinator.run_sorting_algorithm(t)

        # ---- 4. 10 Hz longitudinal control ---------------------------------------------------
        for vid, ego in states.items():
            pred_id = coordinator.get_predecessor(vid)
            pred = states.get(pred_id) if pred_id else None

            leader = None
            info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
            if info:
                lid, gap = info
                if lid in states:
                    leader = {"speed": states[lid]["speed"], "gap": gap}

            if controller.failsafe_active(ego, leader):
                # paper: consensus control is deactivated, internal car-following takes over
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
                        coordinator.get_sequence_id(vid), pred_id, int(vid in controller.failsafe)))

            if step % 20 == 0:
                d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                      f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}) a={a_cmd:5.2f} "
                      f"v_m={coordinator.v_m:.1f}")

    traci.close()
    print(f"\nDone. t={t:.0f}s  collisions={collisions}")

    if log_path:
        with open(log_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
                        "seq", "pred", "failsafe"])
            w.writerows(log)
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
    args = ap.parse_args()

    use_gui = True if args.gui else (False if args.nogui else env_gui)
    run(gui=use_gui, sim_time=args.time, log_path=args.log, config_path=args.config)
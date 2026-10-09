import argparse
import csv
import os
import sys

# Compute paths relative to src/ and project root
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "merge.config.xml")
OUTPUT_DIR = os.path.join(HERE, "output", "perfect_comm")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

sumo_home = os.environ.get("SUMO_HOME")
if sumo_home and os.path.isdir(sumo_home):
    tools = os.path.join(sumo_home, "tools")
    bin_dir = os.path.join(sumo_home, "bin")
    if tools not in sys.path:
        sys.path.append(tools)
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

import traci
import matplotlib.pyplot as plt

from perfect_comm.agent import VehicleAgent
from perfect_comm.infrastructure import InfrastructureCoordinator
from perfect_comm.controller import LongitudinalController

DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe

# Standard packet payload sizes [Bytes] for Communication Cost calculation
PKT_BYTES_V2I = 64
PKT_BYTES_I2V = 48
PKT_BYTES_V2V = 64

LOG_HEADER = [
    "t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
    "seq", "pred", "failsafe", "v2i_tx", "i2v_tx", "v2v_tx"
]


# def save_outputs_and_plots(out_dir, log, metrics, time_series):
#     os.makedirs(out_dir, exist_ok=True)
#     log_path = os.path.join(out_dir, "sim_log.csv")
#     summary_path = os.path.join(out_dir, "metrics_summary.csv")
#     plot_path = os.path.join(out_dir, "metrics_dashboard.png")

#     # 1. Save detailed step-by-step vehicle log
#     with open(log_path, "w", newline="") as f:
#         w = csv.writer(f)
#         w.writerow(LOG_HEADER)
#         w.writerows(log)

#     # 2. Save clean summary metrics CSV
#     with open(summary_path, "w", newline="") as f:
#         w = csv.writer(f)
#         w.writerow(["Metric", "Value", "Unit"])
#         for k, (val, unit) in metrics.items():
#             w.writerow([k, val, unit])

#     # 3. Generate 3-Panel Publication-Ready Dashboard Plot
#     fig, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=150)
#     fig.suptitle("Cooperative Merging Performance — Perfect Communication (10 Hz Baseline)",
#                  fontsize=14, fontweight="bold", y=1.02)

#     # Panel 1: Conflicts & Collisions
#     ax1 = axes[0]
#     c_labels = ["Physical\nCollisions", "TTC Conflict\nEvents (<2.0s)", "Conflict Steps\n(0.1s each)"]
#     c_vals = [
#         metrics["Collisions"][0],
#         metrics["TTC_Conflict_Events"][0],
#         metrics["TTC_Conflict_Steps"][0]
#     ]
#     bars1 = ax1.bar(c_labels, c_vals, color=["#d62728", "#ff7f0e", "#ffbb78"], edgecolor="black", width=0.55)
#     ax1.set_title("1. Safety: Conflicts & Collisions", fontweight="bold")
#     ax1.set_ylabel("Count")
#     ax1.grid(axis="y", linestyle="--", alpha=0.5)
#     for b in bars1:
#         h = b.get_height()
#         ax1.annotate(f"{int(h)}", xy=(b.get_x() + b.get_width() / 2, h),
#                      xytext=(0, 3), textcoords="offset points", ha="center", fontweight="bold")
#     ax1.set_ylim(0, max(max(c_vals) * 1.2, 5))

#     # Panel 2: Number of Messages by Link Type
#     ax2 = axes[1]
#     m_labels = ["V2I Uplink", "I2V Downlink", "V2V CACC", "Total Sent"]
#     m_vals = [
#         metrics["Messages_V2I_Sent"][0],
#         metrics["Messages_I2V_Sent"][0],
#         metrics["Messages_V2V_Sent"][0],
#         metrics["Messages_Total_Sent"][0]
#     ]
#     bars2 = ax2.bar(m_labels, m_vals, color=["#1f77b4", "#2ca02c", "#9467bd", "#333333"], edgecolor="black", width=0.55)
#     ax2.set_title("2. Number of Wireless Messages", fontweight="bold")
#     ax2.set_ylabel("Packet Count")
#     ax2.grid(axis="y", linestyle="--", alpha=0.5)
#     for b in bars2:
#         h = b.get_height()
#         ax2.annotate(f"{int(h):,}", xy=(b.get_x() + b.get_width() / 2, h),
#                      xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, fontweight="bold")
#     ax2.set_ylim(0, max(max(m_vals) * 1.18, 10))

#     # Panel 3: Cumulative Communication Cost Over Time (KB)
#     ax3 = axes[2]
#     t_arr = time_series["t"]
#     cost_kb_arr = time_series["cum_cost_kb"]
#     ax3.plot(t_arr, cost_kb_arr, color="#1f77b4", linewidth=2.2,
#              label=f"Total Cost: {metrics['Comm_Cost_Total_KB'][0]:.2f} KB\nAvg Rate: {metrics['Comm_Cost_Bitrate_kbps'][0]:.2f} kbps")
#     ax3.fill_between(t_arr, cost_kb_arr, color="#1f77b4", alpha=0.15)
#     ax3.set_title("3. Cumulative Communication Cost", fontweight="bold")
#     ax3.set_xlabel("Simulation Time [s]")
#     ax3.set_ylabel("Cumulative Data Transmitted [KB]")
#     ax3.grid(True, linestyle="--", alpha=0.5)
#     ax3.legend(loc="upper left", frameon=True)

#     plt.tight_layout()
#     plt.savefig(plot_path, bbox_inches="tight")
#     plt.close(fig)

#     print(f"\n[SAVED] Vehicle Log     -> {log_path}")
#     print(f"[SAVED] Metrics Summary -> {summary_path}")
#     print(f"[SAVED] Metrics Plot    -> {plot_path}")


def run(gui=True, sim_time=None, out_dir=OUTPUT_DIR, config_path=None):
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

    # Metrics counters
    collisions = 0
    conflict_events = 0
    conflict_steps = 0
    prev_failsafe_set = set()

    v2i_sent = 0
    i2v_sent = 0
    v2v_sent = 0

    log = []
    time_series = {"t": [], "cum_cost_kb": [], "cum_msgs": []}
    sort_steps = int(round(SORT_PERIOD / DT))

    step = 0
    t = 0.0
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
            traci.simulationStep()
            step += 1
            t = traci.simulation.getTime()
            collisions += traci.simulation.getCollidingVehiclesNumber()

            # ---- 1. Read vehicle state & report V2I Uplink (until sequenced) ----
            states = {}
            v2i_tx_step = {}
            for vid in traci.vehicle.getIDList():
                if vid not in agents:
                    agents[vid] = VehicleAgent(vid)
                    traci.vehicle.setSpeedMode(vid, 0)
                ag = agents[vid]
                st = ag.update_state()
                states[vid] = st

                if st["lane"] in ("main", "ramp"):
                    # In baseline, unsequenced cars send V2I uplink every step
                    is_unsequenced = coordinator.get_sequence_id(vid) is None
                    coordinator.receive_vehicle_data(vid, st["lane"], st["speed"], st["dist_to_merge"],
                                                     t, first_contact=not ag.entered_v2i)
                    ag.entered_v2i = True
                    if is_unsequenced:
                        v2i_sent += 1
                        v2i_tx_step[vid] = 1

            # ---- 2. Clean up vehicles that left the network ----
            for vid in traci.simulation.getArrivedIDList():
                agents.pop(vid, None)
                states.pop(vid, None)
                coordinator.remove_vehicle(vid)
                controller.forget(vid)
                prev_failsafe_set.discard(vid)

            # ---- 3. Low-frequency sequencing (0.5 Hz) & I2V Downlink count ----
            i2v_tx_step = {}
            if step % sort_steps == 0:
                coordinator.run_sorting_algorithm(t)
                for e in coordinator.sequence:
                    if e["id"] in states:
                        i2v_sent += 1
                        i2v_tx_step[e["id"]] = 1

            # ---- 4. 10 Hz Longitudinal Control & V2V Message count ----
            for vid, ego in states.items():
                pred_id = coordinator.get_predecessor(vid)
                pred = states.get(pred_id) if pred_id else None

                # If follower has an active predecessor in the network, a 10 Hz V2V beacon is used
                v2v_tx = 1 if pred is not None else 0
                v2v_sent += v2v_tx

                leader = None
                info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
                if info:
                    lid, gap = info
                    if lid in states:
                        leader = {"speed": states[lid]["speed"], "gap": gap}

                is_fs = controller.failsafe_active(ego, leader)
                #this is the part that handles back to SUMO, for further analysis
                if is_fs:
                    conflict_steps += 1
                    if vid not in prev_failsafe_set:
                        conflict_events += 1
                        prev_failsafe_set.add(vid)
                    traci.vehicle.setSpeedMode(vid,0)
                    traci.vehicle.setSpeed(vid)
                    controller.prev_a[vid] = ego["accel"]
                    a_cmd = float("nan")
                else:
                    prev_failsafe_set.discard(vid)
                    a_cmd = controller.compute_acceleration(ego, pred, coordinator.v_m)
                    traci.vehicle.setSpeedMode(vid, 0)
                    traci.vehicle.setSpeed(vid, max(0.0, ego["speed"] + a_cmd * DT))

                log.append((
                    round(t, 1), vid, ego["origin"], ego["lane"], round(ego["dist_to_merge"], 2),
                    round(ego["speed"], 3), round(ego["accel"], 3), a_cmd,
                    coordinator.get_sequence_id(vid), pred_id, int(is_fs),
                    v2i_tx_step.get(vid, 0), i2v_tx_step.get(vid, 0), v2v_tx
                ))

                if step % 20 == 0:
                    d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                    print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                          f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}) a={a_cmd:5.2f} "
                          f"v_m={coordinator.v_m:.1f}")

            total_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_sent * PKT_BYTES_V2V)
            time_series["t"].append(round(t, 1))
            time_series["cum_cost_kb"].append(total_bytes / 1024.0)
            time_series["cum_msgs"].append(v2i_sent + i2v_sent + v2v_sent)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        try:
            traci.close()
        except Exception:
            pass

    #     total_msgs = v2i_sent + i2v_sent + v2v_sent
    #     total_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_sent * PKT_BYTES_V2V)
    #     total_kb = total_bytes / 1024.0
    #     bitrate_kbps = (total_bytes * 8.0 / 1000.0) / max(t, DT)

    #     metrics = {
    #         "Duration_s": (round(t, 1), "s"),
    #         "Collisions": (collisions, "count"),
    #         "TTC_Conflict_Events": (conflict_events, "count"),
    #         "TTC_Conflict_Steps": (conflict_steps, "steps"),
    #         "Messages_V2I_Sent": (v2i_sent, "packets"),
    #         "Messages_I2V_Sent": (i2v_sent, "packets"),
    #         "Messages_V2V_Sent": (v2v_sent, "packets"),
    #         "Messages_Total_Sent": (total_msgs, "packets"),
    #         "Comm_Cost_Total_Bytes": (total_bytes, "B"),
    #         "Comm_Cost_Total_KB": (round(total_kb, 3), "KB"),
    #         "Comm_Cost_Bitrate_kbps": (round(bitrate_kbps, 3), "kbps"),
    #     }

    #     print(f"\nDone (Perfect Comm). t={t:.1f}s | Collisions={collisions} | TTC Conflicts={conflict_events}")
    #     print(f"Messages: Total={total_msgs} (V2I={v2i_sent}, I2V={i2v_sent}, V2V={v2v_sent})")
    #     print(f"Comm Cost: {total_kb:.2f} KB ({bitrate_kbps:.2f} kbps)")

    #     if out_dir:
    #         # save_outputs_and_plots(out_dir, log, metrics, time_series)

    # return collisions


if __name__ == "__main__":
    env_gui = os.environ.get("SUMO_GUI", "true").lower() in ("true", "1", "yes")
    env_time = os.environ.get("SIM_TIME")
    default_time = float(env_time) if env_time else None

    ap = argparse.ArgumentParser(description="Run Perfect-Comm CAV cooperative merge simulation.")
    ap.add_argument("--nogui", action="store_true", help="run headless (much faster)")
    ap.add_argument("--gui", action="store_true", help="force run with GUI")
    ap.add_argument("--time", type=float, default=default_time, help="stop after this many sim seconds")
    ap.add_argument("--config", type=str, default=None, help="path to custom SUMO config file")
    ap.add_argument("--out-dir", default=OUTPUT_DIR, help="Output directory for logs and plots")
    args = ap.parse_args()

    use_gui = True if args.gui else (False if args.nogui else env_gui)
    run(gui=use_gui, sim_time=args.time, out_dir=args.out_dir, config_path=args.config)
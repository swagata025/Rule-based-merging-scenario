import argparse
import csv
import os
import sys

# Compute paths relative to src/event_based_mech/, src/, and project root
HERE = os.path.dirname(os.path.abspath(__file__))          # .../src/event_based_mech
SRC_DIR = os.path.dirname(HERE)                            # .../src
PROJECT_ROOT = os.path.dirname(SRC_DIR)                    # .../minor-sem5-project
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "merge.config.xml")
OUTPUT_DIR = os.path.join(SRC_DIR, "output", "event_based_perfect_comm")

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

# Allow running both from inside `src/event_based_mech/` and from `src/`
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import traci
import matplotlib.pyplot as plt
import numpy as np

from agent import VehicleAgent
from infrastructure import InfrastructureCoordinator
from controller import LongitudinalController

DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe

# ---- Event-Based V2V Default Thresholds ----
DEFAULT_V_TH = 0.3         # [m/s] speed change threshold to trigger V2V packet
DEFAULT_D_TH = 0.5         # [m]   position drift threshold to trigger V2V packet
DEFAULT_MAX_SILENCE = 1.0  # [s]   maximum time between V2V heartbeat packets

# Standard packet payload sizes [Bytes] for Communication Cost calculation (consistent across all folders)
PKT_BYTES_V2I = 64
PKT_BYTES_I2V = 48
PKT_BYTES_V2V = 64

LOG_HEADER = [
    "t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
    "seq", "pred", "failsafe", "v2i_tx", "i2v_tx", "v2v_tx"
]


# def save_outputs_and_plots(out_dir, tag, log, metrics, time_series):
#     os.makedirs(out_dir, exist_ok=True)
#     suffix = f"_{tag}" if tag else ""
#     log_path = os.path.join(out_dir, f"sim_log{suffix}.csv")
#     summary_path = os.path.join(out_dir, f"metrics_summary{suffix}.csv")
#     plot_path = os.path.join(out_dir, f"metrics_dashboard{suffix}.png")

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

#     # 3. Generate 3-Panel Publication-Ready Dashboard Plot (Identical style to perfect_comm & real_comm)
#     fig, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=150)
#     title_params = (f"v_th={metrics['Param_V_Th_mps'][0]} m/s, "
#                     f"d_th={metrics['Param_D_Th_m'][0]} m, "
#                     f"max_silence={metrics['Param_Max_Silence_s'][0]} s")
#     fig.suptitle(f"Cooperative Merging Performance — Event-Based V2V Comm ({title_params})",
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

#     # Panel 2: Number of Messages (Event-Sent vs. Saved by Event Trigger)
#     ax2 = axes[1]
#     links = ["V2I Uplink", "I2V Downlink", "V2V CACC", "Total"]
#     sent_vals = [
#         metrics["Messages_V2I_Sent"][0],
#         metrics["Messages_I2V_Sent"][0],
#         metrics["Messages_V2V_Sent"][0],
#         metrics["Messages_Total_Sent"][0]
#     ]
#     base_v2v = metrics["Messages_V2V_Baseline_10Hz"][0]
#     base_total = metrics["Messages_V2I_Sent"][0] + metrics["Messages_I2V_Sent"][0] + base_v2v
#     base_vals = [
#         metrics["Messages_V2I_Sent"][0],
#         metrics["Messages_I2V_Sent"][0],
#         base_v2v,
#         base_total
#     ]
#     x = np.arange(len(links))
#     width = 0.36
#     b_base = ax2.bar(x - width / 2, base_vals, width, label="10 Hz Baseline", color="#aec7e8", edgecolor="black")
#     b_sent = ax2.bar(x + width / 2, sent_vals, width, label="Event-Triggered Sent", color="#1f77b4", edgecolor="black")
#     ax2.set_xticks(x)
#     ax2.set_xticklabels(links)
#     ax2.set_title("2. Number of Wireless Messages", fontweight="bold")
#     ax2.set_ylabel("Packet Count")
#     ax2.grid(axis="y", linestyle="--", alpha=0.5)
#     ax2.legend(loc="upper left")
#     for b in list(b_base) + list(b_sent):
#         h = b.get_height()
#         ax2.annotate(f"{int(h):,}", xy=(b.get_x() + b.get_width() / 2, h),
#                      xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
#     ax2.set_ylim(0, max(max(base_vals) * 1.2, 10))

#     # Panel 3: Cumulative Communication Cost Over Time (KB)
#     ax3 = axes[2]
#     t_arr = time_series["t"]
#     cost_event_kb = time_series["cum_cost_kb"]
#     cost_base_kb = time_series["cum_baseline_cost_kb"]
#     ax3.plot(t_arr, cost_base_kb, color="#7f7f7f", linestyle="--", linewidth=2.0,
#              label=f"10 Hz Baseline Cost: {metrics['Comm_Cost_Baseline_10Hz_KB'][0]:.2f} KB")
#     ax3.plot(t_arr, cost_event_kb, color="#2ca02c", linewidth=2.2,
#              label=f"Event-Triggered Cost: {metrics['Comm_Cost_Total_KB'][0]:.2f} KB ({metrics['Comm_Cost_Bitrate_kbps'][0]:.2f} kbps)")
#     ax3.fill_between(t_arr, cost_event_kb, cost_base_kb, color="#2ca02c", alpha=0.15,
#                      label=f"Saved Bandwidth ({metrics['V2V_Reduction_Pct'][0]:.1f}% V2V reduction)")
#     ax3.set_title("3. Cumulative Communication Cost", fontweight="bold")
#     ax3.set_xlabel("Simulation Time [s]")
#     ax3.set_ylabel("Cumulative Data Transmitted [KB]")
#     ax3.grid(True, linestyle="--", alpha=0.5)
#     ax3.legend(loc="upper left", fontsize=8.5, frameon=True)

#     plt.tight_layout()
#     plt.savefig(plot_path, bbox_inches="tight")
#     plt.close(fig)

#     print(f"\n[SAVED] Vehicle Log     -> {log_path}")
#     print(f"[SAVED] Metrics Summary -> {summary_path}")
#     print(f"[SAVED] Metrics Plot    -> {plot_path}")


def run(gui=True, sim_time=None, out_dir=OUTPUT_DIR, tag="", config_path=None,
        v_th=DEFAULT_V_TH, d_th=DEFAULT_D_TH, max_silence=DEFAULT_MAX_SILENCE, dead_reckoning=True):
    cfg = config_path or os.environ.get("SUMO_CONFIG_PATH") or DEFAULT_CONFIG
    if not os.path.isabs(cfg):
        cfg = os.path.normpath(os.path.join(PROJECT_ROOT, cfg))
    if not os.path.isfile(cfg):
        fallback_cfg = r"C:\Users\Swagata\OneDrive\Desktop\documents\minor-sem5-project\config\merge.config.xml"
        cfg = fallback_cfg if os.path.isfile(fallback_cfg) else cfg
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
    v2v_baseline_possible = 0

    log = []
    time_series = {"t": [], "cum_cost_kb": [], "cum_baseline_cost_kb": [], "cum_msgs": []}
    sort_steps = int(round(SORT_PERIOD / DT))

    step = 0
    t = 0.0
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
            traci.simulationStep()
            step += 1
            t = traci.simulation.getTime()
            collisions += traci.simulation.getCollidingVehiclesNumber()

            # ---- 1. Every vehicle reads its onboard state (10 Hz) & evaluates V2V Event Trigger ----
            states = {}
            v2i_tx_step = {}
            v2v_tx_flags = {}

            for vid in traci.vehicle.getIDList():
                if vid not in agents:
                    agents[vid] = VehicleAgent(vid)
                    traci.vehicle.setSpeedMode(vid, 0)
                ag = agents[vid]
                st = ag.update_state()
                states[vid] = st

                # Evaluate Event-Based V2V Trigger
                triggered = ag.check_and_broadcast_v2v(
                    current_time=t, current_state=st,
                    v_th=v_th, d_th=d_th, max_silence=max_silence
                )
                v2v_tx_flags[vid] = int(triggered)

                # V2I Uplink (for unsequenced vehicles on main or ramp)
                if st["lane"] in ("main", "ramp"):
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

            # ---- 3. Low-frequency RSU sequencing (0.5 Hz) & I2V Downlink count ----
            i2v_tx_step = {}
            if step % sort_steps == 0:
                coordinator.run_sorting_algorithm(t)
                for e in coordinator.sequence:
                    if e["id"] in states:
                        i2v_sent += 1
                        i2v_tx_step[e["id"]] = 1

            # ---- 4. 10 Hz Longitudinal Control (using EVENT-TRIGGERED V2V predecessor state) ----
            for vid, ego in states.items():
                pred_id = coordinator.get_predecessor(vid)

                # Follower gets predecessor's last broadcasted state + dead-reckoning extrapolation
                pred = None
                v2v_tx_used = 0
                if pred_id and pred_id in agents:
                    pred = agents[pred_id].get_broadcasted_state(t, use_dead_reckoning=dead_reckoning)
                    # Count V2V message only when an active follower-predecessor link exists
                    v2v_baseline_possible += 1
                    v2v_tx_used = v2v_tx_flags.get(pred_id, 0)
                    v2v_sent += v2v_tx_used

                # Physical radar for onboard TTC fail-safe
                leader = None
                info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
                if info:
                    lid, gap = info
                    if lid in states:
                        leader = {"speed": states[lid]["speed"], "gap": gap}

                is_fs = controller.failsafe_active(ego, leader)
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
                    v2i_tx_step.get(vid, 0), i2v_tx_step.get(vid, 0), v2v_tx_flags.get(vid, 0)
                ))

                if step % 20 == 0:
                    d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                    print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                          f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}) a={a_cmd:5.2f} "
                          f"v_m={coordinator.v_m:.1f} tx={v2v_tx_flags.get(vid, 0)}")

            total_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_sent * PKT_BYTES_V2V)
            base_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_baseline_possible * PKT_BYTES_V2V)
            time_series["t"].append(round(t, 1))
            time_series["cum_cost_kb"].append(total_bytes / 1024.0)
            time_series["cum_baseline_cost_kb"].append(base_bytes / 1024.0)
            time_series["cum_msgs"].append(v2i_sent + i2v_sent + v2v_sent)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        try:
            traci.close()
        except Exception:
            pass

        total_msgs = v2i_sent + i2v_sent + v2v_sent
        total_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_sent * PKT_BYTES_V2V)
        base_bytes = (v2i_sent * PKT_BYTES_V2I) + (i2v_sent * PKT_BYTES_I2V) + (v2v_baseline_possible * PKT_BYTES_V2V)
        total_kb = total_bytes / 1024.0
        base_kb = base_bytes / 1024.0
        bitrate_kbps = (total_bytes * 8.0 / 1000.0) / max(t, DT)
        v2v_saved_pct = 100.0 * (1.0 - v2v_sent / max(v2v_baseline_possible, 1))

        metrics = {
            "Param_V_Th_mps": (v_th, "m/s"),
            "Param_D_Th_m": (d_th, "m"),
            "Param_Max_Silence_s": (max_silence, "s"),
            "Duration_s": (round(t, 1), "s"),
            "Collisions": (collisions, "count"),
            "TTC_Conflict_Events": (conflict_events, "count"),
            "TTC_Conflict_Steps": (conflict_steps, "steps"),
            "Messages_V2I_Sent": (v2i_sent, "packets"),
            "Messages_I2V_Sent": (i2v_sent, "packets"),
            "Messages_V2V_Sent": (v2v_sent, "packets"),
            "Messages_V2V_Baseline_10Hz": (v2v_baseline_possible, "packets"),
            "V2V_Reduction_Pct": (round(v2v_saved_pct, 2), "%"),
            "Messages_Total_Sent": (total_msgs, "packets"),
            "Comm_Cost_Total_Bytes": (total_bytes, "B"),
            "Comm_Cost_Total_KB": (round(total_kb, 3), "KB"),
            "Comm_Cost_Baseline_10Hz_KB": (round(base_kb, 3), "KB"),
            "Comm_Cost_Bitrate_kbps": (round(bitrate_kbps, 3), "kbps"),
        }

        print(f"\nDone (Event-Based Comm). t={t:.1f}s | Collisions={collisions} | TTC Conflicts={conflict_events}")
        print(f"Messages: Total={total_msgs} (V2I={v2i_sent}, I2V={i2v_sent}, V2V={v2v_sent} vs 10Hz_V2V={v2v_baseline_possible})")
        print(f"V2V Channel Load Reduction: {v2v_saved_pct:.1f}%")
        print(f"Comm Cost: {total_kb:.2f} KB vs {base_kb:.2f} KB baseline ({bitrate_kbps:.2f} kbps)")

        # if out_dir:
        #     save_outputs_and_plots(out_dir, tag, log, metrics, time_series)

    return collisions


if __name__ == "__main__":
    env_gui = os.environ.get("SUMO_GUI", "true").lower() in ("true", "1", "yes")
    env_time = os.environ.get("SIM_TIME")
    default_time = float(env_time) if env_time else None

    ap = argparse.ArgumentParser(description="Run Event-Based V2V CAV cooperative merge simulation.")
    ap.add_argument("--nogui", action="store_true", help="run headless (much faster)")
    ap.add_argument("--gui", action="store_true", help="force run with GUI")
    ap.add_argument("--time", type=float, default=default_time, help="stop after this many sim seconds")
    ap.add_argument("--config", type=str, default=None, help="path to custom SUMO config file")
    ap.add_argument("--out-dir", default=OUTPUT_DIR, help="Output directory for logs and plots")
    ap.add_argument("--tag", default="", help="Optional filename tag")
    ap.add_argument("--v-th", type=float, default=DEFAULT_V_TH, help="V2V speed change threshold [m/s]")
    ap.add_argument("--d-th", type=float, default=DEFAULT_D_TH, help="V2V position drift threshold [m]")
    ap.add_argument("--max-silence", type=float, default=DEFAULT_MAX_SILENCE, help="Max silence heartbeat [s]")
    ap.add_argument("--no-dead-reckoning", action="store_true", help="Disable dead reckoning (use Zero-Order Hold)")
    args = ap.parse_args()

    use_gui = True if args.gui else (False if args.nogui else env_gui)
    run(gui=use_gui, sim_time=args.time, out_dir=args.out_dir, tag=args.tag, config_path=args.config,
        v_th=args.v_th, d_th=args.d_th, max_silence=args.max_silence,
        dead_reckoning=not args.no_dead_reckoning)
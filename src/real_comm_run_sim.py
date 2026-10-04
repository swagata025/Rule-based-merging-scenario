import argparse
import csv
import os
import sys

# Compute paths relative to src/ and project root
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "merge.config.xml")
OUTPUT_DIR = os.path.join(HERE, "output", "real_comm")

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
import numpy as np

from real_comm.agent import VehicleAgent
from real_comm.infrastructure import InfrastructureCoordinator
from real_comm.channel import Channel

DT = 0.1
SORT_PERIOD = 2.0          # [s] infrastructure sorting period (0.5 Hz)
LEADER_LOOKAHEAD = 150.0   # [m] radar range used by the TTC fail-safe

# Standard packet payload sizes [Bytes] for Communication Cost calculation
PKT_BYTES_V2I = 64
PKT_BYTES_I2V = 48
PKT_BYTES_V2V = 64

LOG_HEADER = [
    "t", "id", "origin", "lane", "dist_to_merge", "speed", "accel", "a_cmd",
    "seq", "pred", "failsafe", "pred_age", "v_m_known"
]


def save_outputs_and_plots(out_dir, tag, log, metrics, time_series):
    os.makedirs(out_dir, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    log_path = os.path.join(out_dir, f"sim_log{suffix}.csv")
    summary_path = os.path.join(out_dir, f"metrics_summary{suffix}.csv")
    plot_path = os.path.join(out_dir, f"metrics_dashboard{suffix}.png")

    # 1. Save detailed step-by-step vehicle log
    with open(log_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(LOG_HEADER)
        w.writerows(log)

    # 2. Save clean summary metrics CSV
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value", "Unit"])
        for k, (val, unit) in metrics.items():
            w.writerow([k, val, unit])

    # 3. Generate 3-Panel Publication-Ready Dashboard Plot
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=150)
    title_params = (f"loss={metrics['Param_Loss_Prob'][0]:.0%}, "
                    f"delay={metrics['Param_Delay_s'][0]}s, "
                    f"jitter={metrics['Param_Jitter_s'][0]}s")
    fig.suptitle(f"Cooperative Merging Performance — Real Impaired Comm ({title_params})",
                 fontsize=14, fontweight="bold", y=1.02)

    # Panel 1: Conflicts & Collisions
    ax1 = axes[0]
    c_labels = ["Physical\nCollisions", "TTC Conflict\nEvents (<2.0s)", "Conflict Steps\n(0.1s each)"]
    c_vals = [
        metrics["Collisions"][0],
        metrics["TTC_Conflict_Events"][0],
        metrics["TTC_Conflict_Steps"][0]
    ]
    bars1 = ax1.bar(c_labels, c_vals, color=["#d62728", "#ff7f0e", "#ffbb78"], edgecolor="black", width=0.55)
    ax1.set_title("1. Safety: Conflicts & Collisions", fontweight="bold")
    ax1.set_ylabel("Count")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    for b in bars1:
        h = b.get_height()
        ax1.annotate(f"{int(h)}", xy=(b.get_x() + b.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", fontweight="bold")
    ax1.set_ylim(0, max(max(c_vals) * 1.2, 5))

    # Panel 2: Number of Messages (Sent vs. Dropped)
    ax2 = axes[1]
    links = ["V2I Uplink", "I2V Downlink", "V2V CACC", "Total"]
    sent_vals = [
        metrics["Messages_V2I_Sent"][0],
        metrics["Messages_I2V_Sent"][0],
        metrics["Messages_V2V_Sent"][0],
        metrics["Messages_Total_Sent"][0]
    ]
    drop_vals = [
        metrics["Messages_V2I_Dropped"][0],
        metrics["Messages_I2V_Dropped"][0],
        metrics["Messages_V2V_Dropped"][0],
        metrics["Messages_Total_Dropped"][0]
    ]
    x = np.arange(len(links))
    width = 0.36
    b_sent = ax2.bar(x - width / 2, sent_vals, width, label="Sent", color="#1f77b4", edgecolor="black")
    b_drop = ax2.bar(x + width / 2, drop_vals, width, label="Dropped", color="#d62728", edgecolor="black")
    ax2.set_xticks(x)
    ax2.set_xticklabels(links)
    ax2.set_title("2. Number of Wireless Messages", fontweight="bold")
    ax2.set_ylabel("Packet Count")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left")
    for b in list(b_sent) + list(b_drop):
        h = b.get_height()
        ax2.annotate(f"{int(h):,}", xy=(b.get_x() + b.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
    ax2.set_ylim(0, max(max(sent_vals) * 1.2, 10))

    # Panel 3: Cumulative Communication Cost Over Time (KB)
    ax3 = axes[2]
    t_arr = time_series["t"]
    cost_tx_kb = time_series["cum_tx_kb"]
    cost_rx_kb = time_series["cum_rx_kb"]
    ax3.plot(t_arr, cost_tx_kb, color="#1f77b4", linewidth=2.2,
             label=f"Transmitted Cost: {metrics['Comm_Cost_Sent_KB'][0]:.2f} KB ({metrics['Comm_Cost_Bitrate_kbps'][0]:.2f} kbps)")
    ax3.plot(t_arr, cost_rx_kb, color="#2ca02c", linestyle="--", linewidth=2.0,
             label=f"Delivered Goodput: {metrics['Comm_Cost_Delivered_KB'][0]:.2f} KB")
    ax3.fill_between(t_arr, cost_rx_kb, cost_tx_kb, color="#d62728", alpha=0.15, label="Wasted Cost (Dropped)")
    ax3.set_title("3. Cumulative Communication Cost", fontweight="bold")
    ax3.set_xlabel("Simulation Time [s]")
    ax3.set_ylabel("Cumulative Data [KB]")
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="upper left", fontsize=8.5, frameon=True)

    plt.tight_layout()
    plt.savefig(plot_path, bbox_inches="tight")
    plt.close(fig)

    print(f"\n[SAVED] Vehicle Log     -> {log_path}")
    print(f"[SAVED] Metrics Summary -> {summary_path}")
    print(f"[SAVED] Metrics Plot    -> {plot_path}")


def run(gui=True, sim_time=None, out_dir=OUTPUT_DIR, tag="", config_path=None,
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

    v2i = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed)       # vehicle -> RSU
    i2v = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed + 1)   # RSU -> vehicle
    v2v = Channel(loss=loss, base_delay=delay, jitter=jitter, seed=seed + 2)   # vehicle -> vehicle

    agents = {}
    collisions = 0
    conflict_events = 0
    conflict_steps = 0
    prev_failsafe_set = set()

    log = []
    time_series = {"t": [], "cum_tx_kb": [], "cum_rx_kb": []}
    sort_steps = int(round(SORT_PERIOD / DT))

    step = 0
    t = 0.0
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and (sim_time is None or step * DT < sim_time):
            traci.simulationStep()
            step += 1
            t = traci.simulation.getTime()
            collisions += traci.simulation.getCollidingVehiclesNumber()

            # ---- 1. Read own state and SEND messages ----
            states = {}
            for vid in traci.vehicle.getIDList():
                if vid not in agents:
                    agents[vid] = VehicleAgent(vid, DT)
                    traci.vehicle.setSpeedMode(vid, 1)
                ag = agents[vid]
                st = ag.update_state()
                states[vid] = st

                if st["lane"] in ("main", "ramp") and not ag.sequenced:
                    v2i.send({"id": vid, "lane": st["lane"], "speed": st["speed"],
                              "dist": st["dist_to_merge"], "ts": t}, t)

            for vid, ag in agents.items():
                p = states.get(ag.pred_id) if ag.pred_id else None
                if p:
                    v2v.send({"to": vid, "from": ag.pred_id, "ts": t, "speed": p["speed"],
                              "dist_to_merge": p["dist_to_merge"], "length": p["length"]}, t)

            # ---- 2. Clean up vehicles that left the network ----
            for vid in traci.simulation.getArrivedIDList():
                agents.pop(vid, None)
                states.pop(vid, None)
                coordinator.remove_vehicle(vid)
                prev_failsafe_set.discard(vid)

            # ---- 2b. DELIVER messages whose delivery time has arrived ----
            for m in v2i.receive(t):
                if m["id"] in agents:
                    coordinator.receive_vehicle_data(m["id"], m["lane"], m["speed"], m["dist"], m["ts"])
            for m in i2v.receive(t):
                if m["to"] in agents:
                    agents[m["to"]].on_downlink(m)
            for m in v2v.receive(t):
                if m["to"] in agents:
                    agents[m["to"]].on_v2v(m)

            # ---- 3. Low-frequency sequencing, then broadcast over I2V ----
            if step % sort_steps == 0:
                coordinator.run_sorting_algorithm(t)
                for m in coordinator.downlink_messages(t):
                    i2v.send(m, t)

            # ---- 4. 10 Hz longitudinal control ----
            for vid, ego in states.items():
                ag = agents[vid]
                pred_id = ag.pred_id
                pred = ag.predecessor_estimate(t)
                pred_age = (t - ag.pred_msg["ts"]) if ag.pred_msg else float("nan")

                leader = None
                info = traci.vehicle.getLeader(vid, LEADER_LOOKAHEAD)
                if info:
                    lid, gap = info
                    if lid in states:
                        leader = {"speed": states[lid]["speed"], "gap": gap}

                ctrl = ag.controller
                is_fs = ctrl.failsafe_active(ego, leader)
                if is_fs:
                    conflict_steps += 1
                    if vid not in prev_failsafe_set:
                        conflict_events += 1
                        prev_failsafe_set.add(vid)
                    traci.vehicle.setSpeedMode(vid, 31)
                    traci.vehicle.setSpeed(vid, -1)
                    ctrl.prev_a = ego["accel"]
                    a_cmd = float("nan")
                else:
                    prev_failsafe_set.discard(vid)
                    a_cmd = ctrl.compute_acceleration(ego, pred, ag.v_m)
                    traci.vehicle.setSpeedMode(vid, 1)
                    traci.vehicle.setSpeed(vid, max(0.0, ego["speed"] + a_cmd * DT))

                log.append((
                    round(t, 1), vid, ego["origin"], ego["lane"], round(ego["dist_to_merge"], 2),
                    round(ego["speed"], 3), round(ego["accel"], 3), a_cmd,
                    coordinator.get_sequence_id(vid), pred_id, int(ctrl.failsafe),
                    round(pred_age, 2), round(ag.v_m, 2)
                ))

                if step % 20 == 0:
                    d_pred = f"{pred['dist_to_merge']:.1f}" if pred else "-"
                    print(f"[{t:6.1f}s] {vid:<14}({ego['lane']:<8}) v={ego['speed']:5.1f} "
                          f"d2m={ego['dist_to_merge']:7.1f} pred={pred_id} (d={d_pred}, age={pred_age:.2f}) "
                          f"a={a_cmd:5.2f} v_m={ag.v_m:.1f}")

            tx_bytes = (v2i.sent * PKT_BYTES_V2I) + (i2v.sent * PKT_BYTES_I2V) + (v2v.sent * PKT_BYTES_V2V)
            rx_bytes = ((v2i.sent - v2i.dropped) * PKT_BYTES_V2I +
                        (i2v.sent - i2v.dropped) * PKT_BYTES_I2V +
                        (v2v.sent - v2v.dropped) * PKT_BYTES_V2V)
            time_series["t"].append(round(t, 1))
            time_series["cum_tx_kb"].append(tx_bytes / 1024.0)
            time_series["cum_rx_kb"].append(rx_bytes / 1024.0)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        try:
            traci.close()
        except Exception:
            pass

        total_sent = v2i.sent + i2v.sent + v2v.sent
        total_dropped = v2i.dropped + i2v.dropped + v2v.dropped
        total_delivered = total_sent - total_dropped

        tx_bytes = (v2i.sent * PKT_BYTES_V2I) + (i2v.sent * PKT_BYTES_I2V) + (v2v.sent * PKT_BYTES_V2V)
        rx_bytes = ((v2i.sent - v2i.dropped) * PKT_BYTES_V2I +
                    (i2v.sent - i2v.dropped) * PKT_BYTES_I2V +
                    (v2v.sent - v2v.dropped) * PKT_BYTES_V2V)
        tx_kb = tx_bytes / 1024.0
        rx_kb = rx_bytes / 1024.0
        bitrate_kbps = (tx_bytes * 8.0 / 1000.0) / max(t, DT)

        metrics = {
            "Param_Loss_Prob": (loss, "prob"),
            "Param_Delay_s": (delay, "s"),
            "Param_Jitter_s": (jitter, "s"),
            "Duration_s": (round(t, 1), "s"),
            "Collisions": (collisions, "count"),
            "TTC_Conflict_Events": (conflict_events, "count"),
            "TTC_Conflict_Steps": (conflict_steps, "steps"),
            "Messages_V2I_Sent": (v2i.sent, "packets"),
            "Messages_V2I_Dropped": (v2i.dropped, "packets"),
            "Messages_I2V_Sent": (i2v.sent, "packets"),
            "Messages_I2V_Dropped": (i2v.dropped, "packets"),
            "Messages_V2V_Sent": (v2v.sent, "packets"),
            "Messages_V2V_Dropped": (v2v.dropped, "packets"),
            "Messages_Total_Sent": (total_sent, "packets"),
            "Messages_Total_Dropped": (total_dropped, "packets"),
            "Messages_Total_Delivered": (total_delivered, "packets"),
            "Comm_Cost_Sent_Bytes": (tx_bytes, "B"),
            "Comm_Cost_Sent_KB": (round(tx_kb, 3), "KB"),
            "Comm_Cost_Delivered_KB": (round(rx_kb, 3), "KB"),
            "Comm_Cost_Bitrate_kbps": (round(bitrate_kbps, 3), "kbps"),
        }

        print(f"\nDone (Real Comm). t={t:.1f}s | Collisions={collisions} | TTC Conflicts={conflict_events}")
        for name, ch in (("v2i", v2i), ("i2v", i2v), ("v2v", v2v)):
            rate = ch.dropped / ch.sent if ch.sent else 0.0
            print(f"  {name}: sent={ch.sent} dropped={ch.dropped} ({rate:.1%})")
        print(f"Comm Cost: Sent={tx_kb:.2f} KB | Delivered={rx_kb:.2f} KB | Avg Rate={bitrate_kbps:.2f} kbps")

        if out_dir:
            auto_tag = tag or (f"loss{int(loss*100)}_delay{int(delay*1000)}ms" if (loss or delay or jitter) else "baseline")
            save_outputs_and_plots(out_dir, auto_tag, log, metrics, time_series)

    return collisions


if __name__ == "__main__":
    env_gui = os.environ.get("SUMO_GUI", "true").lower() in ("true", "1", "yes")
    env_time = os.environ.get("SIM_TIME")
    default_time = float(env_time) if env_time else None

    ap = argparse.ArgumentParser(description="Run Real-Comm CAV cooperative merge simulation.")
    ap.add_argument("--nogui", action="store_true", help="run headless (much faster)")
    ap.add_argument("--gui", action="store_true", help="force run with GUI")
    ap.add_argument("--time", type=float, default=default_time, help="stop after this many sim seconds")
    ap.add_argument("--config", type=str, default=None, help="path to custom SUMO config file")
    ap.add_argument("--out-dir", default=OUTPUT_DIR, help="Output directory for logs and plots")
    ap.add_argument("--tag", default="", help="Optional filename tag (e.g. loss10)")
    ap.add_argument("--loss", type=float, default=0.0, help="packet loss probability per message (0-1)")
    ap.add_argument("--delay", type=float, default=0.0, help="base one-way delay [s]")
    ap.add_argument("--jitter", type=float, default=0.0, help="extra uniform random delay up to this [s]")
    ap.add_argument("--seed", type=int, default=1, help="base RNG seed for the channels")
    args = ap.parse_args()

    use_gui = True if args.gui else (False if args.nogui else env_gui)
    run(gui=use_gui, sim_time=args.time, out_dir=args.out_dir, tag=args.tag,
        config_path=args.config, loss=args.loss, delay=args.delay, jitter=args.jitter, seed=args.seed)
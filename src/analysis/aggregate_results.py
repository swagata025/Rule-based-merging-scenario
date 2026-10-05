import os
import pandas as pd

def aggregate_benchmark_results(output_base_dir="src/output", save_csv=True):
    """
    Scans simulation output folders and aggregates key performance indicators into a unified summary table.
    """
    configs = [
        ("Perfect Comm (10 Hz Baseline)", os.path.join(output_base_dir, "perfect_comm", "metrics_summary.csv")),
        ("Event-Based V2V (Proposed)", os.path.join(output_base_dir, "event_based_perfect_comm", "metrics_summary.csv")),
        ("Real Comm (0% Loss)", os.path.join(output_base_dir, "real_comm", "metrics_summary_base.csv")),
        ("Real Comm (10% Loss)", os.path.join(output_base_dir, "real_comm", "metrics_summary_loss10.csv")),
        ("Real Comm (30% Loss)", os.path.join(output_base_dir, "real_comm", "metrics_summary_loss30.csv")),
    ]

    data = []
    for name, p in configs:
        if os.path.exists(p):
            df = pd.read_csv(p, index_col=0)
            m = df["Value"].to_dict()
            loss_val = float(m.get("Param_Loss_Prob", 0.0))
            cost = m.get("Comm_Cost_Total_KB", m.get("Comm_Cost_Sent_KB", "-"))
            delivered_cost = m.get("Comm_Cost_Delivered_KB", cost)
            data.append({
                "Scenario": name,
                "Duration [s]": m.get("Duration_s", "-"),
                "Collisions": m.get("Collisions", "-"),
                "TTC Conflicts": m.get("TTC_Conflict_Events", "-"),
                "V2V Packets Sent": m.get("Messages_V2V_Sent", "-"),
                "Total Packets Sent": m.get("Messages_Total_Sent", "-"),
                "Sent Data [KB]": cost,
                "Delivered Data [KB]": delivered_cost,
                "Bitrate [kbps]": m.get("Comm_Cost_Bitrate_kbps", "-"),
                "Packet Loss [%]": f"{loss_val*100:.0f}%",
            })

    res = pd.DataFrame(data)
    if save_csv and not res.empty:
        out_path = os.path.join(output_base_dir, "benchmark_aggregate.csv")
        res.to_csv(out_path, index=False)
        print(f"[SAVED] Aggregated table saved to {out_path}")
    return res

if __name__ == "__main__":
    df = aggregate_benchmark_results()
    if not df.empty:
        print("\n" + df.to_string(index=False))

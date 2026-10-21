import os
import subprocess
import csv
import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import shutil

# --- Directory Configuration ---
# Get the exact directory of this script (src)
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# Force Python to go up exactly one level to minor-sem5-project
PROJECT_ROOT = os.path.abspath(os.path.join(SRC_DIR, ".."))

ROUTE_FILE = os.path.join(PROJECT_ROOT, "routes", "merge.route.xml") 
OUTPUT_DIR = os.path.join(SRC_DIR, "perfect_comm_graphs")
RAW_DATA_DIR = os.path.join(OUTPUT_DIR, "raw_data")

# Scripts
BASELINE_SCRIPT = os.path.join(PROJECT_ROOT, "src", "perfect_comm_run_sim.py")
EVENT_SCRIPT = os.path.join(PROJECT_ROOT, "src", "event_based_mech", "run_sim.py")

SIM_TIME = "3600"
SEEDS = [42, 101, 202, 303, 404]

highway_vph = np.linspace(900, 1800, 10, dtype=int)
ramp_vph = np.linspace(600, 1200, 10, dtype=int)
vph_pairs = list(zip(highway_vph, ramp_vph))

def update_route_file(route_path, hw_vph, r_vph):
    tree = ET.parse(route_path)
    root = tree.getroot()
    for flow in root.findall('flow'):
        flow_id = flow.get('id', '').lower()
        if 'main' in flow_id or 'highway' in flow_id:
            flow.set('vehsPerHour', str(hw_vph))
        elif 'ramp' in flow_id:
            flow.set('vehsPerHour', str(r_vph))
    tree.write(route_path)

def parse_metrics(csv_path):
    metrics = {}
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                metrics[row[0]] = float(row[1])
    return metrics

def run_study():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    results = {
        "x_labels": [],
        "baseline": {"collisions": [], "ttc": [], "total_msgs": [], "v2v_msgs": [], "cost_kb": []},
        "event": {"collisions": [], "ttc": [], "total_msgs": [], "v2v_msgs": [], "cost_kb": []}
    }

    for hw, rp in vph_pairs:
        label = f"{hw},{rp}"
        results["x_labels"].append(label)
        print(f"\n--- Running Simulations for VPH: {label} ---")
        update_route_file(ROUTE_FILE, hw, rp)
        
        # Temporary lists to hold seed data for this VPH pair
        temp_base = {"col": [], "ttc": [], "msgs": [], "v2v": [], "cost": []}
        temp_event = {"col": [], "ttc": [], "msgs": [], "v2v": [], "cost": []}

        for seed in SEEDS:
            print(f"  -> Running Seed: {seed}")
            
            # --- 1. BASELINE ---
            subprocess.run([
                "python", BASELINE_SCRIPT, "--time", SIM_TIME, "--out-dir", RAW_DATA_DIR, 
                "--seed", str(seed), "--nogui", "--no-log"
            ], check=True)
            
            # Rename output files
            base_csv = os.path.join(RAW_DATA_DIR, f"baseline_{hw}_{rp}_seed{seed}.csv")
            os.replace(os.path.join(RAW_DATA_DIR, "metrics_summary.csv"), base_csv)
            if os.path.exists(os.path.join(RAW_DATA_DIR, "collisions.xml")):
                os.replace(os.path.join(RAW_DATA_DIR, "collisions.xml"), os.path.join(RAW_DATA_DIR, f"collisions_base_{hw}_{rp}_seed{seed}.xml"))
            
            b_mets = parse_metrics(base_csv)
            temp_base["col"].append(b_mets.get("Collisions", 0))
            temp_base["ttc"].append(b_mets.get("TTC_Conflict_Events", 0))
            temp_base["msgs"].append(b_mets.get("Messages_Total_Sent", 0))
            temp_base["v2v"].append(b_mets.get("Messages_V2V_Sent", 0))
            temp_base["cost"].append(b_mets.get("Comm_Cost_Total_KB", 0))

            # --- 2. EVENT-BASED ---
            tag = f"event_{hw}_{rp}_seed{seed}"
            subprocess.run([
                "python", EVENT_SCRIPT, "--time", SIM_TIME, "--out-dir", RAW_DATA_DIR, 
                "--tag", tag, "--seed", str(seed), "--nogui", "--no-log"
            ], check=True)
            
            event_csv = os.path.join(RAW_DATA_DIR, f"metrics_summary_{tag}.csv")
            if os.path.exists(os.path.join(RAW_DATA_DIR, "collisions.xml")):
                os.replace(os.path.join(RAW_DATA_DIR, "collisions.xml"), os.path.join(RAW_DATA_DIR, f"collisions_{tag}.xml"))
            
            e_mets = parse_metrics(event_csv)
            temp_event["col"].append(e_mets.get("Collisions", 0))
            temp_event["ttc"].append(e_mets.get("TTC_Conflict_Events", 0))
            temp_event["msgs"].append(e_mets.get("Messages_Total_Sent", 0))
            temp_event["v2v"].append(e_mets.get("Messages_V2V_Sent", 0))
            temp_event["cost"].append(e_mets.get("Comm_Cost_Total_KB", 0))
            
            # Clean up generated dashboard images to save space since we only want final graphs
            for file in os.listdir(RAW_DATA_DIR):
                if file.endswith(".png"):
                    os.remove(os.path.join(RAW_DATA_DIR, file))

        # Calculate averages for the 5 seeds and append to main plotting arrays
        results["baseline"]["collisions"].append(np.mean(temp_base["col"]))
        results["baseline"]["ttc"].append(np.mean(temp_base["ttc"]))
        results["baseline"]["total_msgs"].append(np.mean(temp_base["msgs"]))
        results["baseline"]["v2v_msgs"].append(np.mean(temp_base["v2v"]))
        results["baseline"]["cost_kb"].append(np.mean(temp_base["cost"]))
        
        results["event"]["collisions"].append(np.mean(temp_event["col"]))
        results["event"]["ttc"].append(np.mean(temp_event["ttc"]))
        results["event"]["total_msgs"].append(np.mean(temp_event["msgs"]))
        results["event"]["v2v_msgs"].append(np.mean(temp_event["v2v"]))
        results["event"]["cost_kb"].append(np.mean(temp_event["cost"]))

    return results

def plot_comparative_results(results):
    x = np.arange(len(results["x_labels"]))
    labels = results["x_labels"]
    
    # 1. Safety Parameters Plot
    plt.figure(figsize=(10, 5))
    plt.plot(x, results["baseline"]["collisions"], 'r--o', label="Baseline: Physical Collisions")
    plt.plot(x, results["event"]["collisions"], 'r-o', label="Event: Physical Collisions")
    plt.plot(x, results["baseline"]["ttc"], 'b--x', label="Baseline: TTC Events")
    plt.plot(x, results["event"]["ttc"], 'b-x', label="Event: TTC Events")
    plt.xticks(x, labels, rotation=45)
    plt.xlabel("Vehicles Per Hour (Highway, On-Ramp)")
    plt.ylabel("Average Count (over 5 seeds)")
    plt.title("Safety Robustness: Physical Collisions & TTC Events")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "plot_1_safety.png"))
    plt.close()

    # 2. Wireless Messages Plot
    plt.figure(figsize=(10, 5))
    plt.plot(x, results["baseline"]["total_msgs"], 'k--o', label="Baseline: Total Messages")
    plt.plot(x, results["event"]["total_msgs"], 'k-o', label="Event: Total Messages")
    plt.plot(x, results["baseline"]["v2v_msgs"], 'm--x', label="Baseline: V2V Messages")
    plt.plot(x, results["event"]["v2v_msgs"], 'm-x', label="Event: V2V Messages")
    plt.xticks(x, labels, rotation=45)
    plt.xlabel("Vehicles Per Hour (Highway, On-Ramp)")
    plt.ylabel("Average Message Count")
    plt.title("Communication Robustness: Number of Messages")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "plot_2_messages.png"))
    plt.close()

    # 3. Communication Cost Plot
    plt.figure(figsize=(10, 5))
    plt.plot(x, results["baseline"]["cost_kb"], 'g--o', label="Baseline: Comm Cost (KB)")
    plt.plot(x, results["event"]["cost_kb"], 'g-o', label="Event: Comm Cost (KB)")
    plt.xticks(x, labels, rotation=45)
    plt.xlabel("Vehicles Per Hour (Highway, On-Ramp)")
    plt.ylabel("Average Cumulative Cost [KB]")
    plt.title("Data Cost Robustness")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "plot_3_comm_cost.png"))
    plt.close()

    print(f"\n[SUCCESS] Comparative plots saved to {OUTPUT_DIR}")
    print(f"[SUCCESS] All raw seed data archived in {RAW_DATA_DIR}")

if __name__ == "__main__":
    data = run_study()
    plot_comparative_results(data)
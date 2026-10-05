# CAV Rule-Based Cooperative Ramp Merging Simulation

Microscopic co-simulation platform for Connected and Autonomous Vehicle (CAV) cooperative highway on-ramp merging using Eclipse SUMO (Simulation of Urban MObility) and Python (TraCI). The framework couples centralized macroscopic virtual platoon sequencing with distributed consensus-driven Cooperative Adaptive Cruise Control (CACC), an event-triggered wireless transmission engine, dead reckoning, and an autonomous radar fail-safe.

Developed for the Undergraduate Minor Project Mid-Semester Progress Evaluation at the Indian Institute of Information Technology (IIIT) Naya Raipur.

---

## Architecture and Control Framework

The system operates across a multi-tier control hierarchy:

1. **Tier 1: Centralized Roadside Unit (RSU) Coordination (0.5 Hz)**
   - Vehicles entering the 368 m coordination horizon upstream of the merge point transmit kinematic telemetry via V2I.
   - The RSU estimates dynamic bottleneck velocity:
     $$v_m = \min\left(v_{limit},\ \frac{L_{ramp}}{t_{crit}}\right)$$
   - The RSU projects kinematic arrival times ($t_{arr, i} = t + \frac{d_{merge, i}}{v_i}$) and assigns a global First-In-First-Out (FIFO) merging sequence. Each vehicle is assigned a virtual predecessor (physical or cross-ramp "ghost" vehicle) and target merge speed $v_m$.

2. **Tier 2: Distributed Consensus CACC (10 Hz Onboard Loop)**
   - Followers execute distributed consensus tracking:
     $$a_i(t) = -k_p \cdot \left(d_{des} - \text{gap}_i(t)\right) - k_v \cdot \left(v_i(t) - v_{pred}(t)\right)$$
     where $k_p = 0.5$, $k_v = 0.8$, and the desired gap adheres to a constant time-headway policy:
     $$d_{des} = d_0 + h_{des} \cdot v_i(t) \quad (d_0 = 10.0\ \text{m},\ h_{des} = 1.2\ \text{s})$$
   - Physical vehicle bounds enforce comfort and traction limits: $a_i \in [-3.0, +2.0]\ \text{m/s}^2$ and $v_i \in [0, 33.33]\ \text{m/s}$.

3. **Tier 3: Rule-Based Event-Triggered V2V Engine & Dead Reckoning**
   - Instead of continuous 10 Hz beaconing, state updates are broadcast only when deviations exceed thresholds:
     $$\Delta v = |v_i(t) - v_i(t_{last})| \ge 0.3\ \text{m/s} \quad \lor \quad \Delta d = |d_i(t) - d_i(t_{last}) - v_i(t_{last})\Delta t| \ge 0.5\ \text{m} \quad \lor \quad (t - t_{last}) \ge 1.0\ \text{s}$$
   - During silent timesteps or dropped packets, receiving CAVs apply constant-velocity dead reckoning:
     $$\hat{d}_{pred}(t) = d_{pred}(t_{last}) + v_{pred}(t_{last})\Delta t$$
     preventing phantom deceleration and preserving string stability.

4. **Tier 4: Autonomous Sensor Fail-Safe Override**
   - Onboard radar continuously monitors physical headway. If Time-to-Collision ($TTC = \frac{\text{gap}}{\Delta v}$) drops below $2.0\ \text{s}$ or physical distance drops below $5.0\ \text{m}$, the system overrides CACC and commands maximum safe deceleration ($-3.0\ \text{m/s}^2$).

---

## Repository Structure

```text
Rule-based-merging-scenario/
├── config/
│   └── merge.config.xml             # SUMO simulation configuration
├── network/
│   ├── merge.net.xml                # Compiled road network (single-lane mainline + on-ramp)
│   ├── merge.edg.xml                # Road edges definition
│   ├── merge.nod.xml                # Network nodes and junction coordinates
│   ├── merge.con.xml                # Lane connection and priority rules
│   ├── merge.typ.xml                # Edge types and speed limits
│   ├── merge.tll.xml                # Traffic light logic (if applicable)
│   └── merge.netccfg                # Netconvert compiler configuration
├── routes/
│   └── merge.rou.xml                # Vehicle flow routes and insertion rates
├── src/
│   ├── analysis/
│   │   ├── aggregate_results.py     # Cross-scenario KPI aggregation tool
│   │   ├── generate_figures.py      # Trajectory, dashboard, and architecture visualizer
│   │   ├── build_deck.py            # Automated slide deck builder
│   │   └── Progress_Presentation_Redesigned_backup.pptx  # Template backup
│   ├── event_based_mech/
│   │   ├── agent.py                 # CAV state tracker with event detection logic
│   │   ├── controller.py            # CACC controller with dead-reckoning support
│   │   ├── infrastructure.py        # RSU virtual platoon coordinator
│   │   └── run_sim.py               # Event-triggered co-simulation runner
│   ├── perfect_comm/
│   │   ├── agent.py                 # Telemetry agent for 10 Hz continuous beaconing
│   │   ├── controller.py            # Baseline CACC controller
│   │   └── infrastructure.py        # Baseline RSU coordinator
│   ├── real_comm/
│   │   ├── agent.py                 # CAV agent with transmission statistics
│   │   ├── channel.py               # Wireless channel modeling (packet loss, latency)
│   │   ├── controller.py            # Controller resilient to packet drops
│   │   └── infrastructure.py        # RSU coordinator under lossy V2I/V2V
│   ├── output/
│   │   ├── event_based_perfect_comm/# Event-triggered run outputs
│   │   ├── perfect_comm/            # 10 Hz periodic baseline outputs
│   │   ├── real_comm/               # Lossy channel simulation outputs
│   │   ├── figures/                 # Generated trajectory and performance plots
│   │   └── benchmark_aggregate.csv  # Consolidated cross-scenario metrics
│   ├── perfect_comm_run_sim.py      # Runner for 10 Hz periodic baseline
│   └── real_comm_run_sim.py         # Runner for lossy channel experiments
├── .env.example                     # Environment configuration template
├── Progress_Presentation_Redesigned.pptx  # 15-slide progress evaluation presentation
├── requirements.txt                 # Python package dependencies
└── README.md                        # Documentation
```

---

## Requirements

- Python 3.10+
- Eclipse SUMO (v1.20+ recommended, tested with v1.27+)
- `SUMO_HOME` environment variable configured or SUMO binaries added to system `PATH`

---

## Installation and Setup

1. **Clone or navigate to the repository directory:**
   ```powershell
   cd Rule-based-merging-scenario
   ```

2. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Or on Windows Command Prompt:
   ```cmd
   .\.venv\Scripts\activate.bat
   ```

3. **Install required dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment settings:**
   Copy `.env.example` to `.env` and verify local settings:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## Configuration (.env)

Available settings in `.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SUMO_HOME` | Path to Eclipse SUMO installation | (auto-detected from system PATH) |
| `SUMO_GUI` | Launch with graphical interface (`true`) or headless (`false`) | `true` |
| `SUMO_CONFIG_PATH` | Path to SUMO configuration file | `config/merge.config.xml` |
| `SIM_STEP_LENGTH` | Simulation step size in seconds | `0.1` |
| `SIM_TIME` | Optional max simulation duration in seconds | `300.0` |
| `SIM_LOG_PATH` | CSV output destination for simulation telemetry | `sim_log.csv` |

---

## Running Simulations

The platform provides three simulation variants:

### 1. Event-Triggered V2V Mechanism (Proposed)
Runs the rule-based event-triggered communication model with constant-velocity dead reckoning:
```powershell
# Run with GUI
python src/event_based_mech/run_sim.py

# Run headless with custom duration and output directory
python src/event_based_mech/run_sim.py --nogui --time 300 --out-dir src/output/event_based_perfect_comm
```

### 2. 10 Hz Periodic V2V Baseline
Runs continuous 10 Hz periodic V2V broadcasting as a benchmark:
```powershell
# Run with GUI
python src/perfect_comm_run_sim.py

# Run headless
python src/perfect_comm_run_sim.py --nogui --time 300 --out-dir src/output/perfect_comm
```

### 3. Real Communication Channel (Loss and Latency Stress-Testing)
Simulates stochastic packet drop rates and communication latency:
```powershell
# Run ideal channel (0% loss)
python src/real_comm_run_sim.py --nogui --loss 0.0 --time 300 --out-dir src/output/real_comm --tag base

# Run moderate loss (10% packet drop)
python src/real_comm_run_sim.py --nogui --loss 0.1 --time 300 --out-dir src/output/real_comm --tag loss10

# Run severe loss (30% packet drop)
python src/real_comm_run_sim.py --nogui --loss 0.3 --time 300 --out-dir src/output/real_comm --tag loss30
```

---

## Results and Visual Analytics

### Aggregate KPI Metrics
To parse all simulation output logs and consolidate metrics into a single table:
```powershell
python src/analysis/aggregate_results.py
```
Output table is written to `src/output/benchmark_aggregate.csv`.

### Generate Publication Figures
To plot microscopic trajectory profiles, velocity convergence, and communication comparison dashboards:
```powershell
python src/analysis/generate_figures.py
```
Generated plots are saved to `src/output/figures/`:
- `performance_comparison_dashboard.png`: V2V transmission overhead and packet delivery ratio under loss.
- `trajectory_and_speed_profiles.png`: Vehicle distance-to-merge trajectory interlocking and velocity convergence to $v_m = 25.0\ \text{m/s}$.
- `system_architecture_pipeline.png`: Block diagram of the multi-tier coordination pipeline.

---

## Empirical Benchmark Summary

Evaluated over a 300.0-second time horizon with 75 CAVs (50 mainline highway, 25 on-ramp, 900 veh/hr inflow):

| Benchmark Scenario | V2V Pkts Sent | Comm Volume [KB] | Bitrate [kbps] | Collisions | TTC Conflicts (<2.0s) | Safety Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 10 Hz Periodic Baseline | 16,129 | 1,147.19 | 31.33 | 0 | 0 | 100% Collision-Free |
| Event-Triggered (Proposed) | **1,677** | **243.94** | **6.66** | **0** | **0** | **100% Collision-Free** |
| Real Comm: 0% Loss | 16,048 | 1,146.81 | 31.25 | 0 | 0 | 100% Collision-Free |
| Real Comm: 10% Loss | 15,876 | 1,031.08 | 28.10 | 0 | 0 | 100% Collision-Free |
| Real Comm: 30% Loss | 15,422 | 808.19 | 22.02 | 0 | 0 | 100% Collision-Free |

### Key Outcomes:
- **89.60% reduction** in V2V communication transmissions.
- **78.73% bandwidth volume savings** (channel bitrate reduced from 31.33 kbps to 6.66 kbps).
- **Zero collisions and zero emergency TTC interventions** across all baseline and lossy scenarios.
- **Dead-reckoning continuity** maintains string stability and gap tracking under communication losses up to 30%.

---

## Progress Presentation

The project slide deck is maintained at:
`Progress_Presentation_Redesigned.pptx`

It features a 15-slide academic structure tailored for the Minor Project Mid-Semester Progress Evaluation at IIIT Naya Raipur.

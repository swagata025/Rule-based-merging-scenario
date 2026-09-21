# CAV Rule-Based Cooperative Ramp Merging Simulation

This repository simulates Connected and Autonomous Vehicle (CAV) cooperative highway ramp merging using Eclipse SUMO (Simulation of Urban MObility) and Python (TraCI), based on consensus-driven Cooperative Adaptive Cruise Control (CACC).

## Requirements

- Python 3.10+
- Eclipse SUMO (installed with `SUMO_HOME` configured or binaries in system PATH)

## Setup

1. Clone or navigate to the repository directory:
   ```powershell
   cd Rule-based-merging-scenario
   ```

2. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Or on Windows Command Prompt:
   ```cmd
   .\.venv\Scripts\activate.bat
   ```

3. Install required Python packages:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env` and adjust paths or options if needed:
   ```powershell
   Copy-Item .env.example .env
   ```

## Configuration (.env)

Available settings in `.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SUMO_HOME` | Path to Eclipse SUMO directory (e.g. `C:\Program Files (x86)\Eclipse\Sumo`) | (auto-detected from PATH) |
| `SUMO_GUI` | Launch with graphical interface (`true`) or headless (`false`) | `true` |
| `SUMO_CONFIG_PATH` | Path to SUMO configuration file | `config/merge.config.xml` |
| `SIM_STEP_LENGTH` | Simulation step size in seconds | `0.1` |
| `SIM_TIME` | Optional max simulation duration in seconds | Unlimited (runs until clear) |
| `SIM_LOG_PATH` | CSV file path for simulation metrics | `sim_log.csv` |

## Running the Simulation

- Run with GUI (default):
  ```powershell
  python src/run_sim.py
  ```

- Run headless (faster execution):
  ```powershell
  python src/run_sim.py --nogui
  ```

- Run for a fixed duration (e.g., 60 seconds) and custom output log:
  ```powershell
  python src/run_sim.py --nogui --time 60 --log metrics.csv
  ```

## Project Structure

- `src/`
  - `run_sim.py`: Simulation runner, orchestrates TraCI loop, sequencing, and control actuations.
  - `agent.py`: `VehicleAgent` tracking physical vehicle telemetry (speed, acceleration, distance to merge).
  - `infrastructure.py`: `InfrastructureCoordinator` scheduling vehicle arrivals and computing virtual sequence.
  - `controller.py`: `LongitudinalController` calculating acceleration commands using ACC and CACC.
- `config/`: SUMO configuration files (`merge.config.xml`).
- `network/`: Road network definitions (`merge.net.xml`, `merge.node.xml`, `merge.edge.xml`).
- `routes/`: Vehicle types and traffic flow volumes (`merge.route.xml`).
- `.env.example`: Template for environment-specific variables.

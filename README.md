# CAV Cooperative Ramp Merging Simulation

This project simulates Connected and Autonomous Vehicle (CAV) cooperative highway ramp merging using Eclipse SUMO (Simulation of Urban MObility) and Python (TraCI).

## Requirements

- Python 3.10+
- Eclipse SUMO (installed and added to PATH / `SUMO_HOME` environment variable configured)

## Setup

1. Clone or navigate to the repository directory:
   ```powershell
   cd project
   ```

2. Activate the existing virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Or on CMD:
   ```cmd
   .\.venv\Scripts\activate.bat
   ```

3. Install required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Simulation

Ensure Eclipse SUMO is installed on your machine so the `sumo-gui` or `sumo` binaries are available in your PATH.

- Run with SUMO GUI:
  ```powershell
  python src/run_sim.py
  ```

- Run in headless mode (without GUI):
  ```powershell
  python src/run_sim.py --nogui
  ```

## Project Structure

- `src/`
  - `run_sim.py`: Main simulation loop connecting to TraCI, managing vehicle agents, and executing control actions.
  - `agent.py`: `VehicleAgent` tracking physical vehicle states (speed, position, distance to merge).
  - `infrastructure.py`: `InfrastructureCoordinator` scheduling vehicle arrivals and establishing merge sequence.
  - `controller.py`: `LongitudinalController` calculating acceleration commands using ACC and CACC.
- `config/`: SUMO configuration files (`merge.config.xml`).
- `network/`: SUMO road network definition (`merge.net.xml`, `merge.node.xml`, `merge.edge.xml`).
- `routes/`: SUMO traffic and vehicle definitions (`merge.route.xml`).

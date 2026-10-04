import traci


class VehicleAgent:
    """One CAV. Reads its own state from SUMO ONCE per step (call update_state once, reuse the dict)."""

    # Internal-lane (junction) length depends on which approach the vehicle came from.
    # Measured the first time a vehicle of that origin is seen inside the junction, then shared.
    JUNCTION_LEN = {"main": 8.0, "ramp": 8.0}

    def __init__(self, veh_id):
        self.id = veh_id
        self.origin = None          # "main" | "ramp"  (where it entered the network)
        self.lane = None            # "main" | "ramp" | "junction" | "out"
        self.speed = 0.0
        self.accel = 0.0
        self.pos = 0.0
        self.dist_to_merge = None   # >0 before the merge point, <0 after it
        self.length = 5.0
        self.entered_v2i = False    # has the infrastructure been told about this vehicle yet?

    def update_state(self):
        self.speed = traci.vehicle.getSpeed(self.id)
        self.accel = traci.vehicle.getAcceleration(self.id)
        self.pos = traci.vehicle.getLanePosition(self.id)
        self.length = traci.vehicle.getLength(self.id)

        edge_id = traci.vehicle.getRoadID(self.id)
        lane_id = traci.vehicle.getLaneID(self.id)

        if edge_id in ("main_in", "ramp_in"):
            self.origin = "main" if edge_id == "main_in" else "ramp"
            self.lane = self.origin
            # actual (junction-truncated) lane length, not the nominal edge length
            self.dist_to_merge = traci.lane.getLength(lane_id) - self.pos
        elif edge_id.startswith(":"):
            self.lane = "junction"
            VehicleAgent.JUNCTION_LEN[self.origin] = traci.lane.getLength(lane_id)
            self.dist_to_merge = -self.pos
        else:
            self.lane = "out"
            self.dist_to_merge = -(VehicleAgent.JUNCTION_LEN[self.origin] + self.pos)

        return {
            "id": self.id, "lane": self.lane, "origin": self.origin,
            "speed": self.speed, "accel": self.accel, "pos": self.pos,
            "dist_to_merge": self.dist_to_merge, "length": self.length,
        }
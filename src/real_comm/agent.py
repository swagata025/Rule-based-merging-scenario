import traci
from real_comm.controller import LongitudinalController

class VehicleAgent:
    """One CAV. Reads its own state from SUMO ONCE per step (call update_state once, reuse the dict)."""

    # Internal-lane (junction) length depends on which approach the vehicle came from.
    # Measured the first time a vehicle of that origin is seen inside the junction, then shared.
    JUNCTION_LEN = {"main": 8.0, "ramp": 8.0}

    def __init__(self, veh_id, dt):
        self.id = veh_id
        self.origin = None          # "main" | "ramp"  (where it entered the network)
        self.lane = None            # "main" | "ramp" | "junction" | "out"
        self.speed = 0.0
        self.accel = 0.0
        self.pos = 0.0
        self.dist_to_merge = None   # >0 before the merge point, <0 after it
        self.length = 5.0
        self.sequenced = False      # becomes True once an RSU downlink arrives
        self.pred_id = None
        self.v_m = 24.0             # prior (0.8*v_lim) until the first downlink
        self.pred_msg = None        # last V2V snapshot of the predecessor
        self.down_ts = -1.0
        self.controller = LongitudinalController(dt=dt)
    def on_downlink(self, m):
        if m["ts"] < self.down_ts:               # jitter can reorder packets
            return
        self.down_ts, self.sequenced, self.v_m = m["ts"], True, m["v_m"]
        if m["pred"] != self.pred_id:
            self.pred_id, self.pred_msg = m["pred"], None   # old data is irrelevant now

    def on_v2v(self, m):
        if m["from"] != self.pred_id:
            return
        if self.pred_msg and m["ts"] <= self.pred_msg["ts"]:
            return
        self.pred_msg = m

    def predecessor_estimate(self, now, max_age=1.0):
        m = self.pred_msg
        if m is None or now - m["ts"] > max_age:  # nothing, or too stale to trust
            return None
        age = now - m["ts"]
        return {"id": m["from"], "speed": m["speed"], "length": m["length"],
            "dist_to_merge": m["dist_to_merge"] - m["speed"] * age}   # extrapolate
    
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
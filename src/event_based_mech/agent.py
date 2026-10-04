import traci


class VehicleAgent:
    """One CAV. Reads its own state from SUMO at 10 Hz, but only broadcasts V2V
    packets when an event threshold (speed change, position drift, lane transition,
    or max-silence heartbeat) is crossed."""

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

        # ---- Event-Based V2V Communication Memory ----
        self.last_broadcast_time = None
        self.last_broadcast_state = None
        self.broadcast_count = 0
        self.possible_steps = 0

    def update_state(self):
        """Reads local onboard sensors (10 Hz). Does NOT mean a V2V packet is sent."""
        self.speed = traci.vehicle.getSpeed(self.id)
        self.accel = traci.vehicle.getAcceleration(self.id)
        self.pos = traci.vehicle.getLanePosition(self.id)
        self.length = traci.vehicle.getLength(self.id)

        edge_id = traci.vehicle.getRoadID(self.id)
        lane_id = traci.vehicle.getLaneID(self.id)

        if edge_id in ("main_in", "ramp_in"):
            self.origin = "main" if edge_id == "main_in" else "ramp"
            self.lane = self.origin
            self.dist_to_merge = traci.lane.getLength(lane_id) - self.pos
        elif edge_id.startswith(":"):
            self.lane = "junction"
            VehicleAgent.JUNCTION_LEN[self.origin] = traci.lane.getLength(lane_id)
            self.dist_to_merge = -self.pos
        else:
            self.lane = "out"
            # Use a single common reference once on the shared 'out' edge so ramp and main
            # vehicles on the exact same physical lane have zero coordinate offset.
            self.dist_to_merge = -(VehicleAgent.JUNCTION_LEN["main"] + self.pos)

        return {
            "id": self.id, "lane": self.lane, "origin": self.origin,
            "speed": self.speed, "accel": self.accel, "pos": self.pos,
            "dist_to_merge": self.dist_to_merge, "length": self.length,
        }

    def check_and_broadcast_v2v(self, current_time, current_state, v_th=0.3, d_th=0.5, max_silence=1.0):
        """Evaluates the event-trigger conditions.
        Returns True if a V2V packet is broadcasted at this step, False otherwise."""
        self.possible_steps += 1

        # Event 0: First time on the network -> must broadcast initial state
        if self.last_broadcast_state is None:
            self.last_broadcast_time = current_time
            self.last_broadcast_state = current_state.copy()
            self.broadcast_count += 1
            return True

        dt_since_last = current_time - self.last_broadcast_time
        last_v = self.last_broadcast_state["speed"]
        last_d = self.last_broadcast_state["dist_to_merge"]

        # Expected distance-to-merge under constant-velocity dead reckoning
        predicted_d = last_d - last_v * dt_since_last

        speed_err = abs(current_state["speed"] - last_v)
        dist_err = abs(current_state["dist_to_merge"] - predicted_d)
        lane_changed = current_state["lane"] != self.last_broadcast_state["lane"]

        # Trigger if edge/lane changed, speed changed >= v_th, position drifted >= d_th, or heartbeat expired
        if lane_changed or speed_err >= v_th or dist_err >= d_th or dt_since_last >= max_silence - 1e-6:
            self.last_broadcast_time = current_time
            self.last_broadcast_state = current_state.copy()
            self.broadcast_count += 1
            return True

        return False

    def get_broadcasted_state(self, current_time, use_dead_reckoning=True):
        """Returns the state that a follower knows about this vehicle via V2V.
        With use_dead_reckoning=True (default), the follower extrapolates dist_to_merge
        using the last broadcasted speed so the predecessor doesn't appear stationary
        during silent steps between events."""
        if self.last_broadcast_state is None:
            return None
        pkt = self.last_broadcast_state.copy()
        if use_dead_reckoning and self.last_broadcast_time is not None:
            dt_elapsed = current_time - self.last_broadcast_time
            pkt["dist_to_merge"] = pkt["dist_to_merge"] - pkt["speed"] * dt_elapsed
        return pkt
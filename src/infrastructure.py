import math
from collections import deque


def travel_time(s, v0, v_target, a_acc, a_dec):
    """Time to cover distance s, starting at v0, moving toward v_target with constant
    acceleration a_acc (or deceleration a_dec) and cruising at v_target once reached.
    This is the linear-acceleration profile of the paper (eq. 3-4), written once so it works
    for the accelerating ramp car and the (slightly) decelerating highway car alike."""
    v0 = max(v0, 0.1)
    v_target = max(v_target, 0.1)
    if abs(v_target - v0) < 1e-6:
        return s / v0
    acc = a_acc if v_target > v0 else -a_dec
    s_change = (v_target ** 2 - v0 ** 2) / (2.0 * acc)      # distance needed to reach v_target
    if s >= s_change:
        return (v_target - v0) / acc + (s - s_change) / v_target
    v_end = math.sqrt(max(v0 ** 2 + 2.0 * acc * s, 0.01))    # never reaches v_target before the merge
    return (v_end - v0) / acc


class InfrastructureCoordinator:
    """Roadside unit implementing the sequencing protocol of Wang et al. (arXiv:1810.09952).

    1. Vehicles report (speed, distance-to-merge) when they enter V2I range.
    2. Every `sort_period` seconds (set in run_sim.py) the RSU
         a) updates the estimated MERGE SPEED v_m from window-averaged entry speeds (eq. 1-2),
         b) computes an ETA for every NEW vehicle using v_m (eq. 3-4),
         c) enforces same-lane FIFO + a t_head_safe slot between consecutive vehicles,
         d) INSERTS the new vehicles into the sequence.
    3. The order of vehicles already in the sequence is never changed (the paper: re-sorting
       frequently destabilises the longitudinal control).
    """

    def __init__(self, v_lim=30.0, a_max=2.6, a_dec=2.0, t_head_safe=1.5, veh_length=5.0,
                 ramp_len=368.0, window=10.0, vm_deadband=1.0, vm_gain=0.5):
        self.v_lim = v_lim
        self.a_max = a_max
        self.a_dec = a_dec
        self.t_head_safe = t_head_safe
        self.veh_length = veh_length
        self.s_r = ramp_len              # distance of a ramp vehicle to the merge at V2I entry
        self.window = window             # averaging window [s]
        self.vm_deadband = vm_deadband   # v_m only moves if the new estimate differs by more than this
        self.vm_gain = vm_gain           # ... and then only part of the way (low-pass)

        self.hs_window = deque()         # (t, speed) of highway vehicles entering V2I range
        self.rs_window = deque()
        self._v_hs_last = None
        self._v_rs_last = None
        self.v_m = 0.8 * v_lim           # estimated merging speed (slow-changing); prior until 1st estimate
        self._have_vm = False

        self.pending = {}                # vehicles that entered since the last sort
        self.sequence = []               # ordered list of dicts: id, lane, t (assigned arrival time)
        self._pred = {}

    # ------------------------------------------------------------------ V2I interface
    def receive_vehicle_data(self, veh_id, lane, speed, distance, current_time, first_contact):
        """Vehicle -> RSU. Called every step until the vehicle has been sequenced."""
        if lane not in ("main", "ramp"):
            return
        if first_contact:
            (self.hs_window if lane == "main" else self.rs_window).append((current_time, speed))
        if veh_id not in self._pred:     # not yet sequenced -> keep latest state for the next sort
            self.pending[veh_id] = {"id": veh_id, "lane": lane, "speed": speed, "dist": distance}

    def remove_vehicle(self, veh_id):
        self.pending.pop(veh_id, None)
        self.sequence = [e for e in self.sequence if e["id"] != veh_id]
        self._rebuild()

    def get_predecessor(self, veh_id):
        return self._pred.get(veh_id)

    def get_sequence_id(self, veh_id):
        for i, e in enumerate(self.sequence, start=1):
            if e["id"] == veh_id:
                return i
        return None

    # ------------------------------------------------------------------ merge speed (eq. 1-2)
    def _update_merge_speed(self, t):
        for w in (self.hs_window, self.rs_window):
            while w and t - w[0][0] > self.window:
                w.popleft()
        if self.hs_window:
            self._v_hs_last = sum(v for _, v in self.hs_window) / len(self.hs_window)
        if self.rs_window:
            self._v_rs_last = sum(v for _, v in self.rs_window) / len(self.rs_window)
        v_hs = self._v_hs_last if self._v_hs_last is not None else self.v_lim
        v_rs = self._v_rs_last if self._v_rs_last is not None else 0.5 * self.v_lim

        s_acc = (self.v_lim ** 2 - v_rs ** 2) / (2.0 * self.a_max)                   # eq. (1)
        if s_acc <= self.s_r:                                                        # can reach v_lim
            v_rm_max = self.v_lim
        else:
            v_rm_max = math.sqrt(v_rs ** 2 + 2.0 * self.a_max * self.s_r)            # eq. (2)
        raw = min(v_rm_max, v_hs)                                                    # bottleneck speed

        if not self._have_vm:
            self.v_m, self._have_vm = raw, True
        elif abs(raw - self.v_m) > self.vm_deadband:                                 # don't chase noise
            self.v_m += self.vm_gain * (raw - self.v_m)

    # ------------------------------------------------------------------ sequencing (eq. 3-4)
    def run_sorting_algorithm(self, current_time):
        self._update_merge_speed(current_time)
        if not self.pending:
            return
        slot = self.t_head_safe + self.veh_length / max(self.v_m, 1.0)   # time headway incl. car length

        new = []
        for d in self.pending.values():
            eta = travel_time(d["dist"], d["speed"], self.v_m, self.a_max, self.a_dec)
            new.append({"id": d["id"], "lane": d["lane"], "t": current_time + eta})
        # earliest first; on an exact tie the highway vehicle keeps priority (paper)
        new.sort(key=lambda e: (e["t"], e["lane"] == "ramp"))

        for c in new:
            last_same = max((i for i, e in enumerate(self.sequence) if e["lane"] == c["lane"]), default=-1)
            if last_same >= 0:                                   # same-lane FIFO + headway
                c["t"] = max(c["t"], self.sequence[last_same]["t"] + slot)
            idx = len(self.sequence)
            while idx > 0 and self.sequence[idx - 1]["t"] > c["t"]:
                idx -= 1
            idx = max(idx, last_same + 1)                        # never jump ahead of a same-lane car
            if idx > 0:
                c["t"] = max(c["t"], self.sequence[idx - 1]["t"] + slot)
            self.sequence.insert(idx, c)
            for j in range(idx + 1, len(self.sequence)):         # keep slots; ORDER stays untouched
                need = self.sequence[j - 1]["t"] + slot
                if self.sequence[j]["t"] < need:
                    self.sequence[j]["t"] = need
                else:
                    break
        self.pending.clear()
        self._rebuild()

    def _rebuild(self):
        self._pred = {}
        for i, e in enumerate(self.sequence):
            self._pred[e["id"]] = self.sequence[i - 1]["id"] if i > 0 else None
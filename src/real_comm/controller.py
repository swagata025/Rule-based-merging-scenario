class LongitudinalController:
    """Distributed-consensus CACC (paper eq. 5) + time-to-collision fail-safe (paper eq. 6).

        a = -delta * [ (d_des - gap) + gamma * (v - v_pred) ]        (= -kp*pos_err - kv*speed_err)

    * `gap` is measured to the predecessor along the *virtual* (ghost) axis, i.e. using
      distance-to-merge, so it works whether the predecessor is on the same lane or not.
    * With no predecessor the vehicle just holds the slowly-varying merge speed v_m (NOT v_lim:
      chasing v_lim is what produced the "sudden acceleration at the merge point").
    * Everything is bounded by a comfort range and a symmetric jerk limit, so the command
      is smooth.
    * TTC never blends into the control law; it only hands control back to SUMO's built-in
      car-following when a collision is genuinely imminent (paper's fail-safe).
    """

    def __init__(self, dt=0.1):
        self.dt = dt
        # consensus gains (kp = delta, kv = delta*gamma). zeta = kv / (2*sqrt(kp)) ~ 1 -> no oscillation
        self.k_p = 0.15
        self.k_v = 0.80
        self.t_head_safe = 1.5       # desired time headway            [s]
        self.s_head_safe = 5.0       # minimum standstill gap          [m]
        self.v_lim = 30.0
        self.a_comf_max = 2.0        # comfortable acceleration        [m/s^2]
        self.a_comf_min = -3.0       # comfortable deceleration        [m/s^2]
        self.j_max = 2.5             # jerk limit, both directions     [m/s^3]
        self.ttc_on = 2.0            # fail-safe engages below this TTC [s]   (paper: 2 s)
        self.ttc_off = 3.5           # ...and releases above this (hysteresis)
        self.prev_a = None
        self.failsafe = False

    # ---------------------------------------------------------------- consensus law
    def compute_acceleration(self, ego, predecessor, v_free):
        v = ego["speed"]
        d_des = max(v * self.t_head_safe, self.s_head_safe)

        if predecessor:
            gap = ego["dist_to_merge"] - predecessor["dist_to_merge"] - predecessor["length"]
            a = -self.k_p * (d_des - gap) - self.k_v * (v - predecessor["speed"])
        else:
            a = self.k_v * (v_free - v)

        # Never chase a distant predecessor above the (slow-changing) merge speed: consensus is used to
        # OPEN gaps (slow down), not to close large ones (speed up). Also never exceed v_lim.
        v_cap = min(v_free, self.v_lim)
        a = min(a, self.k_v * (v_cap - v))
        a = max(self.a_comf_min, min(a, self.a_comf_max))

        prev = self.prev_a if self.prev_a is not None else ego["accel"]          # first call: start from real accel
        step = self.j_max * self.dt
        a = max(prev - step, min(a, prev + step))                  # symmetric jerk limit
        self.prev_a = a
        return a

    # ---------------------------------------------------------------- TTC fail-safe
    def failsafe_active(self, ego, leader):
        ttc = float("inf")
        if leader is not None and ego["speed"] > leader["speed"]:
            ttc = leader["gap"] / (ego["speed"] - leader["speed"])
        if self.failsafe:
            if ttc > self.ttc_off:
                self.failsafe = False
        elif ttc < self.ttc_on:
            self.failsafe = True
        return self.failsafe

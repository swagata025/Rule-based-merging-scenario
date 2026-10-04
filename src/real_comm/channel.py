import random
import itertools
import heapq

class Channel:
    def __init__(self, loss=0.0, base_delay=0.0, jitter=0.0, seed=None):
        self.loss, self.base, self.jitter = loss, base_delay, jitter
        self.rng = random.Random(seed)       # reproducible runs
        self.queue, self._n = [], itertools.count()
        self.sent = self.dropped = 0

    def send(self, msg, now):                
        self.sent += 1
        if self.rng.random() < self.loss:
            self.dropped += 1
            return
        t_deliver = now + self.base + self.rng.uniform(0, self.jitter)
        heapq.heappush(self.queue, (t_deliver, next(self._n), msg))

    def receive(self, now):
        out = []
        while self.queue and self.queue[0][0] <= now + 1e-9:
            out.append(heapq.heappop(self.queue)[2])
        return out
"""DGIM: at most two power-of-two buckets per size; newest bucket first."""


class DGIM:
    def __init__(self, window=10_000):
        if window <= 0:
            raise ValueError("window must be positive")
        self.window, self.time = window, 0
        self.buckets = []  # (number of ones, timestamp of newest one)

    def add(self, bit):
        if bit not in (0, 1):
            raise ValueError("DGIM accepts only 0 or 1")
        self.time += 1  # Zeros also advance the event-count window.
        cutoff = self.time - self.window
        while self.buckets and self.buckets[-1][1] <= cutoff:
            self.buckets.pop()
        if bit == 0:
            return
        self.buckets.insert(0, (1, self.time))
        size = 1
        while True:
            indexes = [i for i, b in enumerate(self.buckets) if b[0] == size]
            if len(indexes) <= 2:
                break
            newer, older = indexes[-2], indexes[-1]
            # Keep the end timestamp of the more recent of the merged buckets.
            self.buckets[newer] = (2 * size, self.buckets[newer][1])
            del self.buckets[older]
            size *= 2

    def estimate(self):
        if not self.buckets:
            return 0.0
        total = sum(size for size, _ in self.buckets)
        if self.time <= self.window:
            return float(total)  # No observations have expired yet.
        oldest = self.buckets[-1][0]
        # A size-one bucket is a single known in-window observation.
        return float(total) if oldest == 1 else total - oldest / 2


class ExactWindow:
    """Exact byte-per-event circular buffer; O(1) update and query."""
    def __init__(self, window):
        if window <= 0:
            raise ValueError("window must be positive")
        self.array = bytearray(window)
        self.position = 0
        self.total = 0

    def add(self, bit):
        self.total += bit - self.array[self.position]
        self.array[self.position] = bit
        self.position = (self.position + 1) % len(self.array)

    def estimate(self):
        return self.total

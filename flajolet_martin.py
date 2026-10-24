"""Chapter-4 trailing-zero FM estimator, with a median of group means.

This is the maximum-trailing-zero teaching variant. It is not the original
first-zero bitmap estimator; no 0.77351 bitmap correction is applied.
"""
import hashlib
import statistics


class FlajoletMartin:
    def __init__(self, hashes=16, seed=42):
        groups = {1: 1, 16: 4, 64: 8}
        if hashes not in groups:
            raise ValueError("hashes must be 1, 16 or 64")
        self.hashes = hashes
        self.groups = groups[hashes]
        self.max_zeros = bytearray(hashes)
        self.keys = [(seed + i).to_bytes(8, "big") for i in range(hashes)]
        self.seen_any = False

    def add(self, value):
        self.seen_any = True
        raw = value.encode("utf-8")
        for i, key in enumerate(self.keys):
            h = int.from_bytes(hashlib.blake2b(raw, digest_size=8, key=key).digest(), "big")
            zeros = (h & -h).bit_length() - 1 if h else 64
            if zeros > self.max_zeros[i]:
                self.max_zeros[i] = zeros

    def estimate(self):
        if not self.seen_any:
            return 0.0
        width = self.hashes // self.groups
        means = [sum(2.0 ** r for r in self.max_zeros[j:j + width]) / width
                 for j in range(0, self.hashes, width)]
        return statistics.median(means)

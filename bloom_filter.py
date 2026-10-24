"""Bloom membership filter with a packed bit array and deterministic hashes."""
import hashlib
import math


class BloomFilter:
    def __init__(self, bits=1_048_576, hashes=7, seed=42):
        if bits <= 0 or hashes <= 0:
            raise ValueError("bits and hashes must be positive")
        self.bits, self.hashes = bits, hashes
        self.array = bytearray((bits + 7) // 8)
        self.keys = [(seed + i).to_bytes(8, "big") for i in range(hashes)]

    def _positions(self, value):
        raw = value.encode("utf-8")
        for key in self.keys:
            digest = hashlib.blake2b(raw, digest_size=8, key=key).digest()
            yield int.from_bytes(digest, "big") % self.bits

    def contains(self, value):
        return all(self.array[p // 8] & (1 << (p % 8))
                   for p in self._positions(value))

    def add(self, value):
        for p in self._positions(value):
            self.array[p // 8] |= 1 << (p % 8)

    def check_and_add(self, value):
        """Query BEFORE insertion; compute all positions only once."""
        present = True
        for p in self._positions(value):
            mask = 1 << (p % 8)
            if not self.array[p // 8] & mask:
                present = False
            self.array[p // 8] |= mask
        return present

    def predicted_fpr(self, distinct_inserted):
        """Approximate FPR at current occupancy, not cumulative online FPR."""
        return (1 - math.exp(-self.hashes * distinct_inserted / self.bits)) ** self.hashes

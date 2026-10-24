"""Deterministic correctness checks; synthetic fixtures are tests, not results."""
import itertools
import random
import tempfile
from pathlib import Path
import unittest

from bloom_filter import BloomFilter
from flajolet_martin import FlajoletMartin
from dgim import DGIM, ExactWindow
from stream import parse_line, events


class BloomTests(unittest.TestCase):
    def test_membership_and_no_false_negatives(self):
        b = BloomFilter(1024, 4)
        self.assertFalse(b.contains("alpha"))
        for i in range(300):
            b.add(str(i))
        self.assertTrue(all(b.contains(str(i)) for i in range(300)))

    def test_query_before_insertion_and_reproducibility(self):
        a, b = BloomFilter(64, 7), BloomFilter(64, 7)
        for item in ["a", "b", "a", "c"]:
            previous = a.contains(item)
            self.assertEqual(a.check_and_add(item), previous)
            b.add(item)
        self.assertEqual(a.array, b.array)
        self.assertTrue(a.check_and_add("a"))

    def test_saturation_still_has_no_false_negatives(self):
        b = BloomFilter(1, 2)
        b.add("a")
        self.assertTrue(b.contains("a"))
        self.assertTrue(b.contains("unseen"))

    def test_invalid_parameters(self):
        for bits, hashes in [(0, 1), (10, 0), (-1, 3)]:
            with self.assertRaises(ValueError):
                BloomFilter(bits, hashes)


class FMTests(unittest.TestCase):
    def test_empty_and_duplicate_invariance(self):
        f = FlajoletMartin()
        self.assertEqual(f.estimate(), 0)
        f.add("host")
        registers = bytes(f.max_zeros)
        estimate = f.estimate()
        for _ in range(100):
            f.add("host")
        self.assertEqual(registers, bytes(f.max_zeros))
        self.assertEqual(estimate, f.estimate())

    def test_matches_independent_trailing_zero_calculation(self):
        import hashlib
        f = FlajoletMartin(16, 73)
        values = [f"host-{i}" for i in range(100)]
        for v in values:
            f.add(v)
        expected = []
        for key in f.keys:
            bits = [format(int.from_bytes(hashlib.blake2b(v.encode(), key=key,
                    digest_size=8).digest(), "big"), "064b") for v in values]
            expected.append(max(len(s) - len(s.rstrip("0")) for s in bits))
        self.assertEqual(list(f.max_zeros), expected)

    def test_order_invariance_and_fixed_memory(self):
        a, b = FlajoletMartin(64), FlajoletMartin(64)
        for i in range(300):
            a.add(str(i))
        for i in reversed(range(300)):
            b.add(str(i))
        self.assertEqual(a.max_zeros, b.max_zeros)
        self.assertEqual(len(a.max_zeros), 64)

    def test_invalid_hash_count(self):
        with self.assertRaises(ValueError):
            FlajoletMartin(3)


class DGIMTests(unittest.TestCase):
    def check_stream(self, bits, window):
        sketch, exact, history = DGIM(window), ExactWindow(window), []
        for bit in bits:
            sketch.add(bit)
            exact.add(bit)
            history.append(bit)
            truth = sum(history[-window:])
            self.assertEqual(exact.estimate(), truth)
            if truth == 0:
                self.assertEqual(sketch.estimate(), 0)
            self.assertLessEqual(abs(sketch.estimate() - truth), 0.5 * truth)
            sizes = [size for size, _ in sketch.buckets]
            ends = [end for _, end in sketch.buckets]
            self.assertEqual(sizes, sorted(sizes))
            self.assertEqual(ends, sorted(ends, reverse=True))
            self.assertTrue(all(s > 0 and s & (s - 1) == 0 for s in sizes))
            self.assertTrue(all(sizes.count(s) <= 2 for s in set(sizes)))
            self.assertTrue(all(end > sketch.time - window for end in ends))

    def test_exhaustive_short_sequences(self):
        for window in [1, 2, 3, 5, 8, 16]:
            for bits in itertools.product([0, 1], repeat=9):
                self.check_stream(bits, window)

    def test_zeros_ones_alternation_and_sparse_events(self):
        for bits in [[0] * 200, [1] * 200, [0, 1] * 100,
                     [1] + [0] * 198 + [1]]:
            for window in [1, 10, 100]:
                self.check_stream(bits, window)

    def test_random_stream_and_boundary_expiration(self):
        rng = random.Random(101)
        self.check_stream([int(rng.random() < 0.17) for _ in range(2000)], 97)
        d = DGIM(4)
        for b in [1, 0, 0, 0]:
            d.add(b)
        self.assertEqual(d.estimate(), 1)
        d.add(0)
        self.assertEqual(d.estimate(), 0)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            DGIM(0)
        with self.assertRaises(ValueError):
            DGIM().add(2)


class ParserTests(unittest.TestCase):
    LINE = 'host - - [01/Jul/1995:00:00:01 -0400] "GET / HTTP/1.0" 404 -'

    def test_real_format_and_unknown_bytes(self):
        e = parse_line(self.LINE)
        self.assertEqual(e.host, "host")
        self.assertEqual(e.error, 1)
        self.assertIsNone(e.bytes_sent)
        self.assertEqual(parse_line(self.LINE.replace("404 -", "304 0")).error, 0)

    def test_reject_bad_records(self):
        for line in ["broken", self.LINE.replace("01/Jul", "32/Jul"),
                     self.LINE.replace("404 -", "999 1")]:
            self.assertIsNone(parse_line(line))

    def test_limit_counts_valid_rows_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "input.log"
            p.write_text("broken\n" + self.LINE + "\n" +
                         self.LINE.replace("host", "second") + "\n")
            stats = {}
            self.assertEqual([e.host for e in events(p, 1, stats)], ["host"])
            self.assertEqual(stats["skipped"], 1)
            self.assertEqual(stats["valid"], 1)


if __name__ == "__main__":
    unittest.main()

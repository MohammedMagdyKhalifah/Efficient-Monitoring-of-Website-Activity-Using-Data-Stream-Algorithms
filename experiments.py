"""Replay bounded batches, measure algorithm state, export honest comparisons."""
from collections import deque
import csv
import gc
import itertools
import math
import platform
import statistics
import sys
from time import perf_counter
from pathlib import Path

from bloom_filter import BloomFilter
from flajolet_martin import FlajoletMartin
from dgim import DGIM, ExactWindow
from stream import DATA, ROOT, events, write_json, checksum

SEEDS = [7, 19, 42, 73, 101]
RESULTS = ROOT / "results"


def deep_size(value, seen=None):
    """Reachable state in bytes; count each referenced object once per state.

    This includes Python overhead. It excludes interpreter/code objects,
    temporary update allocations, the input batch, and the validation state.
    """
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    total = sys.getsizeof(value)
    if isinstance(value, dict):
        total += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set, frozenset, deque)):
        total += sum(deep_size(v, seen) for v in value)
    elif hasattr(value, "__dict__"):
        total += deep_size(vars(value), seen)
    return total


def write_csv(path, rows):
    if not rows:
        raise ValueError("No result rows")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_case(kind, params=None, limit=None, seed=42, path=DATA, capture=False,
             targets=None):
    """The same parsed batches feed separate approximate and exact states.

    Timing excludes parsing, comparisons and deep_size. It includes state
    updates and queries. Query cadence is 1000 events (also the bounded batch
    size); Bloom membership is naturally queried on EVERY event.
    """
    params = params or {}
    if kind == "bloom":
        sketch, exact = BloomFilter(seed=seed, **params), set()
    elif kind == "fm":
        sketch, exact = FlajoletMartin(seed=seed, **params), set()
    elif kind == "dgim":
        sketch = DGIM(**params)
        exact = ExactWindow(sketch.window)
    else:
        raise ValueError(kind)
    n = fp = negatives = false_negatives = 0
    approx_seconds = exact_seconds = 0.0
    errors, absolute_errors, history, snapshots = [], [], [], []
    targets = set(targets or [])
    stats = {}
    iterator = iter(events(path, limit, stats))
    final_snapshot = None
    while True:
        batch = list(itertools.islice(iterator, 1000))
        if not batch:
            break
        values = [e.error if kind == "dgim" else e.host for e in batch]
        start = perf_counter()
        if kind == "bloom":
            approximate_answers = [sketch.check_and_add(v) for v in values]
        else:
            for v in values:
                sketch.add(v)
            estimate = sketch.estimate()
        approx_seconds += perf_counter() - start
        start = perf_counter()
        if kind == "bloom":
            exact_answers = []
            for v in values:
                exact_answers.append(v in exact)
                exact.add(v)
        elif kind == "fm":
            for v in values:
                exact.add(v)
            truth = len(exact)
        else:
            for v in values:
                exact.add(v)
            truth = exact.estimate()
        exact_seconds += perf_counter() - start
        n += len(batch)
        if kind == "bloom":
            for predicted, actual in zip(approximate_answers, exact_answers):
                negatives += int(not actual)
                fp += int(predicted and not actual)
                false_negatives += int(actual and not predicted)
            truth, estimate = len(exact), None
            error = fp / negatives if negatives else 0.0
            absolute = None
        else:
            absolute = abs(estimate - truth)
            error = absolute / truth if truth else (0.0 if estimate == 0 else None)
            if error is not None:
                errors.append(error)
            absolute_errors.append(absolute)
        if capture:
            history.append(dict(events=n, exact=truth, estimate=estimate,
                                relative_error=error, absolute_error=absolute))
        if n in targets or (limit is not None and n == limit):
            final_snapshot = dict(events=n, exact=truth, estimate=estimate,
                relative_error=error, approximate_seconds=approx_seconds,
                exact_seconds=exact_seconds, state_bytes=deep_size(sketch),
                exact_state_bytes=deep_size(exact))
            snapshots.append(final_snapshot)
    if n == 0:
        raise ValueError("The input contains no valid events")
    # Include the actual EOF, even if it was not a multiple of 1000.
    if not final_snapshot or final_snapshot["events"] != n:
        snapshots.append(dict(events=n, exact=truth, estimate=estimate,
            relative_error=error, approximate_seconds=approx_seconds,
            exact_seconds=exact_seconds, state_bytes=deep_size(sketch),
            exact_state_bytes=deep_size(exact)))
    row = dict(algorithm=kind, events=n, seed=seed, bits=sketch.bits if kind == "bloom" else "",
        hashes=params.get("hashes", 7 if kind == "bloom" else 16 if kind == "fm" else ""),
        window=params.get("window", 10_000 if kind == "dgim" else ""),
        exact=truth, estimate=estimate, relative_error=error,
        mean_checkpoint_relative_error=statistics.mean(errors) if errors else None,
        mean_checkpoint_absolute_error=statistics.mean(absolute_errors) if absolute_errors else None,
        false_positives=fp, negative_queries=negatives, false_negatives=false_negatives,
        final_theoretical_fpr=sketch.predicted_fpr(len(exact)) if kind == "bloom" else None,
        state_bytes=deep_size(sketch), exact_state_bytes=deep_size(exact),
        ideal_payload_bytes=((sketch.bits + 7) // 8 if kind == "bloom" else
                             sketch.hashes if kind == "fm" else None),
        exact_packed_window_bytes=math.ceil(sketch.window / 8) if kind == "dgim" else None,
        approximate_seconds=approx_seconds, exact_seconds=exact_seconds,
        throughput=n / approx_seconds, exact_throughput=n / exact_seconds,
        buckets=len(sketch.buckets) if kind == "dgim" else None,
        skipped_lines=stats["skipped"])
    return row, history, snapshots


def run_experiments(path=DATA):
    RESULTS.mkdir(exist_ok=True)
    sweep = []
    configurations = [("bloom", {"bits": m, "hashes": k})
                      for m in [65_536, 262_144, 1_048_576] for k in [2, 4, 7]]
    configurations += [("fm", {"hashes": k}) for k in [1, 16, 64]]
    configurations += [("dgim", {"window": n}) for n in [1000, 10_000, 100_000]]
    for kind, params in configurations:
        for seed in ([42] if kind == "dgim" else SEEDS):
            row, _, _ = run_case(kind, params, 100_000, seed, path)
            sweep.append(row)
        print("Parameter sweep:", kind, params, flush=True)
        write_csv(RESULTS / "parameter_sweep.csv", sweep)
    # A full pass per algorithm and repetition also provides cumulative timing
    # at each requested prefix, avoiding redundant replays of shorter prefixes.
    scaling, defaults, full_checkpoints = [], [], {}
    for kind in ["bloom", "fm", "dgim"]:
        for repeat in range(1, 4):
            gc.collect()
            row, history, snapshots = run_case(kind, path=path, capture=repeat == 1,
                targets=[10_000, 100_000, 500_000])
            for snapshot in snapshots:
                scaling.append(dict(algorithm=kind, repetition=repeat, **snapshot))
            if repeat == 1:
                defaults.append(row)
                full_checkpoints[kind] = history
                write_csv(RESULTS / f"{kind}_checkpoints.csv", history)
            print("Full pass:", kind, "repeat", repeat, "events", row["events"], flush=True)
            write_csv(RESULTS / "scaling_raw.csv", scaling)
    aggregates = []
    for kind in ["bloom", "fm", "dgim"]:
        for n in sorted({r["events"] for r in scaling if r["algorithm"] == kind}):
            rows = [r for r in scaling if r["algorithm"] == kind and r["events"] == n]
            a, e = [r["approximate_seconds"] for r in rows], [r["exact_seconds"] for r in rows]
            aggregates.append(dict(algorithm=kind, events=n, repetitions=len(rows),
                median_seconds=statistics.median(a), min_seconds=min(a), max_seconds=max(a),
                median_exact_seconds=statistics.median(e), throughput=n / statistics.median(a),
                exact_throughput=n / statistics.median(e),
                state_bytes=rows[0]["state_bytes"], exact_state_bytes=rows[0]["exact_state_bytes"],
                exact=rows[0]["exact"], estimate=rows[0]["estimate"],
                relative_error=rows[0]["relative_error"]))
    write_csv(RESULTS / "scaling_summary.csv", aggregates)
    write_csv(RESULTS / "full_summary.csv", defaults)
    write_json(RESULTS / "run_metadata.json", dict(python=sys.version, platform=platform.platform(),
        machine=platform.machine(), seeds=SEEDS, batch_size=1000, timing_repetitions=3,
        dataset_sha256=checksum(path), sweep_valid_events=100_000,
        timing="update + query; excludes parsing, validation, memory measurement and plotting",
        memory="final reachable Python state, counted independently; not peak process RSS",
        scaling="prefix snapshots within three full replays per algorithm"))
    return defaults

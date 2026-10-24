"""Prepare real NASA records and deterministic hash inputs for the browser lab.

The browser still updates every sketch on every event. Precomputed keyed hash
inputs keep the UI fast and make JS answers identical to the Python experiment.
"""
import csv
import gzip
import hashlib
import json
import shutil
import struct
import zipfile
from datetime import datetime
from pathlib import Path

from stream import DATA, ROOT, events, checksum

DEST = ROOT / "web" / "dist"
SEEDS = [7, 19, 42, 73, 101]
STRIDE = 92  # seven low uint32 hash words (28 bytes), 64 trailing-zero bytes


def export_results():
    """Use the last complete saved submission if a new sweep is in progress."""
    out = DEST / "data"
    recorded = {}
    archive = ROOT / "output" / "481013386_MohammedKhalifah_5113_Assignment_2.zip"
    prefix = archive.stem + "/results/"
    for name in ["full_summary", "parameter_sweep", "scaling_summary"]:
        raw = (ROOT / "results" / (name + ".csv")).read_text()
        rows = list(csv.DictReader(raw.splitlines()))
        expected = {"full_summary": 3, "parameter_sweep": 63, "scaling_summary": 12}[name]
        if len(rows) != expected:
            with zipfile.ZipFile(archive) as previous:
                raw = previous.read(prefix + name + ".csv").decode()
                rows = list(csv.DictReader(raw.splitlines()))
        assert len(rows) == expected, f"Incomplete {name} evidence"
        recorded[name] = rows
        (out / (name + ".csv")).write_text(raw)
    recorded["run_metadata"] = json.loads((ROOT / "results" / "run_metadata.json").read_text())
    (out / "benchmarks.json").write_text(json.dumps(recorded, separators=(",", ":")))


def compressed_json(path, value):
    with gzip.GzipFile(filename=str(path), mode="wb", mtime=0) as f:
        f.write(json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode())


def main():
    out = DEST / "data"
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    assert checksum(DATA) == manifest["sha256"]
    hosts, host_ids, requests, request_ids = [], {}, [], {}
    stats = {}
    first = None
    with gzip.GzipFile(filename=str(out / "events.bin.gz"), mode="wb", mtime=0) as target:
        for count, event in enumerate(events(stats=stats), 1):
            if event.host not in host_ids:
                host_ids[event.host] = len(hosts)
                hosts.append(event.host)
            if event.request not in request_ids:
                request_ids[event.request] = len(requests)
                requests.append(event.request)
            timestamp = int(datetime.strptime(event.timestamp, "%d/%b/%Y:%H:%M:%S %z").timestamp())
            first = first or timestamp
            target.write(struct.pack("<5I", host_ids[event.host], timestamp - first,
                request_ids[event.request], event.status,
                event.bytes_sent if event.bytes_sent is not None else 0xFFFFFFFF))
    assert count == manifest["valid"] and len(hosts) == manifest["exact_hosts"]
    compressed_json(out / "catalog.json.gz", dict(hosts=hosts, requests=requests))
    for seed in SEEDS:
        keys = [(seed + i).to_bytes(8, "big") for i in range(64)]
        with gzip.GzipFile(filename=str(out / f"hashes-{seed}.bin.gz"), mode="wb", mtime=0) as target:
            for host in hosts:
                raw = host.encode()
                hashes = [int.from_bytes(hashlib.blake2b(raw, key=k, digest_size=8).digest(), "big") for k in keys]
                low = [h & 0xFFFFFFFF for h in hashes[:7]]
                zeros = bytes((h & -h).bit_length() - 1 if h else 64 for h in hashes)
                target.write(struct.pack("<7I", *low) + zeros)
        print("Prepared hash inputs for seed", seed, flush=True)
    summary = dict(manifest, epoch=first, record_bytes=20, record_fields=["host_id", "elapsed_seconds",
        "request_id", "http_status", "bytes_or_0xFFFFFFFF"], hash_stride=STRIDE, seeds=SEEDS,
        hash_format="7 little-endian low uint32 words, then 64 trailing-zero counts; BLAKE2b-64",
        browser_note="Deterministic hashes are input preparation; all sketch updates and exact checks run in a Web Worker.",
        prepared_assets={p.name: dict(bytes=p.stat().st_size, sha256=checksum(p)) for p in out.glob("*.gz")})
    (out / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    export_results()
    print(f"Prepared {count:,} real requests, {len(hosts):,} hosts, {len(requests):,} request strings")


if __name__ == "__main__":
    main()

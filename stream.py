"""Bounded-memory parsing and provenance for the NASA Common Log Format."""
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "NASA_access_log_Jul95.gz"
SOURCE_URL = "https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz"
SOURCE_PAGE = "https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html"
PATTERN = re.compile(r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"(.*)"\s+(\d{3})\s+(\d+|-)\s*$')


@dataclass(frozen=True, slots=True)
class Event:
    host: str
    timestamp: str
    request: str
    status: int
    bytes_sent: int | None

    @property
    def error(self):
        return int(400 <= self.status <= 599)


def parse_line(line):
    m = PATTERN.match(line)
    if not m:
        return None
    host, timestamp, request, status, size = m.groups()
    try:
        datetime.strptime(timestamp, "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return None
    if not 100 <= int(status) <= 599:
        return None
    return Event(host, timestamp, request, int(status), None if size == "-" else int(size))


def events(path=DATA, limit=None, stats=None):
    """A generator; limit counts valid records, preserving source-file order."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    stats = stats if stats is not None else {}
    stats.update(lines=0, valid=0, skipped=0, unknown_bytes=0, timestamp_inversions=0)
    opener = gzip.open if str(path).endswith(".gz") else open
    previous = None
    with opener(path, "rt", encoding="latin-1", newline="") as f:
        for line in f:
            stats["lines"] += 1
            event = parse_line(line.rstrip("\r\n"))
            if event is None:
                stats["skipped"] += 1
                continue
            # YYYYMMDDhhmmss can be compared lexicographically within July 1995.
            key = datetime.strptime(event.timestamp, "%d/%b/%Y:%H:%M:%S %z")
            stats["timestamp_inversions"] += int(previous is not None and key < previous)
            previous = key
            stats["valid"] += 1
            stats["unknown_bytes"] += int(event.bytes_sent is None)
            yield event
            if limit is not None and stats["valid"] >= limit:
                break


def checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def profile(path=DATA):
    stats, hosts, statuses, days = {}, set(), Counter(), Counter()
    first, last = None, None
    samples = []
    for e in events(path, stats=stats):
        hosts.add(e.host)
        statuses[str(e.status)] += 1
        days[e.timestamp[:11]] += 1
        first = first or e.timestamp
        last = e.timestamp
        if len(samples) < 5:
            samples.append(asdict(e))
    stats.update(source_url=SOURCE_URL, source_page=SOURCE_PAGE,
                 source_file=Path(path).name, sha256=checksum(path),
                 compressed_bytes=Path(path).stat().st_size,
                 exact_hosts=len(hosts), statuses=dict(statuses), daily_counts=dict(days),
                 errors=sum(n for s, n in statuses.items() if 400 <= int(s) <= 599),
                 first_timestamp=first, last_timestamp=last, sample_events=samples)
    return stats


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

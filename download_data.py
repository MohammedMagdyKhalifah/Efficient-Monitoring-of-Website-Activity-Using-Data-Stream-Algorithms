"""Optional public-source download; the submission already includes the data."""
import argparse
import gzip
import json
from pathlib import Path
import urllib.request

from stream import DATA, ROOT, SOURCE_URL, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DATA)
    args = parser.parse_args()
    if args.destination.exists():
        raise SystemExit("Destination exists; choose a different --destination to download again.")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.destination.with_suffix(".part")
    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=90) as src, temporary.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        # Read through EOF to verify the gzip CRC, not only its header.
        with gzip.open(temporary, "rb") as f:
            while f.read(1024 * 1024):
                pass
        manifest = ROOT / "data" / "manifest.json"
        if manifest.exists():
            expected = json.loads(manifest.read_text())["sha256"]
            actual = checksum(temporary)
            if actual != expected:
                raise ValueError("Checksum differs from the evaluated dataset")
        temporary.replace(args.destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(args.destination)


if __name__ == "__main__":
    main()

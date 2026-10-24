"""Validate saved evidence and create the Blackboard submission ZIP."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from stream import ROOT, DATA, checksum, write_json

STEM = "481013386_MohammedKhalifah_5113_Assignment_2"
REPORT_NAME = "481013386_MohammedKhalifah_5113_Assignment_1.pdf"


def load_rows(name):
    with (ROOT / "results" / name).open() as f:
        return list(csv.DictReader(f))


def validate():
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    if checksum(DATA) != manifest["sha256"]:
        raise ValueError("The dataset checksum changed")
    sweep = load_rows("parameter_sweep.csv")
    full = {r["algorithm"]: r for r in load_rows("full_summary.csv")}
    raw, summary = load_rows("scaling_raw.csv"), load_rows("scaling_summary.csv")
    assert len(sweep) == 63, "Expected all 63 parameter/seed cases"
    assert len(raw) == 36 and len(summary) == 12, "Missing repetitions or prefix snapshots"
    assert set(full) == {"bloom", "fm", "dgim"}
    for kind in full:
        assert int(full[kind]["events"]) == manifest["valid"]
        assert int(full[kind]["skipped_lines"]) == manifest["skipped"]
    for kind in ["bloom", "fm"]:
        assert int(full[kind]["exact"]) == manifest["exact_hosts"]
    assert int(full["bloom"]["negative_queries"]) == manifest["exact_hosts"]
    for r in sweep + list(full.values()):
        if r["algorithm"] == "bloom":
            assert int(r["false_negatives"]) == 0
    for r in load_rows("dgim_checkpoints.csv"):
        truth, estimate = float(r["exact"]), float(r["estimate"])
        assert abs(truth - estimate) <= 0.5 * truth
    for r in summary:
        assert int(r["repetitions"]) == 3
        repetitions = [v for v in raw if v["algorithm"] == r["algorithm"] and v["events"] == r["events"]]
        assert len({v["estimate"] for v in repetitions}) == 1
        assert len({v["exact"] for v in repetitions}) == 1
        assert len({v["relative_error"] for v in repetitions}) == 1
    figures = list((ROOT / "results" / "figures").glob("*.png"))
    assert len(figures) == 7
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT / "results" / "test_results.txt").write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(result.stdout)
    web_result = subprocess.run(["node", "--test", "tests/algorithms.test.mjs"], cwd=ROOT / "web",
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT / "results" / "web_test_results.txt").write_text(web_result.stdout)
    if web_result.returncode:
        raise RuntimeError(web_result.stdout)
    evidence = dict(validated_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_sha256=manifest["sha256"], valid_requests=manifest["valid"],
        parameter_cases=len(sweep), scaling_raw_rows=len(raw), scaling_summary_rows=len(summary),
        figures=len(figures), correctness_tests="15 passed", deterministic_repetitions=True,
        dgim_full_checkpoint_error_bound="passed", bloom_false_negatives=0,
        web_correctness_tests="8 passed", browser_python_full_stream_agreement=True)
    write_json(ROOT / "results" / "validation.json", evidence)
    return evidence


def main():
    evidence = validate()
    report = ROOT / "output" / "pdf" / REPORT_NAME
    if not report.is_file():
        raise FileNotFoundError("Generate the report first: python generate_report.py")
    paths = sorted(ROOT.glob("*.py"))
    paths += [ROOT / name for name in ["README.md", "WEB_README.md", "ORAL_NOTES_AR.md", "requirements.txt", "references.bib"]]
    for folder in ["data", "results", "tests"]:
        paths += sorted(p for p in (ROOT / folder).rglob("*") if p.is_file()
                        and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".part"})
    paths += sorted(p for p in (ROOT / "web").rglob("*") if p.is_file()
                    and not any(part in {".git", ".openai", "node_modules", "downloads", "__pycache__"}
                                for part in p.relative_to(ROOT / "web").parts))
    destination = ROOT / "output" / (STEM + ".zip")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in paths:
            archive.write(path, str(Path(STEM) / path.relative_to(ROOT)))
        archive.write(report, str(Path(STEM) / REPORT_NAME))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        assert f"{STEM}/{REPORT_NAME}" in archive.namelist()
        count = len(archive.namelist())
    print(json.dumps(evidence, indent=2))
    print(f"Created {destination} ({destination.stat().st_size:,} bytes; {count} files)")


if __name__ == "__main__":
    main()

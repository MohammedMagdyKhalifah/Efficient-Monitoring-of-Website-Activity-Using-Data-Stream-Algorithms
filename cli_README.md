# Efficient Monitoring of Website Activity Using Data Stream Algorithms

**Mohammed Khalifah | 481013386 | CSD 5113 | Assignment 2**

Repository: [Efficient Monitoring of Website Activity Using Data Stream Algorithms](https://github.com/MohammedMagdyKhalifah/Efficient-Monitoring-of-Website-Activity-Using-Data-Stream-Algorithms).

The final Word report is
`output/docx/481013386_MohammedKhalifah_5113_Assignment_2.docx`.
It uses the university template and replaces the code appendix with a blank
GitHub repository field.

## Open the interactive web project

The project includes a complete responsive browser application. Run
`python3 serve_web.py --open` and visit `http://127.0.0.1:5173`.
For a standalone offline HTML file, run `python3 web_bundle.py`, then open
`output/StreamLab_Offline.html` directly in a current browser.
Use **Start / Pause / Step**, change replay speed and stream length, inspect
Bloom bits / FM registers / DGIM buckets, and compare with exact results.
The Experiments view contains the recorded Python benchmarks. See
`WEB_README.md` for browser data preparation, reproducibility and measurement limits.

The modular site lives in `web/dist/`. The standalone offline file contains the
real data and is generated locally rather than committed. Neither npm installation nor
internet access is required to use the prepared web app. Node is needed only to
run the web correctness tests (`cd web` then `npm test`).

Python mini project implementing Bloom filtering, Flajolet-Martin distinct
counting, and DGIM sliding-window counting. All experimental results use the
included real NASA HTTP log. Synthetic sequences occur only in correctness tests.

## Quick demonstration (offline, no third-party dependencies)

Use Python 3.12, open a terminal in this folder, and run:

```bash
python3 main.py --mode demo
python3 -m unittest discover -s tests -v
```

The demo reads the first 10,000 valid requests. It writes
`results/demo/summary.csv` and per-algorithm checkpoints. No account, API key,
network connection, database, Spark installation, or live server is needed.
Core source requires Python 3.10+; the pinned report/plot dependencies were tested
on Python 3.12. Python 3.12 is recommended for the complete workflow.

## Reproduce all experiments and figures

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --mode experiments --profile
python generate_report.py
python package_submission.py
```

On Windows activate with `.venv\Scripts\activate`. Omit the `python3.12` command
name if your Python 3.12 installation is invoked as `python`. Installation needs
internet access only when the dependencies are not already installed. The data,
saved results, figures and final report are already included. Execution time for
the complete suite depends on the machine; it performs 63 parameter cases plus
nine full-file replays. Console progress identifies each completed case group.

Other commands:

```bash
python main.py --mode full
python main.py --mode demo --data data/NASA_access_log_Jul95.gz
python plots.py
```

`full` runs one default replay per algorithm and saves to `results/full/`.
`experiments` regenerates the authoritative result tables in `results/` and the
seven PNG figures. `--profile` recomputes `data/manifest.json` before the run.
Running the report generator alone rebuilds the PDF from the saved results.
Running the packaging helper checks the results and tests before creating ZIP.
The default input is resolved relative to the source files, not the terminal's
working directory. User-provided input must follow NASA Common Log Format.

## What each algorithm measures

| Algorithm | Stream input | Question / exact baseline |
|---|---|---|
| Bloom | Host strings | Has this host appeared before this event? / prior-host set |
| FM | Host strings | How many different hosts have appeared? / distinct-host set |
| DGIM | 1 for status 400-599, else 0 | How many errors in the last N requests? / circular byte buffer |

One event is one HTTP request, including image/asset requests. A host is an IP
address or hostname, not a verified unique person. DGIM windows count requests,
not seconds. Neither Bloom nor FM forgets old hosts in these implementations.

The FM implementation is the chapter's **maximum trailing-zero teaching
variant**, with `2**R` estimates and a median of arithmetic group means. It is
not the first-zero bitmap estimator or HyperLogLog, and it has no fitted bias
correction. Some measured errors are large; the report analyzes them explicitly.

## Dataset

- Real source: NASA Kennedy Space Center WWW server, Internet Traffic Archive.
- Source and redistribution terms: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html
- Original archive: https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
- 1,891,714 valid requests; 81,982 distinct host strings; 10,980 HTTP errors.
- Actual coverage: July 1-28, 1995, despite the archive's July 1-31 description.
- One incomplete trailing line is skipped. Unknown response sizes remain `None`.
- The compressed dataset is included unchanged. See `data/manifest.json` and
  `data/README.md` for checksum and handling details.

To independently redownload without overwriting the included file:

```bash
python download_data.py --destination data/NASA_download_check.gz
```

This optional command validates gzip integrity and compares the download SHA-256
with the evaluated source. Do not use `--profile` with unrelated replacement data
to claim it is the original NASA source: change provenance documentation too.

## Experimental protocol and interpretation

- First 100,000 valid events: Bloom 3 bit sizes x 3 hash counts x 5 seeds;
  FM 3 hash counts x 5 seeds; DGIM 3 windows (deterministic).
- Seeds: 7, 19, 42, 73, 101. Min-max bands describe these runs, not confidence intervals.
- Default settings: Bloom 1,048,576 bits / 7 hashes; FM 16 hashes / four groups of
  four; DGIM 10,000 requests; seed 42.
- Scaling: snapshots at 10,000, 100,000, 500,000 and EOF within each of three full
  replays per algorithm. Shorter-prefix durations are cumulative measurements.
- At most 1,000 parsed events are buffered. The core algorithms never store the
  whole stream. Exact validation sets intentionally retain distinct hosts.
- Timings include updates and queries, but exclude reading/parsing, validation,
  memory inspection and plotting. FM/DGIM query every 1,000 events plus EOF.
  Bloom queries each incoming host before insertion. Throughput is algorithm
  throughput, not end-to-end I/O throughput.
- Memory is recursively measured final reachable Python state, not peak process
  RSS. Keys and container overhead are included; validation and batch memory are
  separate. A theoretical packed exact DGIM ring (`N/8` bytes) is also reported.
- Bloom FPR uses truly unseen-host queries as its denominator, not all events.
  The saved final occupancy formula is not the same as cumulative online FPR.
- Relative error is `abs(estimate-exact)/exact`. For an exact zero, a zero estimate
  records zero error; a nonzero estimate has undefined relative error. DGIM also
  records mean absolute error. Empty checkpoints are retained in its mean.
- Timings/object sizes vary by Python, operating system and hardware. Seeded
  estimates on identical inputs are deterministic. Exact methods may be faster.

## Files

| File / folder | Purpose |
|---|---|
| `bloom_filter.py`, `flajolet_martin.py`, `dgim.py` | Core algorithm implementations |
| `stream.py`, `main.py`, `experiments.py` | Parser, CLI, evaluation and measurement |
| `plots.py`, `generate_report.py` | Figures and typeset PDF with complete code appendix |
| `download_data.py`, `package_submission.py` | Optional verified download and packaging |
| `tests/test_algorithms.py` | Fifteen deterministic correctness tests |
| `data/` | Real source archive and provenance |
| `results/parameter_sweep.csv` | All 63 parameter/seed measurements |
| `results/scaling_raw.csv`, `results/scaling_summary.csv` | Raw repetitions and median timings |
| `results/full_summary.csv`, `results/*_checkpoints.csv` | Full-stream answers and plotted histories |
| `results/figures/`, `results/run_metadata.json` | Seven figures and execution metadata |
| `ORAL_NOTES_AR.md`, `references.bib` | Arabic oral preparation and bibliography |

## Submission filenames

ZIP: `481013386_MohammedKhalifah_5113_Assignment_2.zip`.

Final Word report: `output/docx/481013386_MohammedKhalifah_5113_Assignment_2.docx`.

The original generated PDF with the complete code appendix remains in
`output/pdf/`. The final Word report omits code and leaves the repository field
blank as requested. The PDF generator does not regenerate the Word report.
The assignment handout uses `_Assignment_1` in its report-naming example;
the current report uses `_Assignment_2` as requested.

The repository includes the real source archive, prepared modular web data,
results, figures, tests, Python code, browser code, and both report versions.
Temporary previews, local dependencies, IDE settings, hosting configuration,
old unrelated templates and the generated standalone HTML are excluded.

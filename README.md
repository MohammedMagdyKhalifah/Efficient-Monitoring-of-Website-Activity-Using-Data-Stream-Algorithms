# StreamLab: the responsive web project

**Mohammed Khalifah · 481013386 · CSD 5113**

The web application replays all 1,891,714 valid real NASA HTTP requests and
updates Bloom, FM, DGIM and exact checks in a Web Worker. The UI contains an
overview, live algorithm-state visualizations, recorded experiments, data
provenance, request inspection, a source explorer and downloadable project files.

## Open it

The standalone `output/StreamLab_Offline.html` opens directly in a current browser.
It includes the real dataset and works without a server or internet connection.
This large generated file is excluded from Git. After cloning the repository or
extracting the ZIP, `python3 web_bundle.py` generates this standalone file
using the included source, data and PDF, with no third-party dependencies.

For the modular source version, from the project root:

```bash
python3 serve_web.py --open
```

Open `http://127.0.0.1:5173`. Python's standard library is enough; no npm install
or framework build is required. If the port is occupied, use `--port 5174`.
Stop the local server with Ctrl+C. Use a current browser with Web Workers,
DecompressionStream, Canvas and JavaScript modules.

## What to try

1. Click **Step** to process exactly one request. Inspect its host and HTTP status.
2. Start a replay, change speed, pause and resume. Choose a 10k, 100k, 500k or full
   stream. This is historical replay, not today's NASA traffic.
3. Open **Algorithm lab**. Inspect real Bloom bits and hash positions, FM registers
   and group means, and the DGIM buckets / last 128 binary events.
4. Change bit-array size, hash counts, window or seed. Settings restart the replay
   so an old state is never mislabeled with new parameters.
5. Open **Experiments** for the 63 recorded Python cases and full-stream outcomes.
   These benchmarks are explicitly separate from current browser computation.
6. Inspect the dataset source, actual date range, skipped fragment and checksum.
7. Open the guide or source explorer, export CSV, or download the project ZIP.

## Reproduce and test

```bash
python3 prepare_web.py
cd web
npm test
cd ..
python3 web_bundle.py
```

Node 22 was used for eight web tests, including processing every real request and
checking agreement with Python: 81,982 hosts, 27 Bloom false positives, FM 442,368,
DGIM 28 against 30 exact errors in the final window, and 10,980 total HTTP errors.
The actual worker is also tested for one-step execution, playback and one-request-
per-second pacing. The exact-count mismatch of FM is exposed rather than corrected with a fitted
number. The Python project and its 15 algorithm/parser tests remain included.

## Browser data format and measurement limits

The original gzip remains unchanged. `prepare_web.py` exports valid records as
little-endian uint32 tuples `(host_id, elapsed_seconds, request_id, status, bytes)`;
`0xFFFFFFFF` means unknown bytes. Host and original request strings are in a
catalog. Browser hashes use the same seeds and BLAKE2b inputs as Python: seven
low 32-bit words for power-of-two Bloom array indexing, and 64 trailing-zero
counts for FM. No prepared answers or artificial events drive the live counters.

The modular worker incrementally decompresses records and keeps bounded input
chunks; it does not need a complete event array. The offline HTML embeds its
compressed assets, so the file and browser input cache are larger than the sketch
state. Both versions retain exact validation state for comparison. Live payload
labels exclude input caches, exact checks and JavaScript object overhead; they
are not process-memory measurements. The Experiments page shows separately
measured Python state, timings and limitations.

`web_bundle.py` refreshes the source explorer, hosted download files/index and
standalone offline HTML. Project ZIP generation in the browser uses CRC32 and
standard ZIP records; it avoids keeping another large duplicate ZIP on hosting.
`serve_web.py` maps the raw-dataset/report download aliases to the project copies.

## Responsive and accessible behavior

The desktop sidebar becomes a mobile drawer; cards and charts stack at smaller
widths. Wide data tables scroll inside their panels. Buttons work with keyboard
or touch, focus is visible, dialogs support Escape, chart data is also available
as text/tables, progress is labeled, and reduced-motion preferences are respected.

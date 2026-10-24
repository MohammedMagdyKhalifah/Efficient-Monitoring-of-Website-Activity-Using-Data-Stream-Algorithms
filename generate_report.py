"""Build the assignment PDF from actual saved measurements, including all code."""
from collections import defaultdict
import csv
from datetime import date
from html import escape
import json
from pathlib import Path
import statistics
import textwrap

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, Preformatted, KeepTogether)

from stream import ROOT

NAME, ID = "Mohammed Khalifah", "481013386"
REPORT = ROOT / "output" / "pdf" / f"{ID}_MohammedKhalifah_5113_Assignment_1.pdf"
NAVY, TEAL = colors.HexColor("#182B49"), colors.HexColor("#087F8C")
GRAY = colors.HexColor("#516174")
WIDTH = A4[0] - 96
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10,
    leading=14.2, textColor=NAVY, spaceAfter=9))
styles.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=27,
    leading=32, textColor=NAVY, spaceAfter=16))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=18,
    leading=23, textColor=NAVY, spaceAfter=14))
styles.add(ParagraphStyle(name="Sub", fontName="Helvetica-Bold", fontSize=11.5,
    leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=7))
styles.add(ParagraphStyle(name="SmallCustom", fontName="Helvetica", fontSize=8.2,
    leading=11, textColor=GRAY, spaceAfter=7))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8,
    leading=10.5, textColor=NAVY))
styles.add(ParagraphStyle(name="CodeCustom", fontName="Courier", fontSize=6.6,
    leading=8.4, textColor=NAVY, spaceAfter=4))
story = []


def p(text, style="Body"):
    story.append(Paragraph(text, styles[style]))


def section(title):
    if story:
        story.append(PageBreak())
    p(title, "Section")


def table(headers, rows, widths=None):
    header_style = ParagraphStyle(name="WhiteCell", parent=styles["Cell"], textColor=colors.white)
    values = [[Paragraph(escape(str(x)), header_style) for x in headers]]
    values += [[Paragraph(escape(str(x)), styles["Cell"]) for x in row] for row in rows]
    t = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF4F6"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), .8, TEAL)]))
    story.extend([t, Spacer(1, 10)])


def figure(name, caption, width=WIDTH):
    from PIL import Image as PILImage
    path = ROOT / "results" / "figures" / (name + ".png")
    with PILImage.open(path) as im:
        height = width * im.height / im.width
    story.extend([Image(str(path), width=width, height=height), Spacer(1, 5)])
    p(caption, "SmallCustom")


def code(text):
    story.append(Preformatted(text.strip("\n"), styles["CodeCustom"]))
    story.append(Spacer(1, 7))


def read_csv(name):
    with (ROOT / "results" / name).open() as f:
        return list(csv.DictReader(f))


def percent(value):
    return f"{100 * float(value):.2f}%"


def frame(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, h - 8, w, 8, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(48, h - 31, f"{NAME}  |  Student ID: {ID}")
    canvas.drawRightString(w - 48, h - 31, "CSD 5113 - Assignment 2")
    canvas.setStrokeColor(colors.HexColor("#D8E4E8"))
    canvas.line(48, 40, w - 48, 40)
    canvas.drawString(48, 27, "Mining Data Streams | Real NASA HTTP requests")
    canvas.drawRightString(w - 48, 27, f"{doc.page}")
    canvas.restoreState()


def main():
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    metadata = json.loads((ROOT / "results" / "run_metadata.json").read_text())
    sweep, summaries, scaling = (read_csv(n) for n in
        ["parameter_sweep.csv", "full_summary.csv", "scaling_summary.csv"])
    full = {r["algorithm"]: r for r in summaries}
    final_n = int(full["fm"]["events"])
    timings = {r["algorithm"]: r for r in scaling if int(r["events"]) == final_n}
    bloom, fm, dgim = [full[k] for k in ["bloom", "fm", "dgim"]]
    story.append(Spacer(1, 65))
    p("MINI PROJECT / CHAPTER 4", "Sub")
    p("Efficient Monitoring<br/>of Website Activity<br/>Using Data Stream Algorithms", "TitleCustom")
    p("An interactive, responsive web application and reproducible experiment on real NASA HTTP access logs", "Body")
    story.append(Spacer(1, 18))
    table(["Student", "Course", "Submission"],
          [[f"{NAME}\n{ID}", "Big Data Mining\nCSD 5113", "Assignment 2\nSemester I, 2026-2027"]],
          [WIDTH*.36, WIDTH*.32, WIDTH*.32])
    p("Project overview", "Sub")
    p("StreamLab is the project's browser interface. Playback controls, a live request feed, "
      "charts and algorithm-state views make the stream processing visible. The prepared "
      "offline HTML opens directly in a browser; the modular version runs with a small "
      "standard-library Python static server.")
    p(f"This project replays {final_n:,} genuine HTTP requests as a sequential stream. "
      "Three independently implemented summaries answer different questions: whether a host "
      "has appeared before, how many different hosts have appeared, and how many recent "
      "requests produced HTTP errors. Exact baselines make the approximation costs visible.")
    p(f"The source contains {manifest['exact_hosts']:,} distinct host strings and "
      f"{manifest['errors']:,} error responses. Results are generated from the included data, "
      "rather than inserted as example numbers. More compact summaries do not automatically "
      "produce faster execution or accurate estimates at every parameter setting.")
    p("Reading guide: Sections 1-3 explain the task and implementation; Sections 4-5 present "
      "the measured evidence; Section 6 contains the complete Python source; Section 7 lists references.", "SmallCustom")

    section("1. Mini Project Description")
    p("A website operator may need a quick repeat-host check, a running estimate of distinct "
      "hosts, and a recent error count. Keeping every request makes memory grow with the stream. "
      "A summary can preserve selected information while discarding individual events. The "
      "objective here is to measure the resulting accuracy, state size and processing cost.")
    table(["Observed dataset property", "Value"], [
        ["Origin", "NASA Kennedy Space Center WWW server, Internet Traffic Archive [1]"],
        ["Valid requests / distinct hosts", f"{final_n:,} / {manifest['exact_hosts']:,}"],
        ["Actual first / last timestamps", f"{manifest['first_timestamp']} / {manifest['last_timestamp']}"],
        ["HTTP errors (400-599)", f"{manifest['errors']:,} ({100*manifest['errors']/final_n:.3f}% of requests)"],
        ["Rejected / unknown-byte records", f"{manifest['skipped']} trailing fragment / {manifest['unknown_bytes']:,} unknown response sizes"],
        ["Compressed file size", f"{manifest['compressed_bytes']:,} bytes"],
    ], [WIDTH*.39, WIDTH*.61])
    p("The archive description labels this file as July 1995, but inspection finds valid records "
      "only through 28 July at 13:32:25. The final raw line is the incomplete fragment 'alyssa.p'. "
      "It is counted as rejected; no missing events are synthesized. The gzip file was read through "
      "EOF with its integrity check, and no timestamp inversions were found among valid records.")
    p("One stream element is one HTTP request, including asset requests and repeated requests. "
      "A host is an IP address or hostname; it is not a verified person. Missing response size '-' "
      "is kept as None because size is not needed by these algorithms. Raw order and duplicate "
      "requests are preserved. Only general traffic patterns are studied, following the archive's "
      "request, and redistribution is permitted [1].")
    figure("01_dataset", "Figure 1. Counts calculated directly from valid source records. Days after 28 July are not represented as zero traffic.")

    section("2. Selected Concepts: Bloom Filtering")
    p("Purpose and mathematical model", "Sub")
    p("The filter answers whether a host may have appeared earlier in the stream. It stores "
      "m bits and uses k hash positions per host. A zero in any queried position proves absence; "
      "all queried bits being one gives only possible membership. Collisions can make an unseen "
      "host appear present. Insertions never clear bits, so previously inserted hosts have no "
      "false negatives [2, 3].")
    code("P(bit stays 0 after d distinct inserts) = (1 - 1/m)^(k*d)\n"
         "p_FP(d) ~= (1 - exp(-k*d/m))^k\n"
         "k_opt ~= (m/d) * ln(2)\n"
         "Online FPR = false positives / queries for truly unseen hosts")
    p("The probability expression assumes approximately independent uniform hash positions. "
      "Keyed 64-bit BLAKE2b hashes provide deterministic, well-distributed positions for this "
      "experiment; distinct keys are used for the k functions. The implementation packs eight "
      "bits per byte using masks, rather than allocating a Python Boolean per bit.")
    p("Update algorithm", "Sub")
    code("for each incoming host x:\n"
         "    result = true\n"
         "    for each hash function h_j:\n"
         "        p = h_j(x) mod m\n"
         "        if bit[p] == 0: result = false\n"
         "        bit[p] = 1\n"
         "    compare result with exact prior membership\n"
         "    add x to the exact validation set")
    p("The query is evaluated against prior state, before insertion. A false positive therefore "
      "means a first-ever host request was incorrectly classified as a repeat. Each first-seen "
      "host contributes one negative query. Later requests from that host are positive queries. "
      "The exact set is an evaluation instrument and is not part of the Bloom state.")
    p("Trade-off and limitations", "Sub")
    p("State payload is ceil(m/8) bytes and each fused query/insertion costs O(k) hashes. "
      "Increasing m reduces saturation for fixed d and k. Increasing k helps only up to an "
      "appropriate occupancy-dependent range and always adds hashing work. This filter cannot "
      "list hosts or delete an individual host. It represents all previous history, not a sliding window.")
    p("The saved final_theoretical_fpr column describes occupancy at the end. The measured "
      "online FPR averages queries over a filter that starts empty. They are different quantities; "
      "the endpoint formula should not be interpreted as the expected cumulative observed rate.", "SmallCustom")

    section("2. Selected Concepts: Flajolet-Martin")
    p("Purpose and estimator", "Sub")
    p("Distinct counting asks for the number of different host identifiers seen so far. Repeated "
      "requests should not increase that count. Hashing maps each host to a reproducible 64-bit "
      "string, so repeats produce the same evidence. Let rho(h(x)) be the number of trailing zero "
      "bits. Long zero runs are rare and become more likely as distinct hosts accumulate [3, 4].")
    code("P(rho(h(x)) >= r) = 2^(-r)       [uniform-hash model]\n"
         "R_j = max over observed x of rho(h_j(x))\n"
         "Single estimate E_j = 2^(R_j)\n"
         "Group mean A_g = mean(E_j for j in group g)\n"
         "Final estimate = median(A_1, ..., A_G)")
    p("This project implements the chapter's maximum-trailing-zero teaching variant. It does "
      "not implement the original first-zero bitmap estimator or HyperLogLog. In particular, "
      "the bitmap correction constant 0.77351 is not attached to a maximum-zero statistic. "
      "The versions use 1 hash; 16 hashes split into four groups of four; and 64 hashes split "
      "into eight groups of eight. For an even group count, the median is the average of the "
      "two middle group means.")
    p("Update algorithm", "Sub")
    code("initially R_j = 0 for every hash; seen_any = false\n"
         "for each host x:\n"
         "    seen_any = true\n"
         "    for j in 1..H:\n"
         "        z = trailing_zeros(hash_j(x))\n"
         "        R_j = max(R_j, z)\n"
         "on query: return 0 if empty, otherwise median of group means")
    p("The all-zero 64-bit hash has a defined trailing-zero count of 64. Each register uses "
      "one byte, so H registers have H bytes of payload plus keys and Python object overhead. "
      "An update costs O(H), and a query costs O(H) plus sorting the few group means.")
    p("Limitations to investigate", "Sub")
    p("The estimate changes in jumps. A rare hash with many trailing zeros can create a very "
      "large value of 2^R. Arithmetic group means retain sensitivity to such outliers; taking "
      "their median reduces some instability but supplies no small-error guarantee here. "
      "Five predetermined seeds expose that variation. More hashes can improve some runs "
      "without improving every seed or removing this variant's bias. No empirical correction "
      "is fitted to the NASA answers.")

    section("2. Selected Concepts: DGIM and Sliding Windows")
    p("Purpose and binary representation", "Sub")
    p("For request t, set b_t to one for HTTP status 400-599 and zero otherwise. The requested "
      "answer is the sum of these bits in the last N valid requests. A request-count window "
      "does not represent a fixed number of seconds when traffic rates change. DGIM "
      "summarizes the ones using buckets whose sizes are powers of two [3, 5].")
    code("C_t(N) = sum b_i for max(1,t-N+1) <= i <= t\n"
         "bucket = (number of ones, timestamp of newest one)\n"
         "at most two buckets of each size\n"
         "estimate = sum(bucket sizes) - half the oldest retained size")
    p("A timestamp here is the integer event index t. On every bit, including zero, time "
      "advances and buckets whose newest timestamp is at most t-N expire. A one creates a "
      "size-one bucket. If three buckets share a size, merge the two oldest and keep the "
      "newer of their endpoint timestamps; repeat if the larger size now has three buckets.")
    code("advance event index and expire old buckets\n"
         "if bit == 1:\n"
         "    insert (1, t) as newest bucket\n"
         "    while three buckets have the same size:\n"
         "        merge the oldest two, keeping the newer endpoint\n"
         "query: sum all sizes, with half-weight on the oldest bucket")
    p("When t is at most N, no prior observations have expired, so the implementation returns "
      "the sum exactly. A retained size-one oldest bucket is also exact because its single "
      "one is known to be inside the window. An empty bucket list returns zero. Otherwise "
      "half-weighting approximates the uncertain contribution of the oldest bucket.")
    p("The basic two-bucket rule gives the standard coarse relative-error bound of at most "
      "50% for a positive true count. Zero-count windows are evaluated separately and should "
      "return zero. There are O(log N) buckets. Classical modulo-N timestamps use O(log N) "
      "bits each, giving O(log-squared N) bits overall. This readable Python version uses "
      "absolute event indices and Python tuples, so its actual overhead is measured separately.")
    p("The exact baseline is a circular bytearray with a running total: O(N) bytes and "
      "constant-time updates and queries. A packed exact bit ring could use only ceil(N/8) "
      "payload bytes; that theoretical alternative is shown alongside the implemented baseline.")

    section("3. Mini Project Design and Algorithms")
    table(["Stage", "Behavior"], [
        ["Source and parser", "Read gzip line by line; validate the timestamp and HTTP fields; retain valid requests in original order."],
        ["Bounded replay", "Collect at most 1,000 parsed events per batch. Stream speed is simulated without real-time sleeps."],
        ["Approximate branches", "Host -> Bloom; host -> FM; error bit -> DGIM. Each branch has independent state."],
        ["Exact validation", "Prior-host set for Bloom; distinct-host set for FM; byte ring and sum for DGIM."],
        ["Measurement", "Time updates/queries separately; compare answers outside timing; measure final reachable state."],
        ["Outputs", "CSV rows and checkpoints -> seven figures -> report; preserve raw repetitions and provenance."],
    ], [WIDTH*.27, WIDTH*.73])
    p("Each replay is one forward traversal. Experiments reopen the file for independent "
      "runs; algorithms do not revisit previous events within a run. The profiler and exact "
      "sets deliberately use more memory to establish ground truth. Shared parsing buffers, "
      "validation state and plots are excluded from sketch-state comparisons.")
    p("The web implementation adds a responsive HTML/CSS interface, a JavaScript Web Worker, "
      "and lossless compact browser inputs. The worker incrementally decompresses 20-byte "
      "records and updates the three summaries plus exact validation. The catalog preserves "
      "host and request strings. Prepared BLAKE2b hash words and zero counts reproduce the "
      "Python hashes without millions of slow browser hash operations; summary states and "
      "answers are calculated on every event, rather than loaded as prepared results.")
    table(["Experiment", "Settings"], [
        ["Bloom parameter sweep", "m = 65,536; 262,144; 1,048,576 bits; k = 2, 4, 7 (9 combinations)"],
        ["FM parameter sweep", "H = 1, 16, 64; fixed grouping described in Section 2"],
        ["DGIM parameter sweep", "N = 1,000; 10,000; 100,000 requests"],
        ["Sweep stream and seeds", "First 100,000 valid requests; seeds 7, 19, 42, 73, 101; deterministic DGIM run once"],
        ["Default full-stream settings", "Bloom m=1,048,576 and k=7; FM H=16; DGIM N=10,000; seed 42"],
        ["Scaling and timing", "10,000; 100,000; 500,000; EOF snapshots within three full replays per algorithm"],
    ], [WIDTH*.34, WIDTH*.66])
    p("The 1,000-event batch is also the FM/DGIM query interval. Bloom requires one membership "
      "query per event. Timed blocks include their updates and queries; parsing, comparison, "
      "CSV writing and memory inspection are outside those blocks. Approximate/exact comparisons "
      "are made within a task, rather than claiming the three different tasks have identical costs.")

    section("4. Demonstration of Concepts")
    p(f"At EOF, {final_n:,} valid requests have been processed. The same source-file order "
      "is used for both approximate and exact calculations. The table reports the first full "
      "replay with seed 42; repeated-run timing is reported separately.")
    table(["Concept", "Observed result", "Exact comparison"], [
        ["Bloom prior-host membership", f"{bloom['false_positives']} false positives; online FPR {percent(bloom['relative_error'])}",
         f"{int(bloom['negative_queries']):,} genuinely unseen-host queries; {bloom['false_negatives']} false negatives"],
        ["FM distinct hosts", f"Estimate {float(fm['estimate']):,.1f}; relative error {percent(fm['relative_error'])}",
         f"{int(fm['exact']):,} distinct host strings"],
        ["DGIM recent errors", f"Estimate {float(dgim['estimate']):,.1f}; relative error {percent(dgim['relative_error'])}",
         f"{int(dgim['exact']):,} errors in the final 10,000 requests"],
    ], [WIDTH*.27, WIDTH*.37, WIDTH*.36])
    figure("05_full_estimates", "Figure 2. Checkpoints every 1,000 requests plus EOF. FM is cumulative; DGIM describes a moving request-count window.")
    p("Bloom's uncertain positive result is visible as a measured false-positive rate. FM's "
      "stepwise changes and possible overestimation are visible against exact cardinality. "
      "DGIM follows changes in recent errors with a much smaller summary than the full request "
      "history. The checkpoint CSVs retain the plotted numbers for inspection.")

    section("4. Demonstration: The Interactive Web Application")
    p("The web application turns the mini project into a working visual lab. It offers "
      "historical replay of the first 10,000, 100,000, 500,000 or all 1,891,714 valid requests. "
      "This is live computation on historical records, not a connection to current NASA traffic.")
    table(["Interface", "What it demonstrates"], [
        ["Overview", "Current counts, exact-versus-approximate curves, source timestamps, recent real requests and logical summary payload."],
        ["Replay controls", "Start, pause, resume, reset, and exactly one event per Step. Speed ranges from one to 100,000 requested events per second; compute capacity can limit it."],
        ["Bloom state", "128 actual bit positions at a time, paging and jump-to-hash; current membership decision, prior exact membership and false positives."],
        ["FM state", "The actual maximum-zero registers, powers-of-two evidence, group means, current estimate and relative error."],
        ["DGIM state", "Power-of-two buckets ordered by recency; current merges/expirations and last 128 actual binary request events."],
        ["Experiments", "The 63 recorded Python parameter cases, memory and throughput comparisons, CSV export and transparent FM error."],
        ["Dataset and source", "Provenance, actual dates, response distribution, checksum, original request inspection, complete source explorer and project ZIP download."],
    ], [WIDTH*.25, WIDTH*.75])
    p("Changing a sketch parameter or hash seed restarts the replay. This prevents an existing "
      "state from being labeled with settings that did not produce it. Changing speed affects "
      "only pacing. Work is done in a worker so the controls and layout can remain responsive. "
      "The sidebar becomes a mobile menu; cards and charts stack, while wide data tables scroll "
      "inside their panels. Keyboard focus, accessible labels and reduced-motion behavior are included.")
    code("python3 serve_web.py --open\n"
         "# Or open output/StreamLab_Offline.html directly.\n"
         "cd web\n"
         "npm test")
    p("Eight web tests include a full replay of every real event and the actual worker's "
      "initialization, step, playback and one-event-per-second pacing. The JavaScript implementation "
      "matches Python exactly: 81,982 distinct hosts, 27 Bloom false positives, FM estimate "
      "442,368, DGIM estimate 28 versus 30 exact recent errors, and 10,980 total HTTP errors. "
      "Browser checks also verified initial loading, one-step processing and a 100,000-event replay.")
    p("Live memory badges show logical payload only. The browser has additional input/hash "
      "caches, JavaScript overhead and exact state. In particular, the standalone HTML embeds "
      "compressed inputs and is larger than the sketch state. The Experiments view labels "
      "measured Python state separately. A hosting source push was blocked by DNS restrictions "
      "in the task environment; the delivered app works locally and offline.", "SmallCustom")

    section("5. Evaluation: Bloom Filter Parameters")
    figure("02_bloom", "Figure 3. Online FPR across nine settings. Error bars span the five fixed seeds; they are not confidence intervals.")
    groups = defaultdict(list)
    for r in sweep:
        if r["algorithm"] == "bloom":
            groups[(int(r["bits"]), int(r["hashes"]))].append(r)
    table(["Bit payload", "Hashes", "Mean online FPR", "Min-max FPR"], [
        [f"{m//8//1024} KiB", k, percent(statistics.mean(float(r['relative_error']) for r in rs)),
         f"{percent(min(float(r['relative_error']) for r in rs))} - {percent(max(float(r['relative_error']) for r in rs))}"]
        for (m, k), rs in sorted(groups.items())], [WIDTH*.22, WIDTH*.15, WIDTH*.28, WIDTH*.35])
    p("At fixed k, the larger array spreads the inserted hosts over more bits and reduces "
      "collisions. Hash count is not a universal accuracy knob: the best k depends on m/d. "
      "If the filter becomes crowded, setting more positions can increase saturation. When the "
      "array is very large relative to the 7,752 distinct hosts in this prefix, some observed "
      "rates are zero. That means no false positives were observed in these finite tests; it "
      "does not prove a zero underlying probability.")
    p("The prefix sweep should not be mistaken for the full-month occupancy. The default "
      "full-stream filter receives many more distinct hosts. Its memory stays fixed while "
      "the risk of false positives grows. No false negatives were observed in the evaluated "
      "runs, consistent with the insertion-only design.")

    section("5. Evaluation: FM Variability")
    figure("03_fm_parameters", "Figure 4. Per-seed final errors and maintained state on the first 100,000 requests. The nonlinear error scale preserves outliers.")
    fm_rows = []
    for k in [1, 16, 64]:
        rs = [r for r in sweep if r["algorithm"] == "fm" and int(r["hashes"]) == k]
        errs = [float(r["relative_error"]) for r in rs]
        fm_rows.append([k, percent(statistics.mean(errs)), percent(min(errs)), percent(max(errs)),
                        f"{statistics.mean(float(r['state_bytes']) for r in rs):,.0f}"])
    table(["Hashes", "Mean error", "Minimum", "Maximum", "State bytes"], fm_rows,
          [WIDTH*.13, WIDTH*.23, WIDTH*.21, WIDTH*.21, WIDTH*.22])
    p("A single unusually long zero run can dominate 2^R, which explains the large variation "
      "for a single hash. Grouping multiple estimates changes the distribution but arithmetic "
      "means remain sensitive to extreme estimates. The results show the actual errors rather "
      "than claiming that increasing H guarantees improvement. These groups and seeds were "
      "fixed before inspecting outcomes; no seed was selected to make a favorable plot.")
    p(f"The default full-stream estimate is {float(fm['estimate']):,.1f} against "
      f"{int(fm['exact']):,} exact hosts. Its error is {percent(fm['relative_error'])}. "
      "This is an important practical limitation of the uncalibrated teaching estimator. "
      "It demonstrates how a tiny hash summary operates, but this experiment does not support "
      "using it for a strict-accuracy production counter. A separately evaluated bitmap FM or "
      "a modern cardinality sketch would be a useful extension, not a result claimed here.")

    section("5. Evaluation: DGIM Window Size")
    figure("04_dgim_parameters", "Figure 5. Mean checkpoint error and final state at the 100,000-request prefix. The ideal packed exact line is payload only.")
    drows = [r for r in sweep if r["algorithm"] == "dgim"]
    table(["Window", "Mean rel. error", "Final exact / est.", "DGIM bytes", "Exact bytes"], [
        [f"{int(r['window']):,}", percent(r['mean_checkpoint_relative_error']),
         f"{r['exact']} / {float(r['estimate']):.1f}", r['state_bytes'], r['exact_state_bytes']]
        for r in drows], [WIDTH*.17, WIDTH*.23, WIDTH*.24, WIDTH*.18, WIDTH*.18])
    p("A larger window includes more old events and can require buckets at more scales. "
      "Its exact byte buffer grows linearly with N, while the bucket count grows slowly. "
      "Error does not have to grow monotonically with the window: it depends on how recent "
      "ones fall around the oldest bucket boundary. The N=100,000 run at this prefix is a "
      "startup case with no expired data, so its zero error is expected and is not evidence "
      "of exact behavior after the window starts sliding.")
    p("Mean relative error is the unweighted mean across the 1,000-request checkpoints, "
      "including zero-error empty windows. Absolute errors are also stored. For a zero true "
      "count, a zero estimate is recorded as zero error; a nonzero estimate would have an "
      "undefined relative error and would not silently be divided by zero. Small true counts "
      "can turn a small absolute error into a large percentage.")
    p("At small N, Python tuple/list overhead can outweigh the theoretical saving compared "
      "with an efficiently packed exact ring. This is why the figure includes the ideal "
      "N/8 exact payload. Claims of space efficiency must state which representation is used.")

    section("5. Evaluation: Memory and Processing Cost")
    figure("06_full_tradeoffs", "Figure 6. Default parameters at EOF. Timing excludes parsing and validation; throughput uses the median of three full replays.")
    table(["Task", "Approx. state", "Exact state", "Approx. events/s", "Exact events/s"], [
        [kind.upper(), f"{int(full[kind]['state_bytes']):,}", f"{int(full[kind]['exact_state_bytes']):,}",
         f"{float(timings[kind]['throughput']):,.0f}", f"{float(timings[kind]['exact_throughput']):,.0f}"]
        for kind in ["bloom", "fm", "dgim"]],
        [WIDTH*.16, WIDTH*.21, WIDTH*.21, WIDTH*.21, WIDTH*.21])
    p("Memory is the recursively measured reachable state using sys.getsizeof, with each "
      "object counted once per algorithm. It includes arrays, keys, containers and Python "
      "overhead. It is final maintained state, not peak process RSS or a claim about total "
      "application memory. Temporary allocations, interpreter code and the shared input "
      "batch are excluded consistently. Exact states are measured independently.")
    p("Python's exact set uses an optimized built-in hash table. Bloom and FM perform several "
      "BLAKE2b calculations per event and execute their loops in Python, so their smaller "
      "state need not lead to higher throughput. DGIM processes zeros cheaply, and only "
      "about 0.58% of requests are errors; that sparsity helps this implementation. Results "
      "are workload- and machine-dependent, rather than a general ranking of the concepts.")
    p(f"Measured environment: Python {escape(metadata['python'].split()[0])}; "
      f"{escape(metadata['platform'])}; architecture {escape(metadata['machine'])}. "
      "Raw timings, minimum/maximum cumulative durations and all repetitions are included "
      "in scaling_raw.csv and scaling_summary.csv.", "SmallCustom")

    section("5. Evaluation: Scalability and Reproducibility")
    figure("07_scaling", "Figure 7. Prefix snapshots within three full replays. Window size stays fixed; distinct-host exact state grows as new hosts appear.")
    p("Bloom state is fixed by m and k, and FM state by H. They summarize all history. DGIM "
      "depends on its fixed recent window and the current bucket pattern. The exact distinct "
      "set grows with distinct hosts, not directly with request count; many repeated requests "
      "can arrive without adding any keys. The exact circular buffer remains fixed once N is chosen.")
    p("Validation", "Sub")
    p("Fifteen unittest cases cover Bloom membership and saturation; query-before-insert; "
      "FM empty streams, duplicate/order invariance and an independent trailing-zero "
      "calculation; parser failures and valid-row limits; and DGIM invariants, expiry, "
      "alternation, sparse input and randomized streams. DGIM is also checked exhaustively "
      "on every 9-bit sequence for six window lengths, against an independently summed history. "
      "The tests verify the 50% positive-count error bound on these fixtures. Artificial "
      "fixtures are used only for tests, not for the experimental results.")
    p("Reproduction and limitations", "Sub")
    code("python main.py --mode demo\n"
         "python -m unittest discover -s tests -v\n"
         "python main.py --mode experiments --profile\n"
         "python generate_report.py")
    p("The ZIP includes the compressed real dataset, exact parameter choices, five seeds, "
      "raw results and plotting/report scripts. Deterministic estimates reproduce on the "
      "same input, whereas timings and Python object sizes can vary across systems. Only "
      "one historical server workload is evaluated. Error sparsity, repeated hosts, the "
      "capture's partial-month coverage and Python implementation overhead limit generalization.")
    p("The evidence supports compact summary states, while exposing their task-specific "
      "costs: Bloom can misclassify new hosts, this FM variant can be substantially inaccurate, "
      "and DGIM trades exact recent counts for bucket-based estimates. None of the "
      "three summaries replaces the full log when individual request retrieval is required.")

    section("6. Code Appendix")
    p("Complete project source follows, including the three core algorithms, replay "
      "and evaluation code, web interface, worker, browser algorithms, data preparation, "
      "offline bundler, figures, report generator, download/packaging helpers and tests. "
      "The matching standalone files in the ZIP can be executed directly. Wrapped continuation "
      "lines in this appendix retain the original source line number; the source files remain authoritative.")
    source_paths = sorted(ROOT.glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    source_paths += sorted(p for p in (ROOT / "web" / "dist").glob("*")
                           if p.suffix in {".js", ".html", ".css", ".svg"})
    source_paths += sorted((ROOT / "web" / "tests").glob("*.mjs"))
    for index, path in enumerate(source_paths):
        story.append(PageBreak())
        p(str(path.relative_to(ROOT)), "Sub")
        numbered = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # Courier at 6.6pt permits 120 characters in the printable width.
            wrapped = textwrap.wrap(line.expandtabs(4), width=112, replace_whitespace=False,
                drop_whitespace=False) or [""]
            numbered.append(f"{n:4}  " + wrapped[0])
            numbered.extend("      " + continuation for continuation in wrapped[1:])
        story.append(Preformatted("\n".join(numbered), styles["CodeCustom"]))

    section("7. References")
    refs = [
        "[1] Internet Traffic Archive. NASA-HTTP: Two Months of HTTP Logs from the KSC-NASA WWW Server. "
        "Collected by Jim Dumoulin; contributed by Martin Arlitt and Carey Williamson. "
        "https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html (accessed 23 October 2026).",
        "[2] Bloom, B. H. (1970). Space/time trade-offs in hash coding with allowable errors. "
        "Communications of the ACM, 13(7), 422-426. https://doi.org/10.1145/362686.362692.",
        "[3] Leskovec, J., Rajaraman, A., and Ullman, J. D. Mining of Massive Datasets, "
        "Chapter 4: Mining Data Streams. Author-hosted materials: https://www.mmds.org/; "
        "chapter: https://infolab.stanford.edu/~ullman/mmds/ch4.pdf.",
        "[4] Flajolet, P., and Martin, G. N. (1985). Probabilistic counting algorithms for data base "
        "applications. Journal of Computer and System Sciences, 31(2), 182-209. "
        "https://doi.org/10.1016/0022-0000(85)90041-8.",
        "[5] Datar, M., Gionis, A., Indyk, P., and Motwani, R. (2002). Maintaining stream statistics "
        "over sliding windows. SIAM Journal on Computing, 31(6), 1794-1813. "
        "https://doi.org/10.1137/S0097539701398363.",
    ]
    for ref in refs:
        p(escape(ref))
    p("Data provenance and integrity", "Sub")
    p("Original download: " + escape(manifest["source_url"]), "SmallCustom")
    p("SHA-256 (compressed source file):", "SmallCustom")
    code(manifest["sha256"][:32] + "\n" + manifest["sha256"][32:])
    p("The included references.bib provides a reusable bibliography. Results and narrative "
      "are specific to this project's measured runs; external sources provide the dataset "
      "provenance and algorithm foundations.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(REPORT), pagesize=A4, rightMargin=48, leftMargin=48,
        topMargin=53, bottomMargin=53, title="Efficient Monitoring of Website Activity Using Data Stream Algorithms",
        author=NAME, subject="CSD 5113 Assignment 2 - Mining Data Streams")
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    print(REPORT)


if __name__ == "__main__":
    main()

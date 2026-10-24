"""Create static research figures directly from the saved experiment CSVs."""
from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import statistics

from stream import ROOT


def read_csv(name):
    with (ROOT / "results" / name).open(newline="") as f:
        return list(csv.DictReader(f))


def make_plots():
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titleweight": "bold", "figure.dpi": 120, "savefig.dpi": 180})
    out = ROOT / "results" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    teal, orange, blue = "#087F8C", "#D68035", "#4059AD"

    def save(fig, name):
        fig.tight_layout(pad=1.5)
        fig.savefig(out / (name + ".png"), bbox_inches="tight", facecolor="white")
        plt.close(fig)

    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    days = sorted(manifest["daily_counts"], key=lambda s: int(s[:2]))
    fig, ax = plt.subplots(figsize=(9, 3.3))
    ax.bar([int(d[:2]) for d in days], [manifest["daily_counts"][d] for d in days], color=teal)
    ax.set(xlabel="Day of July 1995", ylabel="Valid HTTP requests",
           title="Observed source-file coverage: 1-28 July 1995")
    ax.ticklabel_format(style="plain", axis="y")
    save(fig, "01_dataset")

    rows = read_csv("parameter_sweep.csv")
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    for k, color in zip([2, 4, 7], [orange, teal, blue]):
        xs, means, lo, hi = [], [], [], []
        for bits in [65_536, 262_144, 1_048_576]:
            group = [100 * float(r["relative_error"]) for r in rows
                     if r["algorithm"] == "bloom" and int(r["bits"]) == bits and int(r["hashes"]) == k]
            mean = statistics.mean(group)
            xs.append(bits / 8 / 1024); means.append(mean)
            lo.append(mean - min(group)); hi.append(max(group) - mean)
        ax.errorbar(xs, means, yerr=[lo, hi], marker="o", capsize=4, color=color,
                    label=f"{k} hashes")
    ax.set(xlabel="Packed Bloom bit-array size (KiB)", ylabel="Online false-positive rate (%)",
           title="Bloom filter: first 100,000 valid requests")
    ax.set_xscale("log", base=2)
    ax.set_xticks([8, 32, 128], ["8", "32", "128"])
    ax.legend(title="Mean and min-max of 5 seeds")
    ax.grid(axis="y", alpha=.2)
    save(fig, "02_bloom")

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7))
    for x, k in enumerate([1, 16, 64]):
        group = [r for r in rows if r["algorithm"] == "fm" and int(r["hashes"]) == k]
        errors = [100 * float(r["relative_error"]) for r in group]
        axes[0].scatter([x + v for v in np.linspace(-.09, .09, len(group))], errors,
                        color=teal, s=30, label="Individual seed" if x == 0 else None)
        axes[0].hlines(statistics.mean(errors), x-.2, x+.2, color=orange, linewidth=2,
                       label="Mean of five seeds" if x == 0 else None)
        axes[1].bar(x, statistics.mean(float(r["state_bytes"]) for r in group), color=blue)
    axes[0].set(xticks=[0, 1, 2], xticklabels=[1, 16, 64], xlabel="Hash functions",
                ylabel="Final relative error (%)", title="FM variation across five seeds")
    axes[0].set_yscale("symlog", linthresh=10)
    axes[0].set_ylim(bottom=0)
    axes[0].legend(loc="lower right", fontsize=7)
    axes[1].set(xticks=[0, 1, 2], xticklabels=[1, 16, 64], xlabel="Hash functions",
                ylabel="Reachable Python state (bytes)", title="More hashes require more state")
    save(fig, "03_fm_parameters")

    dgim_rows = [r for r in rows if r["algorithm"] == "dgim"]
    x = [int(r["window"]) for r in dgim_rows]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    axes[0].plot(x, [100*float(r["mean_checkpoint_relative_error"]) for r in dgim_rows], "o-", color=teal)
    axes[0].set(ylabel="Mean checkpoint relative error (%)", title="DGIM error by window size")
    for field, label, color, style in [("state_bytes", "DGIM Python state", teal, "o-"),
            ("exact_state_bytes", "Exact byte-buffer state", orange, "s-"),
            ("exact_packed_window_bytes", "Ideal exact bit payload", blue, "^--")]:
        axes[1].plot(x, [float(r[field]) for r in dgim_rows], style, color=color, label=label)
    axes[1].set(yscale="log", ylabel="Bytes (log scale)", title="Implementation overhead matters")
    axes[1].legend(fontsize=7)
    for ax in axes:
        ax.set_xscale("log"); ax.set_xlabel("Window length in requests")
        ax.grid(axis="y", alpha=.2)
    save(fig, "04_dgim_parameters")

    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for kind, ax, title in [("fm", axes[0], "Distinct hosts: FM versus exact set"),
                            ("dgim", axes[1], "HTTP errors in the last 10,000 requests")]:
        history = read_csv(f"{kind}_checkpoints.csv")
        ns = [int(r["events"]) / 1_000_000 for r in history]
        ax.plot(ns, [float(r["exact"]) for r in history], color=teal, label="Exact", linewidth=1.4)
        ax.plot(ns, [float(r["estimate"]) for r in history], color=orange, label=kind.upper(),
                linewidth=1.1, alpha=.9)
        ax.set(title=title, ylabel="Count")
        ax.legend(loc="upper left", ncol=2)
        ax.grid(alpha=.2)
    axes[1].set_xlabel("Valid requests processed (millions)")
    save(fig, "05_full_estimates")

    scaling = read_csv("scaling_summary.csv")
    maximum = max(int(r["events"]) for r in scaling)
    full = [next(r for r in scaling if r["algorithm"] == kind and int(r["events"]) == maximum)
            for kind in ["bloom", "fm", "dgim"]]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    pos = np.arange(3)
    for ax, approx_field, exact_field, ylabel, title in [
            (axes[0], "state_bytes", "exact_state_bytes", "Bytes (log scale)", "Final maintained state"),
            (axes[1], "throughput", "exact_throughput", "Events/second (log scale)", "Median of three full replays")]:
        ax.bar(pos-.18, [float(r[approx_field]) for r in full], .36, color=teal, label="Approximate")
        ax.bar(pos+.18, [float(r[exact_field]) for r in full], .36, color=orange, label="Exact")
        ax.set(xticks=pos, xticklabels=["Bloom", "FM", "DGIM"], yscale="log", ylabel=ylabel, title=title)
        ax.legend(fontsize=8)
    save(fig, "06_full_tradeoffs")

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.5))
    for kind, ax in zip(["bloom", "fm", "dgim"], axes):
        group = [r for r in scaling if r["algorithm"] == kind]
        ns = [int(r["events"]) for r in group]
        ax.plot(ns, [float(r["state_bytes"]) for r in group], "o-", color=teal, label="Approximate")
        ax.plot(ns, [float(r["exact_state_bytes"]) for r in group], "s-", color=orange, label="Exact")
        ax.set(xscale="log", yscale="log", title=kind.upper(), xlabel="Requests processed", ylabel="State bytes")
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=7)
    save(fig, "07_scaling")
    print("Saved seven figures to", out)


if __name__ == "__main__":
    make_plots()

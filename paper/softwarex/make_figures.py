#!/usr/bin/env python3
"""Paper figures for the FastForest SoftwareX manuscript, from results/summary/ (per_run.csv, stability.csv, recovery.csv).

Usage: python3 make_figures.py <results/summary dir> <output dir>
Produces fig2_reduction_vs_accuracy, fig3_stability, fig4_madelon_recovery and figS1_half_tables (PDF + PNG).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# fixed categorical assignment (colour + marker), never cycled
METHODS = [
    ("fastforest_mdi", "FastForest (MDI)", "#2a78d6", "o"),
    ("fastforest_perm", "FastForest (permutation)", "#eb6834", "s"),
    ("boruta", "Boruta", "#1baf7a", "^"),
    ("rfecv", "RFECV", "#eda100", "v"),
    ("perm_threshold", "Permutation > 0", "#e87ba4", "D"),
    ("l1_logistic", "L1 logistic", "#008300", "P"),
    ("full", "No selection", "#6250d6", "X"),
    ("random", "Random subset", "#e34948", "*"),
]
LABEL = {k: lab for k, lab, _, _ in METHODS}
COLOR = {k: c for k, _, c, _ in METHODS}
MARKER = {k: m for k, _, _, m in METHODS}

MAIN = [
    ("body_site", "Body site (reaction abundance)"),
    ("rp_combined_phylum", "APOLLO combined, phylum"),
    ("rp_combined_order", "APOLLO combined, order"),
    ("rp_combined_genus", "APOLLO combined, genus"),
    ("madelon", "Madelon"),
    ("gisette", "Gisette"),
    ("gemler_breast", "GEMLeR breast vs rest"),
]
HALVES = [
    ("rp_150k_phylum", "Sequenced genomes, phylum"),
    ("rp_150k_order", "Sequenced genomes, order"),
    ("rp_150k_genus", "Sequenced genomes, genus"),
    ("rp_90k_phylum", "Gut MAGs, phylum"),
    ("rp_90k_order", "Gut MAGs, order"),
    ("rp_90k_genus", "Gut MAGs, genus"),
]

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e6e3", "grid.linewidth": 0.5, "axes.edgecolor": "#9a9a97",
    "pdf.fonttype": 42, "savefig.dpi": 300,
})

per = pd.read_csv(SRC / "per_run.csv")
per = per[per.status == "ok"]
agg = per.groupby(["dataset", "method"]).agg(
    n=("seed", "nunique"), feat=("n_features", "mean"), feat_sd=("n_features", "std"),
    acc=("test_accuracy", "mean"), acc_sd=("test_accuracy", "std")).reset_index()


def panel(ax, dataset, title, show_err=True):
    d = agg[agg.dataset == dataset].set_index("method")
    for key, lab, col, mk in METHODS:
        if key not in d.index:
            continue
        r = d.loc[key]
        xerr = r.feat_sd if show_err and np.isfinite(r.feat_sd) else None
        yerr = 100 * r.acc_sd if show_err and np.isfinite(r.acc_sd) else None
        ax.errorbar(r.feat, 100 * r.acc, xerr=xerr, yerr=yerr, fmt=mk, color=col, ms=6 if mk != "*" else 9,
                    mec="white", mew=0.6, elinewidth=0.8, capsize=2, label=lab, zorder=3)
    n = int(d.n.max())
    ax.set_xscale("log")
    from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter
    lo, hi = d.feat.min(), d.feat.max()
    ax.xaxis.set_minor_formatter(NullFormatter())
    if hi / lo < 30:  # narrow range: a few readable ticks instead of 2x10^3-style minor labels
        ticks = [t for t in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000) if lo / 1.5 <= t <= hi * 1.5]
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        fmt = ScalarFormatter(); fmt.set_scientific(False)
        ax.xaxis.set_major_formatter(fmt)
    ax.set_title(f"{title} ({n} seed{'s' if n > 1 else ''})")
    ax.set_xlabel("features kept (log scale)")
    ax.set_ylabel("test accuracy (%)")


def legend_handles():
    return [plt.Line2D([], [], color=col, marker=mk, linestyle="", ms=6 if mk != "*" else 9, mec="white", mew=0.6, label=lab)
            for _, lab, col, mk in METHODS]


# ---------------------------------------------------------------- Fig. 2: seven multi-seed tables
fig, axes = plt.subplots(2, 4, figsize=(11, 5.6))
for ax, (ds, ttl) in zip(axes.flat, MAIN):
    panel(ax, ds, ttl)
axes.flat[-1].axis("off")
axes.flat[-1].legend(handles=legend_handles(), loc="center", frameon=False, ncol=1, title="Method")
fig.tight_layout(w_pad=1.2, h_pad=1.6)
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig2_reduction_vs_accuracy.{ext}")
plt.close(fig)

# ---------------------------------------------------------------- Fig. S1: the six single-seed halves
fig, axes = plt.subplots(2, 3, figsize=(9, 5.4))
for ax, (ds, ttl) in zip(axes.flat, HALVES):
    panel(ax, ds, ttl, show_err=False)
axes.flat[0].legend(handles=legend_handles(), loc="lower left", frameon=True, framealpha=0.9, ncol=2, fontsize=6.5)
fig.tight_layout(w_pad=1.2, h_pad=1.6)
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"figS1_half_tables.{ext}")
plt.close(fig)

# ---------------------------------------------------------------- Fig. 3: stability (mean pairwise Jaccard)
st = pd.read_csv(SRC / "stability.csv").set_index(["dataset", "method"])
sel = [k for k, *_ in METHODS if k not in ("full", "random")]
fig, ax = plt.subplots(figsize=(9, 3.2))
w = 0.8 / len(sel)
x = np.arange(len(MAIN))
for j, key in enumerate(sel):
    means = [st.loc[(ds, key), "jaccard_mean"] if (ds, key) in st.index else np.nan for ds, _ in MAIN]
    sds = [st.loc[(ds, key), "jaccard_sd"] if (ds, key) in st.index else np.nan for ds, _ in MAIN]
    ax.bar(x + (j - (len(sel) - 1) / 2) * w, means, w * 0.92, color=COLOR[key], label=LABEL[key], yerr=sds,
           error_kw=dict(elinewidth=0.7, capsize=1.5, ecolor="#333"), zorder=3)
ax.set_xticks(x)
ax.set_xticklabels([t for _, t in MAIN], rotation=15, ha="right")
ax.set_ylabel("mean pairwise Jaccard\nof selected sets across seeds")
ax.set_ylim(0, 1)
ax.legend(ncol=6, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.grid(axis="x", visible=False)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig3_stability.{ext}")
plt.close(fig)

# ---------------------------------------------------------------- Fig. 4: Madelon relevant-feature recovery
rec = pd.read_csv(SRC / "recovery.csv")
rec = rec[rec.dataset == "madelon"]
g = rec.groupby("method").agg(prec=("precision", "mean"), prec_sd=("precision", "std"), rec=("recall", "mean"), rec_sd=("recall", "std"),
                              nsel=("n_selected", "mean"))
order = [k for k, *_ in METHODS if k in g.index]
fig, ax = plt.subplots(figsize=(7.2, 2.8))
x = np.arange(len(order))
ax.bar(x - 0.2, [g.loc[k, "prec"] for k in order], 0.38, yerr=[g.loc[k, "prec_sd"] for k in order], color="#2a78d6",
       error_kw=dict(elinewidth=0.7, capsize=1.5, ecolor="#333"), label="precision (selected features that are relevant)", zorder=3)
ax.bar(x + 0.2, [g.loc[k, "rec"] for k in order], 0.38, yerr=[g.loc[k, "rec_sd"] for k in order], color="#eb6834",
       error_kw=dict(elinewidth=0.7, capsize=1.5, ecolor="#333"), label="recall (of the 20 relevant features)", zorder=3)
for i, k in enumerate(order):
    ax.text(i, 1.04, f"{g.loc[k, 'nsel']:.0f} kept", ha="center", va="bottom", fontsize=6.5, color="#52514e")
ax.set_xticks(x)
ax.set_xticklabels([LABEL[k] for k in order], rotation=15, ha="right")
ax.set_ylim(0, 1.15)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.legend(frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0))
ax.grid(axis="x", visible=False)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig4_madelon_recovery.{ext}")
plt.close(fig)
print("figures written to", OUT)

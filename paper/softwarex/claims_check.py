#!/usr/bin/env python3
"""Recompute the claims ledger of the FastForest SoftwareX paper (``claims.md``).

Run from anywhere; paths resolve from the repository root::

    python paper/softwarex/claims_check.py              # run every check and print the report
    python paper/softwarex/claims_check.py --write      # also write computed values and statuses
    python paper/softwarex/claims_check.py --skip-slow  # skip test suite, CLI and listing runs
    python paper/softwarex/claims_check.py --offline    # skip the request to the hosted app

Every ledger row's "how to check" cell is the snippet that is run: a Python expression evaluated
in this module's namespace (the frames and helpers below), or a shell command prefixed with
``$`` and run from the repository root. Its printed value is compared with the "claimed value"
after normalisation (thousands separators, dashes, ``±``, ``%``, spacing and case are ignored,
and so is a trailing parenthetical in the computed value, which carries the evidence). Equal is
``reproduced``, anything else ``differs``. Rows marked ``by construction`` or ``not checkable``
keep their status; their snippet, if any, still fills the computed column.

The script also checks that each statement is still on its line of ``main.tex`` (reporting where
it moved to) and that the ``## Discrepancies`` section lists every ``differs`` row. It needs the
local, git-ignored ``results/`` directory; the Madelon checks also need
``benchmarks/data/prepared/madelon.parquet``. Exit status 1 if a snippet fails or a statement
is not found in ``main.tex``; ``differs`` rows are findings, not failures.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LEDGER = HERE / "claims.md"
TEX_PATH = HERE / "main.tex"
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Several of these names are used only by the ledger's snippets (evaluated in this namespace).
from fastforest import FastForest, __version__, load_sample, viz  # noqa: E402, F401
from fastforest.datasets import TABLE_SUFFIXES  # noqa: E402, F401
from fastforest.importance import IMPORTANCE_METHODS  # noqa: E402, F401
from fastforest.metrics import criterion_metrics  # noqa: E402, F401
from fastforest.preprocess import Preprocessor  # noqa: E402
from fastforest.reduce import quantile_levels, quantile_threshold_search  # noqa: E402
from fastforest.redundancy import find_redundant  # noqa: E402, F401

# ------------------------------------------------------------------------- data in scope
SUMMARY = ROOT / "results" / "summary"
S = pd.read_csv(SUMMARY / "summary.csv").set_index(["dataset", "method"])
P = pd.read_csv(SUMMARY / "per_run.csv")
ST = pd.read_csv(SUMMARY / "stability.csv").set_index(["dataset", "method"])
R = pd.read_csv(SUMMARY / "recovery.csv")
D = pd.read_csv(SUMMARY / "datasets.csv").set_index("dataset")
SC = pd.read_csv(SUMMARY / "scalability.csv").set_index("dataset")
ENV = json.loads((ROOT / "results" / "env.json").read_text())
CFG = yaml.safe_load((ROOT / "benchmarks" / "config.yaml").read_text())
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
TEX = TEX_PATH.read_text(encoding="utf-8").splitlines()

FF = "fastforest_mdi"
BASELINES = ["boruta", "rfecv", "l1_logistic"]
COMBINED = ["rp_combined_phylum", "rp_combined_order", "rp_combined_genus"]
HALVES = [d for d in D.index if d.startswith(("rp_150k", "rp_90k"))]
RP = COMBINED + HALVES  # the nine reaction-presence tables
RECON = ["body_site", *RP]  # the ten reconstruction tables
PUBLIC = ["madelon", "gisette", "gemler_breast"]
MAIN = ["body_site", *COMBINED, *PUBLIC]  # Table 3 and Fig. 2
ALL13 = RECON + PUBLIC
T3 = [FF, "boruta", "rfecv", "l1_logistic", "full", "random"]  # Table 3 column order

SKIP_SLOW = False
OFFLINE = False


class Skip(Exception):
    """Raised by a helper whose check was switched off on the command line."""


def slow(fn):
    """Cache a slow helper and skip it under ``--skip-slow``."""
    cached = functools.cache(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if SKIP_SLOW:
            raise Skip(fn.__name__)
        return cached(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------------------- formatting
def fx(x, d=0):
    """Format a number with ``d`` decimals and thousands separators."""
    return f"{float(x):,.{d}f}"


def rng(values, d=0):
    """``min–max`` of ``values`` with ``d`` decimals."""
    vals = [float(v) for v in values]
    return f"{fx(min(vals), d)}–{fx(max(vals), d)}"


def ev(cond, evidence):
    """A verdict with its evidence: ``True (…)`` or ``False (…)``."""
    return f"{bool(cond)} ({evidence})"


def row(*cells):
    """Join table cells as in the LaTeX source."""
    return " & ".join(str(c) for c in cells)


def mean_(ds, m=FF, col="test_accuracy"):
    return float(S.loc[(ds, m), f"{col}_mean"])


def sd_(ds, m=FF, col="test_accuracy"):
    return float(S.loc[(ds, m), f"{col}_sd"])


def pct(ds, m=FF, d=2):
    """Mean test accuracy in percent."""
    return fx(100 * mean_(ds, m), d)


def acc(ds, m=FF, d=2):
    """Mean ± SD test accuracy in percent (mean only for a single run)."""
    sd = sd_(ds, m)
    return pct(ds, m, d) + ("" if np.isnan(sd) else f" ± {100 * sd:.{d}f}")


def nf(ds, m=FF):
    """Mean number of features kept, as an integer."""
    return fx(mean_(ds, m, "n_features"))


def sec(ds, m=FF):
    """Mean selection time as printed in Table 3 (one decimal below 2 s)."""
    x = mean_(ds, m, "select_seconds")
    return f"{x:.1f}" if x < 2 else fx(x)


def jac(ds, m=FF):
    return f"{ST.loc[(ds, m), 'jaccard_mean']:.2f}"


def kept_pct(ds, m=FF):
    return 100 * mean_(ds, m, "n_features") / D.loc[ds, "features"]


# ------------------------------------------------------------------------- comparisons
def ratios(dss, ms=BASELINES):
    """Features kept by each method in ``ms`` divided by FastForest's, per table."""
    return [
        mean_(d, m, "n_features") / mean_(d, FF, "n_features")
        for d in dss
        for m in ms
        if (d, m) in S.index
    ]


def not_worse(dss, ms=BASELINES):
    """Pairs where FastForest's printed test accuracy is at least the method's."""
    fails, n = [], 0
    for d in dss:
        for m in ms:
            n += 1
            if round(100 * mean_(d), 2) < round(100 * mean_(d, m), 2):
                fails.append(f"{d}: {pct(d)} < {m} {pct(d, m)}")
    return f"{n - len(fails)}/{n}" + (f" ({'; '.join(fails)})" if fails else "")


def less_stable(dss, ref="boruta"):
    """Tables where FastForest's mean Jaccard is below ``ref``'s."""
    rev = [f"{d}: {jac(d)} vs {jac(d, ref)}" for d in dss if not jac(d) < jac(d, ref)]
    return f"{len(dss) - len(rev)}/{len(dss)}" + (f" (not on {'; '.join(rev)})" if rev else "")


def fewer(dss, m):
    """Tables where method ``m`` keeps fewer features than FastForest."""
    rev = [
        f"{d}: {nf(d, m)} vs {nf(d)}"
        for d in dss
        if not mean_(d, m, "n_features") < mean_(d, FF, "n_features")
    ]
    return f"{len(dss) - len(rev)}/{len(dss)}" + (f" (not on {'; '.join(rev)})" if rev else "")


def best_baseline(d):
    return max(BASELINES, key=lambda m: mean_(d, m))


def best_gap(d):
    """Points by which the most accurate baseline beats FastForest (printed values)."""
    m = best_baseline(d)
    return round(100 * mean_(d, m), 2) - round(100 * mean_(d), 2)


def best_ratio(d):
    return mean_(d, best_baseline(d), "n_features") / mean_(d, FF, "n_features")


def n_better(d):
    """Baselines with a higher printed test accuracy than FastForest."""
    return sum(round(100 * mean_(d, m), 2) > round(100 * mean_(d), 2) for m in BASELINES)


def left_edge(dss):
    """Panels where FastForest (MDI) keeps the fewest features of the plotted methods."""
    ok, other = 0, []
    for d in dss:
        sub = S.xs(d, level="dataset")
        sub = sub[sub.index != "random"]  # same size as FastForest by construction
        lo = sub.n_features_mean.min()
        if sub.loc[FF, "n_features_mean"] <= lo:
            ok += 1
        else:
            m = sub.n_features_mean.idxmin()
            other.append(f"{d}: {m} {fx(lo, 1)}")
    return f"{ok}/{len(dss)}" + (f" (fewer: {'; '.join(other)})" if other else "")


def gaps_to_full(dss):
    """FastForest minus no-selection test accuracy, in printed points."""
    return [round(100 * mean_(d), 2) - round(100 * mean_(d, "full"), 2) for d in dss]


# ------------------------------------------------------------------------- per run
def runs(ds, m=FF):
    return P[(P.dataset == ds) & (P.method == m)].sort_values("seed")


def flag(series):
    return series.astype(str).str.lower().eq("true")


def held(ds, m=FF):
    r = runs(ds, m)
    return f"{int(flag(r.bound_satisfied).sum())}/{len(r)}"


def held_all():
    """FastForest runs whose validation bound held."""
    ff = P[P.method.str.startswith("fastforest")]
    ok = flag(ff.bound_satisfied)
    parts = [
        f"{m} {int(ok[ff.method == m].sum())}/{int((ff.method == m).sum())}"
        for m in sorted(ff.method.unique())
    ]
    return f"{int(ok.sum())}/{len(ff)} (FastForest runs of {len(P)}; {', '.join(parts)})"


def same_size():
    a = P[P.method == FF].set_index(["dataset", "seed"]).n_features
    b = P[P.method == "random"].set_index(["dataset", "seed"]).n_features.reindex(a.index)
    return f"{int((a == b).sum())}/{len(a)}"


def rec(m=FF):
    return R[(R.dataset == "madelon") & (R.method == m)]


def run_json(dss, m=FF):
    out = []
    for d in dss:
        for path in sorted((ROOT / "results" / "runs" / d / m).glob("seed*.json")):
            out.append(json.loads(path.read_text()))
    return out


def stage_share(dss, num, den="total"):
    """Per-run ratio of two stage timings of FastForest's comparison runs."""
    return [r["extra"]["timings"][num] / r["extra"]["timings"][den] for r in run_json(dss)]


def sc(d):
    """One scalability row in the words of section 3.3."""
    r = SC.loc[d]
    minutes, accuracy = r.select_seconds / 60, 100 * r.test_accuracy
    return f"{fx(r.rows)} × {fx(r.features)} → {r.features_final}; {minutes:.1f}; {accuracy:.2f}"


def l1_by_classes():
    """Whether the L1 selection time rises with the number of classes on the combined tables."""
    pts = sorted(
        (int(D.loc[d, "classes_comparison"]), mean_(d, "l1_logistic", "select_seconds"))
        for d in COMBINED
    )
    rising = all(a[1] < b[1] for a, b in zip(pts, pts[1:], strict=False))
    return ev(rising, "; ".join(f"{k} classes {fx(t)} s" for k, t in pts))


# ------------------------------------------------------------------------- tables
def t2(d):
    r = D.loc[d]
    rows = fx(r.rows_comparison) + (f" ({fx(r.rows_full)})" if r.subsampled else "")
    return row(rows, fx(r.features), int(r.classes_comparison), int(S.loc[(d, FF), "n_runs"]))


def t3f(d):
    return row(*(nf(d, m) for m in T3))


def t3a(d):
    return row(*(acc(d, m) for m in T3))


def t3t(d):
    return row(*(sec(d, m) for m in T3[:4]), "--", "--")


def t4(d):
    r = SC.loc[d]
    return row(
        fx(r.rows),
        fx(r.features),
        int(r.classes),
        int(r.features_final),
        f"{100 * r.test_accuracy:.2f}",
        f"{r.select_seconds / 60:.1f}",
        f"{r.peak_rss_mb / 1000:.1f}",  # peak_rss_mb is ru_maxrss bytes / 1e6 on macOS
    )


# ------------------------------------------------------------------------- code and repo
def default(*names):
    """Constructor defaults of :class:`FastForest`, space-separated."""
    params = inspect.signature(FastForest).parameters
    return " ".join(str(params[n].default) for n in names)


def src(obj):
    return inspect.getsource(obj)


def text(path):
    return Path(path).read_text(encoding="utf-8")


def tracked(path):
    out = subprocess.run(
        ["git", "ls-files", "--", path], capture_output=True, text=True, check=True
    )
    return bool(out.stdout.strip())


def n_tracked(prefix):
    out = subprocess.run(
        ["git", "ls-files", "--", prefix], capture_output=True, text=True, check=True
    )
    return len(out.stdout.split())


def grep_count(pattern, *dirs):
    """Matching lines in the Python files under ``dirs``."""
    rx = re.compile(pattern)
    return sum(
        bool(rx.search(line))
        for d in dirs
        for path in sorted(Path(d).rglob("*.py"))
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def _names(reqs):
    return [re.split(r"[<>=!~\[ ;]", r, maxsplit=1)[0].lower() for r in reqs]


def core_deps():
    return _names(PYPROJECT["project"]["dependencies"])


def extra(name):
    return _names(PYPROJECT["project"]["optional-dependencies"][name])


def ci_pythons():
    ci = yaml.safe_load(text(".github/workflows/ci.yml"))
    return [str(v) for v in ci["jobs"]["test"]["strategy"]["matrix"]["python-version"]]


def qlevels():
    levels = quantile_levels()
    strict = "values > threshold" in src(quantile_threshold_search)
    evidence = f"{len(levels)} levels; kept if importance > threshold: {strict}"
    return f"{levels[0]} {levels[1]} … {levels[-1]} ({evidence})"


def searches_on_val():
    return bool(
        re.search(
            r"quantile_threshold_search\(\s*X_train,\s*y_train,\s*X_val,\s*y_val",
            src(FastForest.fit),
        )
    )


def fits_on_train():
    pre = src(Preprocessor)
    return (
        ".fit(X.iloc[splits.train])" in src(FastForest.fit)
        and "median" in pre
        and "OrdinalEncoder" in pre
    )


def test_only_at_the_end():
    """``X_test`` is built in S0 and used only in the final evaluation block."""
    decide = src(FastForest._final_model) + src(quantile_threshold_search)
    return src(FastForest.fit).count("X_test") == 2 and "X_test" not in decide


def grid(metrics):
    stages = len(metrics)
    splits = len(next(iter(metrics.values())))
    names = len(next(iter(next(iter(metrics.values())).values())))
    return f"{stages} stages × {splits} splits × {names} metrics"


def missing(obj, names):
    return ", ".join(n for n in names if not hasattr(obj, n)) or "none"


def missing_keys(d, names):
    return ", ".join(n for n in names if n not in d) or "none"


def sample_dims(classes=False):
    X, y = load_sample()
    out = f"{fx(X.shape[0])} × {fx(X.shape[1])}"
    return out + (f", {len(set(y))} classes" if classes else "")


def app_controls():
    app = text("app/streamlit_app.py")
    wanted = {
        "upload": "st.file_uploader(",
        "bundled sample": "Use the bundled sample dataset",
        "class column": "Target (class) column",
        "bound": '"Bound (',
        "seed": '"Random seed"',
        "importance": '"Feature importance"',
        "redundancy cut": '"Redundancy cut',
        "progress bar": "st.progress(",
        "download": ".download_button(",
    }
    absent = [k for k, v in wanted.items() if v not in app]
    return f"{len(wanted) - len(absent)}/{len(wanted)}" + (
        f" (missing: {', '.join(absent)})" if absent else ""
    )


def dockerfile_cmd():
    cmd = [line for line in text("Dockerfile").splitlines() if line.startswith("CMD")][-1]
    return json.loads(cmd[3:].strip().rstrip("\\").split(",")[0] + "]")[0]


def nice_level():
    return re.search(r"nice -n (\d+)", text("benchmarks/reproduce.sh")).group(1)


def config_hash():
    return hashlib.sha256((ROOT / "benchmarks" / "config.yaml").read_bytes()).hexdigest()[:16]


def bug_tests():
    """Bug IDs of CHANGELOG "Fixed" that a test names (``b1``, ``B4``, ``_b9``)."""
    fixed_block = text("CHANGELOG.md").split("### Fixed", 1)[1].split("---", 1)[0]
    fixed = sorted(set(re.findall(r"\bB(\d+)\b", fixed_block)), key=int)
    tests = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(Path("tests").glob("test_*.py"))
    )
    named = {n for n in fixed if re.search(rf"(?i)(?<![a-z0-9])b{n}(?![0-9])", tests)}
    rest = [f"B{n}" for n in fixed if n not in named]
    return f"{len(named)}/{len(fixed)} (not named in a test: {' '.join(rest)})"


def body_words():
    """Approximate word count of sections 1–5 (running text only)."""
    start = next(i for i, line in enumerate(TEX) if line.startswith(r"\section{Motivation"))
    end = next(
        i for i, line in enumerate(TEX) if line.startswith(r"\section*{Declaration of competing")
    )
    body = "\n".join(TEX[start:end])
    body = re.sub(
        r"\\begin\{(table|figure|lstlisting|tikzpicture)\}.*?\\end\{\1\}", " ", body, flags=re.S
    )
    body = re.sub(r"(?<!\\)%.*", " ", body)
    body = re.sub(r"\\(cite|ref|label|url)\{[^}]*\}", " ", body)
    body = re.sub(r"\$[^$]*\$", " x ", body)
    body = re.sub(r"\\[a-zA-Z]+\*?", " ", body)
    return fx(len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'.,%\-]*", body)))


def http_status(url):
    if OFFLINE:
        raise Skip("offline")
    try:
        # Cloudflare answers Python's default user agent with 403 whatever the origin's state
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (claims_check.py)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return str(r.status)
    except urllib.error.HTTPError as err:
        return str(err.code)
    except urllib.error.URLError as err:
        return f"unreachable ({err.reason})"


def min_class_count():
    """Smallest class of any prepared table after subsampling (local prepared/*.json)."""
    metas = sorted((ROOT / "benchmarks" / "data" / "prepared").glob("*.json"))
    if not metas:
        raise Skip("benchmarks/data/prepared not present")
    counts = [min(json.loads(p.read_text())["class_counts_comparison"].values()) for p in metas]
    return int(min(counts))


def madelon():
    path = ROOT / "benchmarks" / "data" / "prepared" / "madelon.parquet"
    if not path.exists():
        raise Skip("madelon.parquet not prepared")
    frame = pd.read_parquet(path)
    target = "__target__" if "__target__" in frame else CFG["datasets"]["madelon"]["target"]
    return frame.drop(columns=[target]), {
        str(f) for f in CFG["datasets"]["madelon"]["relevant_features"]
    }


def madelon_corr():
    """Features whose largest |r| with another feature is clearly non-zero."""
    X, relevant = madelon()
    C = np.abs(np.corrcoef(X.to_numpy(float).T))
    np.fill_diagonal(C, 0)
    top = pd.Series(C.max(axis=1), index=X.columns.astype(str))
    hit = set(top[top > 0.5].index)
    probe = top.drop(index=list(relevant)).max()
    weakest = top.loc[sorted(relevant)].min()
    return (
        f"{len(hit)} (= the configured relevant set: {hit == relevant}; largest abs r of a probe "
        f"{probe:.2f}, smallest of a relevant feature {weakest:.2f})"
    )


def madelon_rank():
    """Principal components of the 20 standardised relevant features for 99% of the variance."""
    X, relevant = madelon()
    Z = X[sorted(relevant)].to_numpy(float)
    Z = (Z - Z.mean(axis=0)) / Z.std(axis=0)
    share = np.cumsum(np.linalg.svd(Z, compute_uv=False) ** 2)
    return int(np.searchsorted(share / share[-1], 0.99) + 1)


# ------------------------------------------------------------------------- slow checks
def _listing_source():
    start = next(i for i, line in enumerate(TEX) if line.startswith(r"\begin{lstlisting}"))
    end = next(i for i, line in enumerate(TEX) if line.startswith(r"\end{lstlisting}"))
    return "\n".join(TEX[start + 1 : end])


def _run_listing():
    """Execute the paper's sample code verbatim in a temporary directory."""
    here = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            ns: dict = {}
            exec(compile(_listing_source(), "main.tex listing", "exec"), ns)
            payload = json.loads(Path("fastforest_result.json").read_text())
            files = sorted(p.name for p in Path(tmp).iterdir())
        finally:
            os.chdir(here)
    return {"ok": True, "result": ns["result"], "json": payload, "files": files}


@slow
def listing():
    return _run_listing()


@slow
def seeded_repeat():
    """Two runs of the listing (random_state=0) select the same features."""
    first = listing()["result"].features_final
    return first == _run_listing()["result"].features_final


@slow
def fig_types():
    r = listing()["result"]
    figs = [viz.dendrogram(r.redundancy), viz.importance_bar(r.importances["full"])]
    return sorted({type(f).__module__.split(".")[0] for f in figs})


@slow
def cli():
    """Run the shell command printed after the listing, with --out in a temporary directory."""
    line = next(t for t in TEX if t.startswith(r"\noindent The same run from a shell:"))
    cmd = re.search(r"\\texttt\{(.*)\}\.", line).group(1).replace(r"\_", "_")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "demo"
        cmd = cmd.replace("--out results/demo", f"--out {out}") + " --quiet"
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        seconds = time.perf_counter() - t0
        files = sorted(p.name for p in out.iterdir()) if out.exists() else []
        payload = (
            json.loads((out / "metrics.json").read_text())
            if (out / "metrics.json").exists()
            else {}
        )
        figures = out / "figures"
        kinds = (
            sorted({p.stem.split("_")[0] for p in figures.iterdir()}) if figures.exists() else []
        )
    return {
        "ok": proc.returncode == 0,
        "files": files,
        "json": payload,
        "figure_kinds": kinds,
        "seconds": seconds,
        "stderr": proc.stderr[-500:],
    }


@slow
def tests():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--cov=fastforest",
            "--cov-report=term",
        ],
        capture_output=True,
        text=True,
    )
    passed = re.search(r"(\d+) passed", proc.stdout)
    cover = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", proc.stdout, flags=re.M)
    failed = re.search(r"(\d+) failed", proc.stdout)
    return {
        "passed": passed.group(1) if passed else "0",
        "failed": failed.group(1) if failed else "0",
        "cover": cover.group(1) if cover else "?",
    }


# ------------------------------------------------------------------------- the ledger
CELL_SPLIT = re.compile(r"(?<!\\)\|")
COLUMNS = ["id", "section", "statement", "claimed", "source", "how", "computed", "status", "note"]
LOCKED = {"by construction", "not checkable"}


def parse_row(line):
    cells = [c.strip() for c in CELL_SPLIT.split(line.strip())[1:-1]]
    if len(cells) != len(COLUMNS):
        raise ValueError(f"expected {len(COLUMNS)} cells, got {len(cells)}: {line[:80]}")
    return dict(zip(COLUMNS, cells, strict=True))


def format_row(cells):
    return "| " + " | ".join(cells[c] for c in COLUMNS) + " |"


def unescape(cell):
    return cell.replace(r"\|", "|")


def snippet(cell):
    """The code of a "how to check" cell (one code span), or None for prose."""
    cell = unescape(cell.strip())
    m = re.fullmatch(r"`(.+)`", cell)
    return m.group(1) if m else None


def run_snippet(code):
    if code.startswith("$ "):
        proc = subprocess.run(
            code[2:],
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash",
            timeout=900,
        )
        if proc.returncode != 0 and not proc.stdout.strip():
            raise RuntimeError(proc.stderr.strip()[-300:] or f"exit {proc.returncode}")
        return " ".join(proc.stdout.split())
    value = eval(code, globals())  # the snippets come from this repository's own ledger
    return " ".join(str(value).split())


def strip_evidence(s):
    """Drop a trailing parenthetical (which may itself contain parentheses)."""
    s = s.rstrip()
    if not s.endswith(")"):
        return s
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        depth += {")": 1, "(": -1}.get(s[i], 0)
        if depth == 0:
            return s[:i].rstrip() if i > 0 and s[i - 1] == " " else s
    return s


def norm(s, *, evidence=False):
    """Normalise a value for comparison; ``evidence`` drops a trailing parenthetical."""
    s = unescape(s)
    if evidence:
        s = strip_evidence(s)
    for a, b in [
        ("$\\pm$", "±"),
        ("\\pm", "±"),
        ("\\%", ""),
        ("%", ""),
        ("{,}", ","),
        ("\\times", "×"),
        ("---", "-"),
        ("--", "-"),
        ("–", "-"),
        ("—", "-"),
        ("−", "-"),
        ("$", ""),
        ("~", " "),
        ("\\ldots", "…"),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return re.sub(r"\s*([&×±/;:-])\s*", r"\1", s)


def check_line(cells):
    """Where the statement is in main.tex: '' if on its line, else a message."""
    stmt = unescape(cells["statement"])
    m = re.search(r"L(\d+)", cells["section"])
    if m and 0 < int(m.group(1)) <= len(TEX) and stmt in TEX[int(m.group(1)) - 1]:
        return ""
    found = [i + 1 for i, line in enumerate(TEX) if stmt in line]
    return f"moved to L{found[0]}" if found else "not found in main.tex"


def main(argv=None):
    global SKIP_SLOW, OFFLINE
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--write", action="store_true", help="write computed values and statuses into claims.md"
    )
    ap.add_argument(
        "--skip-slow", action="store_true", help="skip the test suite, CLI and listing runs"
    )
    ap.add_argument("--offline", action="store_true", help="skip the request to the hosted app")
    args = ap.parse_args(argv)
    SKIP_SLOW, OFFLINE = args.skip_slow, args.offline

    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    problems, skipped, rows = [], [], []
    for i, line in enumerate(lines):
        if not re.match(r"^\| C\d{3} \|", line):
            continue
        cells = parse_row(line)
        where = check_line(cells)
        if where:
            problems.append(f"{cells['id']}: statement {where}")
        code = snippet(cells["how"])
        if code is not None:
            try:
                cells["computed"] = run_snippet(code).replace("|", r"\|")
                if cells["status"] not in LOCKED:
                    same = norm(
                        cells["computed"], evidence=not cells["claimed"].rstrip().endswith(")")
                    ) == norm(cells["claimed"])
                    cells["status"] = "reproduced" if same else "differs"
            except Skip as why:
                skipped.append(f"{cells['id']} ({why})")
            except Exception as err:  # any failure is reported in the ledger
                cells["computed"] = f"ERROR: {type(err).__name__}: {err}".replace("|", "/")[:200]
                problems.append(f"{cells['id']}: snippet failed: {err}")
                if cells["status"] not in LOCKED:
                    cells["status"] = "differs"
        lines[i] = format_row(cells)
        rows.append(cells)

    counts = {
        s: sum(r["status"] == s for r in rows)
        for s in ("reproduced", "differs", "not checkable", "by construction")
    }
    summary = (
        f"{len(rows)} claims: {counts['reproduced']} reproduced, {counts['differs']} differ, "
        f"{counts['not checkable']} not checkable, {counts['by construction']} by construction "
        f"(claims_check.py, {date.today().isoformat()}"
        f"{', slow checks skipped' if skipped else ''})."
    )
    text_all = "\n".join(lines)
    text_all = re.sub(
        r"<!-- counts -->.*?<!-- /counts -->",
        f"<!-- counts -->{summary}<!-- /counts -->",
        text_all,
        flags=re.S,
    )

    disc = re.search(r"^## Discrepancies\n(.*?)(?=^## )", text_all, flags=re.S | re.M)
    listed = set(re.findall(r"\bC\d{3}\b", disc.group(1))) if disc else set()
    differs = {r["id"] for r in rows if r["status"] == "differs"}
    for cid in sorted(differs - listed):
        problems.append(f"{cid}: differs but is not listed under ## Discrepancies")
    for cid in sorted(listed - {r["id"] for r in rows}):
        problems.append(f"{cid}: listed under ## Discrepancies but not in the ledger")

    print(summary)
    for r in rows:
        if r["status"] == "differs":
            claimed, computed = unescape(r["claimed"]), unescape(r["computed"])
            print(f"  {r['id']} differs: claimed {claimed!r}, computed {computed!r}")
    if skipped:
        print("skipped: " + ", ".join(skipped))
    for p in problems:
        print("PROBLEM " + p)
    if args.write:
        LEDGER.write_text(text_all + "\n", encoding="utf-8")
        print(f"wrote {LEDGER.relative_to(ROOT)}")
    return 1 if any("snippet failed" in p or "not found" in p for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())

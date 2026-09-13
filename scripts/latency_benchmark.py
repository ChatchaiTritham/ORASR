"""Wall-clock latency and throughput of the committed routing engine.

The manuscript previously reported per-pathway latency and throughput as design
targets derived from assumed per-gate budgets. This driver measures them instead,
on the same seed-42 synthetic cohort the rest of the evaluation uses, by calling
the real ``ORASRRouter``.

Wall-clock numbers are host-specific and are reported as such: the environment
block records the machine they came from, and the portable claim remains the
gate-work reduction in ``scripts/flat_baseline.py``. What this driver removes is
the need to *assume* a per-gate cost.

Configurations compared
-----------------------
The engine exposes three pathways, distinguished by how many gates they run:

    FAST    {G1}                 1 gate
    NORMAL  {G1, G2, G3}         3 gates
    SAFE    {G1, G2, G3, G4}     4 gates

* **ORASR (adaptive)** routes each action at its own risk score, so the cohort
  spreads across all three pathways.
* **Flat monitors** force every action down one pathway regardless of risk, which
  is what a non-adaptive runtime monitor does. Forcing SAFE is the four-gate flat
  monitor; forcing NORMAL is the three-gate one.

Note that the manuscript's "Flat-2 (G1+G2)" configuration does not exist in the
implementation -- there is no two-gate pathway -- so it is not measured here.

Run:  python scripts/latency_benchmark.py
Writes: results/latency_benchmark.json

Variance mode:  python scripts/latency_benchmark.py --trials 30 --out results/latency_benchmark_30.json
additionally stores per-trial totals and per-trial mean latencies per configuration
and seeded (42) percentile-bootstrap 95% CIs of the per-trial mean latency and of the
ORASR/Flat-4 latency and throughput ratios. The default output file is unchanged.
"""

from __future__ import annotations

import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from orasr import ORASRRouter  # noqa: E402
from orasr.constants import DEFAULT_RANDOM_SEED  # noqa: E402

SEED = DEFAULT_RANDOM_SEED
COHORT_SPEC = [("FAST", 3500, 0.00, 0.30),
               ("NORMAL", 4500, 0.30, 0.70),
               ("SAFE", 2000, 0.70, 1.00)]
WARMUP = 500
TRIALS = 3


def build_cohort(rng: random.Random) -> List[Dict[str, Any]]:
    cohort: List[Dict[str, Any]] = []
    for stratum, n, lo, hi in COHORT_SPEC:
        for _ in range(n):
            cohort.append({"stratum": stratum, "risk": rng.uniform(lo, hi)})
    rng.shuffle(cohort)
    return cohort


def identity(data: Any) -> Any:
    return data


def measure(cohort, risk_of, label: str, trials: int = TRIALS,
            keep_trials: bool = False) -> Dict[str, Any]:
    """Route the whole cohort, timing each call. risk_of picks the risk used."""
    router = ORASRRouter(enable_fast_path=True, enable_audit=False)

    for s in cohort[:WARMUP]:
        router.route(action=identity, input_data={"payload": 1},
                     risk_score=risk_of(s), human_approved=True)

    per_trial_total: List[float] = []
    lat_by_path: Dict[str, List[float]] = {"FAST": [], "NORMAL": [], "SAFE": []}
    counts: Dict[str, int] = {"FAST": 0, "NORMAL": 0, "SAFE": 0}

    per_trial_mean: List[float] = []
    for trial in range(trials):
        trial_sum = 0.0
        t_all = time.perf_counter()
        for s in cohort:
            t0 = time.perf_counter()
            res = router.route(action=identity, input_data={"payload": 1},
                               risk_score=risk_of(s), human_approved=True)
            dt = (time.perf_counter() - t0) * 1000.0
            path = str(getattr(res, "path", "")).split(".")[-1].upper()
            if path not in lat_by_path:
                path = "SAFE"
            if trial == 0:
                counts[path] += 1
            lat_by_path[path].append(dt)
            trial_sum += dt
        per_trial_total.append(time.perf_counter() - t_all)
        per_trial_mean.append(trial_sum / len(cohort))

    allt = [x for v in lat_by_path.values() for x in v]

    def pct(xs, q):
        if not xs:
            return None
        s = sorted(xs)
        return round(s[min(len(s) - 1, int(q * len(s)))], 5)

    best = min(per_trial_total)
    out = {
        "configuration": label,
        "n_actions": len(cohort),
        "trials": trials,
        "pathway_counts_first_trial": counts,
        "throughput_actions_per_s": round(len(cohort) / best, 1),
        "wall_clock_s_best_trial": round(best, 4),
        "latency_ms": {
            "mean": round(statistics.fmean(allt), 5),
            "p50": pct(allt, 0.50),
            "p95": pct(allt, 0.95),
            "p99": pct(allt, 0.99),
            "max": round(max(allt), 5),
        },
        "latency_ms_by_pathway": {
            p: {"n": len(v),
                "mean": round(statistics.fmean(v), 5) if v else None,
                "p95": pct(v, 0.95)}
            for p, v in lat_by_path.items()
        },
    }
    if keep_trials:
        out["per_trial_total_s"] = [round(x, 6) for x in per_trial_total]
        out["per_trial_mean_latency_ms"] = [round(x, 6) for x in per_trial_mean]
        out["per_trial_throughput_actions_per_s"] = [
            round(len(cohort) / x, 2) for x in per_trial_total]
    return out


def bootstrap_ci(stat, arrays, n_boot: int = 10000, seed: int = SEED):
    """Percentile bootstrap (independent resampling of each array's trials)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    arrs = [np.asarray(a, dtype=float) for a in arrays]
    boots = np.empty(n_boot)
    for b in range(n_boot):
        boots[b] = stat(*[a[rng.integers(0, len(a), len(a))] for a in arrs])
    point = stat(*arrs)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"estimate": round(float(point), 6), "ci95": [round(float(lo), 6), round(float(hi), 6)],
            "n_boot": n_boot, "seed": seed}


def variance_run(trials: int, out_path: Path) -> int:
    import numpy as np

    rng = random.Random(SEED)
    cohort = build_cohort(rng)
    specs = [(lambda s: s["risk"], "ORASR (adaptive)"),
             (lambda s: 0.95, "Flat monitor, 4 gates (forced SAFE)"),
             (lambda s: 0.50, "Flat monitor, 3 gates (forced NORMAL)"),
             (lambda s: 0.10, "Single gate (forced FAST)")]
    results = [measure(cohort, f, label, trials=trials, keep_trials=True) for f, label in specs]
    for r in results:
        r["per_trial_mean_latency_ms_summary"] = bootstrap_ci(
            lambda a: a.mean(), [r["per_trial_mean_latency_ms"]])
    adaptive, flat4 = results[0], results[1]
    out = {
        "seed": SEED,
        "trials": trials,
        "warmup_calls": WARMUP,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "note": ("Wall-clock figures are specific to this host. Configurations are run "
                 "sequentially (all trials of one configuration, then the next), so "
                 "ratio CIs resample each configuration's trials independently."),
        "configurations": results,
        "orasr_vs_flat4": {
            "latency_ratio_orasr_over_flat4": bootstrap_ci(
                lambda a, f: a.mean() / f.mean(),
                [adaptive["per_trial_mean_latency_ms"], flat4["per_trial_mean_latency_ms"]]),
            "throughput_ratio_orasr_over_flat4": bootstrap_ci(
                lambda a, f: a.mean() / f.mean(),
                [adaptive["per_trial_throughput_actions_per_s"],
                 flat4["per_trial_throughput_actions_per_s"]]),
        },
        "numpy": np.__version__,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    for r in results:
        print(r["configuration"], r["per_trial_mean_latency_ms_summary"])
    print(json.dumps(out["orasr_vs_flat4"]))
    return 0


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.trials is not None or args.out is not None:
        out_path = args.out or ROOT / "results" / f"latency_benchmark_{args.trials or TRIALS}.json"
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        return variance_run(args.trials or TRIALS, out_path)

    rng = random.Random(SEED)
    cohort = build_cohort(rng)

    results = [
        measure(cohort, lambda s: s["risk"], "ORASR (adaptive)"),
        measure(cohort, lambda s: 0.95, "Flat monitor, 4 gates (forced SAFE)"),
        measure(cohort, lambda s: 0.50, "Flat monitor, 3 gates (forced NORMAL)"),
        measure(cohort, lambda s: 0.10, "Single gate (forced FAST)"),
    ]

    adaptive, flat4 = results[0], results[1]
    out = {
        "seed": SEED,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
        "note": ("Wall-clock figures are specific to this host. The portable claim "
                 "is the gate-work reduction reported by scripts/flat_baseline.py."),
        "configurations": results,
        "adaptive_vs_flat4": {
            "latency_mean_ratio": round(
                flat4["latency_ms"]["mean"] / adaptive["latency_ms"]["mean"], 2),
            "throughput_ratio": round(
                adaptive["throughput_actions_per_s"]
                / flat4["throughput_actions_per_s"], 2),
            "latency_reduction_pct": round(
                100.0 * (1 - adaptive["latency_ms"]["mean"]
                         / flat4["latency_ms"]["mean"]), 1),
        },
    }

    (ROOT / "results").mkdir(exist_ok=True)
    with open(ROOT / "results" / "latency_benchmark.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")

    for r in results:
        print(f"{r['configuration']:38s} mean={r['latency_ms']['mean']:.5f} ms  "
              f"p95={r['latency_ms']['p95']:.5f}  "
              f"{r['throughput_actions_per_s']:>10,.0f} actions/s")
    print("\nadaptive vs 4-gate flat monitor:",
          json.dumps(out["adaptive_vs_flat4"]))
    print("host:", out["environment"]["platform"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Deterministic reproducibility driver for ORASR.

Runs only what the committed source code supports, with a fixed seed, and
writes machine-readable artifacts to ``results/``.

What this driver DOES reproduce (deterministic, portable):
  1. Structural properties of the routing engine verified at runtime:
       - pathway-selection thresholds (0.3 / 0.7);
       - monotonic gate inclusion (FAST=1 gate, NORMAL=3, SAFE=4);
       - non-bypass behaviour (a failed gate marks the routing unsafe and the
         action is not executed).
  2. A synthetic routing cohort (3,500 Fast / 4,500 Normal / 2,000 Safe) routed
     through the real ``ORASRRouter``, producing the pathway distribution and an
     honestly measured gate pass rate.

What this driver does NOT fabricate:
  - Pathway LATENCIES are measured on the current host and written with an
    explicit ``environment`` block. They are wall-clock timings of THIS machine
    and are not portable; the manuscript's literal values (2.3 / 45.2 / 287.5 ms)
    are NOT copied here.
  - The MIMIC-IV retrospective analysis and the flat-monitor baseline are NOT
    reproduced: no clinical dataset and no baseline implementation are committed.
    These gaps are recorded in ``results/gaps.json``.

Usage:
    python scripts/run_all.py
"""

from __future__ import annotations

import csv
import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RESULTS = ROOT / "results"
sys.path.insert(0, str(SRC))

from orasr import ORASRRouter, ReasoningPath  # noqa: E402
from orasr.constants import DEFAULT_RANDOM_SEED  # noqa: E402

SEED = DEFAULT_RANDOM_SEED  # 42, sourced from the package constant


# --------------------------------------------------------------------------
# 1. Structural verification (deterministic, host-independent)
# --------------------------------------------------------------------------
def verify_structure() -> Dict[str, Any]:
    """Verify the routing structure directly against the committed engine."""
    router = ORASRRouter(enable_fast_path=True, enable_audit=False)

    thresholds = {
        "fast_path_threshold": router.FAST_PATH_THRESHOLD,
        "safe_path_threshold": router.SAFE_PATH_THRESHOLD,
        "fast_threshold_expected_0_3": router.FAST_PATH_THRESHOLD == 0.3,
        "safe_threshold_expected_0_7": router.SAFE_PATH_THRESHOLD == 0.7,
    }

    # Gate counts per pathway, read straight from the engine configuration.
    gate_counts = {
        path.name: len(router.pathways[path].gates)
        for path in (ReasoningPath.FAST, ReasoningPath.NORMAL, ReasoningPath.SAFE)
    }
    monotonic = gate_counts["FAST"] < gate_counts["NORMAL"] < gate_counts["SAFE"]

    # Gate inclusion is a strict superset chain (monotonic inclusion, not just count).
    fast_gates = set(router.pathways[ReasoningPath.FAST].gates)
    normal_gates = set(router.pathways[ReasoningPath.NORMAL].gates)
    safe_gates = set(router.pathways[ReasoningPath.SAFE].gates)
    inclusion_chain = fast_gates < normal_gates < safe_gates

    # Threshold partition: probe representative risk scores.
    def selected(risk: float) -> str:
        return router._select_pathway(risk, require_approval=False).name

    partition_probe = {
        "rho_0.00": selected(0.00),
        "rho_0.29": selected(0.29),
        "rho_0.30": selected(0.30),
        "rho_0.50": selected(0.50),
        "rho_0.69": selected(0.69),
        "rho_0.70": selected(0.70),
        "rho_1.00": selected(1.00),
    }
    partition_ok = (
        partition_probe["rho_0.00"] == "FAST"
        and partition_probe["rho_0.29"] == "FAST"
        and partition_probe["rho_0.30"] == "NORMAL"
        and partition_probe["rho_0.50"] == "NORMAL"
        and partition_probe["rho_0.69"] == "NORMAL"
        and partition_probe["rho_0.70"] == "SAFE"
        and partition_probe["rho_1.00"] == "SAFE"
    )

    # Non-bypass: a failed precondition gate must keep the action from executing.
    sentinel = {"ran": False}

    def tracking_action(_data: Any) -> str:
        sentinel["ran"] = True
        return "executed"

    bad = router.route(action=tracking_action, input_data=None, risk_score=0.1)
    non_bypass_ok = (not bad.safe) and (bad.action_result is None) and (not sentinel["ran"])

    return {
        "thresholds": thresholds,
        "gate_counts": gate_counts,
        "monotonic_gate_count": monotonic,
        "monotonic_gate_inclusion_chain": inclusion_chain,
        "partition_probe": partition_probe,
        "partition_correct": partition_ok,
        "non_bypass_holds": non_bypass_ok,
        "all_structural_checks_pass": bool(
            thresholds["fast_threshold_expected_0_3"]
            and thresholds["safe_threshold_expected_0_7"]
            and monotonic
            and inclusion_chain
            and partition_ok
            and non_bypass_ok
        ),
    }


# --------------------------------------------------------------------------
# 2. Synthetic cohort routing (deterministic structure, measured latency)
# --------------------------------------------------------------------------
COHORT_SPEC = [
    ("FAST", 3500, 0.00, 0.30),
    ("NORMAL", 4500, 0.30, 0.70),
    ("SAFE", 2000, 0.70, 1.00),
]


def build_cohort(rng: random.Random) -> List[Dict[str, Any]]:
    """Build the stratified synthetic scenario cohort (10,000 scenarios)."""
    cohort: List[Dict[str, Any]] = []
    for stratum, n, lo, hi in COHORT_SPEC:
        for _ in range(n):
            cohort.append({"stratum": stratum, "risk": rng.uniform(lo, hi)})
    rng.shuffle(cohort)
    return cohort


def run_cohort() -> Dict[str, Any]:
    """Route the synthetic cohort through the real engine.

    Structure (pathway assignment, gate pass/fail) is deterministic given the
    seed; latency is the wall-clock time measured on this host.
    """
    rng = random.Random(SEED)
    cohort = build_cohort(rng)

    router = ORASRRouter(enable_fast_path=True, enable_audit=True)

    def identity_action(data: Any) -> Any:
        return data

    pathway_counts: Dict[str, int] = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
    latencies_by_path: Dict[str, List[float]] = {"FAST": [], "NORMAL": [], "SAFE": []}
    passed = 0
    blocked = 0

    for scenario in cohort:
        # Safe pathway requires human approval; grant it so the scenario reflects
        # an approved high-risk action (matching the cohort design).
        result = router.route(
            action=identity_action,
            input_data={"payload": 1},
            risk_score=scenario["risk"],
            human_approved=True,
        )
        pathway_counts[result.path.name] += 1
        latencies_by_path[result.path.name].append(result.latency * 1000.0)  # ms
        if result.safe:
            passed += 1
        else:
            blocked += 1

    total = len(cohort)

    def summarise(vals: List[float]) -> Dict[str, float]:
        if not vals:
            return {"n": 0, "mean_ms": None, "p95_ms": None}
        ordered = sorted(vals)
        idx = max(0, int(round(0.95 * (len(ordered) - 1))))
        return {
            "n": len(vals),
            "mean_ms": round(statistics.fmean(vals), 4),
            "p95_ms": round(ordered[idx], 4),
        }

    return {
        "total_scenarios": total,
        "pathway_distribution": pathway_counts,
        "pathway_distribution_pct": {
            k: round(100.0 * v / total, 2) for k, v in pathway_counts.items()
        },
        "gate_pass_rate_pct": round(100.0 * passed / total, 4),
        "blocked": blocked,
        "latency_measured_ms": {k: summarise(v) for k, v in latencies_by_path.items()},
        "latency_note": (
            "Latencies are wall-clock timings measured on THIS host (see "
            "environment block). They are environment-specific and are NOT the "
            "manuscript literals."
        ),
    }


def environment_block() -> Dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
        "seed": SEED,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def gaps_block() -> Dict[str, Any]:
    return {
        "mimic_iv_retrospective": {
            "status": "NOT REPRODUCIBLE",
            "reason": (
                "No MIMIC-IV data, extraction code, or risk-assignment mapping is "
                "committed. The 8,412-action corpus and its 58.1/31.5/10.4% "
                "distribution cannot be regenerated from this repository."
            ),
        },
        "flat_monitor_baseline": {
            "status": "NOT REPRODUCIBLE",
            "reason": (
                "No flat runtime-monitor implementation is committed, so the "
                "86% latency-reduction and 7.3x figures cannot be recomputed."
            ),
        },
        "manuscript_latency_literals": {
            "status": "ENVIRONMENT-SPECIFIC",
            "reason": (
                "Latencies depend on host hardware/load. This driver measures "
                "latency on the current machine and labels it as such; it does "
                "not reproduce the manuscript's specific values."
            ),
        },
        "gate_pass_rate_98_7": {
            "status": "NOT REPRODUCIBLE AS PUBLISHED",
            "reason": (
                "The committed gate validators pass for well-formed inputs, so a "
                "clean synthetic cohort yields a 100% pass rate. The 98.7% rate "
                "and the 130-block breakdown depend on a failure-injection / "
                "malformed-input mix that is not committed and is not "
                "reconstructed here (no tuning to match the paper)."
            ),
        },
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    structure = verify_structure()
    cohort = run_cohort()
    env = environment_block()
    gaps = gaps_block()

    # JSON artifacts.
    (RESULTS / "structural_verification.json").write_text(
        json.dumps(structure, indent=2), encoding="utf-8"
    )
    (RESULTS / "synthetic_cohort.json").write_text(
        json.dumps({"environment": env, **cohort}, indent=2), encoding="utf-8"
    )
    (RESULTS / "gaps.json").write_text(json.dumps(gaps, indent=2), encoding="utf-8")

    # CSV: pathway distribution (consumed by the figure script).
    with (RESULTS / "pathway_distribution.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pathway", "count", "pct", "mean_latency_ms", "p95_latency_ms"])
        for path in ("FAST", "NORMAL", "SAFE"):
            lat = cohort["latency_measured_ms"][path]
            writer.writerow(
                [
                    path,
                    cohort["pathway_distribution"][path],
                    cohort["pathway_distribution_pct"][path],
                    lat["mean_ms"],
                    lat["p95_ms"],
                ]
            )

    # CSV: threshold band map (consumed by the figure script).
    with (RESULTS / "threshold_bands.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pathway", "rho_low", "rho_high", "n_gates"])
        writer.writerow(["FAST", 0.0, structure["thresholds"]["fast_path_threshold"], 1])
        writer.writerow(
            [
                "NORMAL",
                structure["thresholds"]["fast_path_threshold"],
                structure["thresholds"]["safe_path_threshold"],
                3,
            ]
        )
        writer.writerow(["SAFE", structure["thresholds"]["safe_path_threshold"], 1.0, 4])

    print("Structural checks pass:", structure["all_structural_checks_pass"])
    print("Pathway distribution:", cohort["pathway_distribution"])
    print("Gate pass rate (clean cohort):", cohort["gate_pass_rate_pct"], "%")
    print("Measured latency (ms, host-specific):")
    for path in ("FAST", "NORMAL", "SAFE"):
        print("  ", path, cohort["latency_measured_ms"][path])
    print("Artifacts written to", RESULTS)


if __name__ == "__main__":
    main()

"""Flat-monitor vs ORASR adaptive-routing baseline (reproducible, host-independent).

This driver reproduces the *gate-work* part of the manuscript's efficiency claim
WITHOUT relying on wall-clock latency, which is environment-specific.

Definitions
-----------
* **Gate-evaluation count** = the number of safety-gate ``check()`` calls the
  monitor performs for one routed action. This is a deterministic, machine-
  independent integer that we count by instrumenting the *real* committed gates
  (``SafetyGate.check`` is wrapped, so the count comes from the engine, not from
  a hand-written formula).
* **ORASR (adaptive)** evaluates only the gates in the selected pathway:
  FAST -> {G1}; NORMAL -> {G1,G2,G3}; SAFE -> {G1,G2,G3,G4}. The POSTCONDITION
  gate (G4) is evaluated after the action runs, so for SAFE it adds one more
  evaluation when the action executes.
* **Flat monitor** evaluates *every* gate on *every* action regardless of risk
  (the baseline a non-adaptive runtime monitor would use). With four committed
  gates that is a constant 4 evaluations per call.

What is reproducible here
-------------------------
* expected gate-evaluations / call (ORASR vs flat) on the seed-42 synthetic
  cohort,
* the **gate-work reduction %** = 1 - (ORASR evals / flat evals),
* the **throughput ratio** = flat evals / ORASR evals (work-normalised, i.e. how
  many more actions ORASR can clear per unit of gate-work).

What is NOT reproducible here (and is labelled as such)
-------------------------------------------------------
* Absolute wall-clock latency reductions (the manuscript's ~84-86% / 7.3x in
  milliseconds) are HOST-dependent: they depend on per-gate cost, hardware, and
  load. We measure per-host latency for transparency but do not claim the
  manuscript literals. The gate-work reduction is the portable invariant.
* The MIMIC-IV action mix (58.1/31.5/10.4%) is credentialed data; the same
  arithmetic applied to that mix gives the manuscript's ~1.94 evals/call, but
  that mix cannot be regenerated here (see ``scripts/extract_mimic.py``).

Usage:
    python scripts/flat_baseline.py
"""

from __future__ import annotations

import json
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RESULTS = ROOT / "results"
sys.path.insert(0, str(SRC))

from orasr import ORASRRouter, ReasoningPath, SafetyGate  # noqa: E402
from orasr.constants import DEFAULT_RANDOM_SEED  # noqa: E402

SEED = DEFAULT_RANDOM_SEED  # 42

# Synthetic cohort identical to scripts/run_all.py (seed-42 stratified, 10,000).
COHORT_SPEC = [
    ("FAST", 3500, 0.00, 0.30),
    ("NORMAL", 4500, 0.30, 0.70),
    ("SAFE", 2000, 0.70, 1.00),
]


def build_cohort(rng: random.Random) -> List[Dict[str, Any]]:
    cohort: List[Dict[str, Any]] = []
    for stratum, n, lo, hi in COHORT_SPEC:
        for _ in range(n):
            cohort.append({"stratum": stratum, "risk": rng.uniform(lo, hi)})
    rng.shuffle(cohort)
    return cohort


class _CountingGate(SafetyGate):
    """SafetyGate that records every check() call into a shared counter."""

    def __init__(self, inner: SafetyGate, counter: Dict[str, int]):
        super().__init__(inner.gate_type, inner.validator, inner.name, inner.description)
        self._counter = counter

    def check(self, context: Dict[str, Any]):
        self._counter["evals"] += 1
        return super().check(context)


def _instrument(router: ORASRRouter, counter: Dict[str, int]) -> None:
    """Wrap every gate on the router so check() calls are counted by the engine."""
    for gtype, gate in list(router.gates.items()):
        router.gates[gtype] = _CountingGate(gate, counter)


def _adaptive_evals_for_risk(risk: float) -> int:
    """Gate evaluations ORASR performs for a single action (counted from engine)."""
    counter = {"evals": 0}
    router = ORASRRouter(enable_fast_path=True, enable_audit=False)
    _instrument(router, counter)

    def identity_action(data: Any) -> Any:
        return data

    router.route(
        action=identity_action,
        input_data={"payload": 1},
        risk_score=risk,
        human_approved=True,  # let SAFE execute so its POSTCONDITION gate is counted
    )
    return counter["evals"]


def _flat_evals(router: ORASRRouter) -> int:
    """A flat monitor checks every committed gate once per action."""
    return len(router.gates)


def run() -> Dict[str, Any]:
    rng = random.Random(SEED)
    cohort = build_cohort(rng)

    # Count ORASR (adaptive) gate evaluations from the real engine, per scenario.
    counter = {"evals": 0}
    router = ORASRRouter(enable_fast_path=True, enable_audit=False)
    _instrument(router, counter)

    def identity_action(data: Any) -> Any:
        return data

    flat_per_call = _flat_evals(router)  # constant 4 (number of committed gates)

    adaptive_evals_total = 0
    flat_evals_total = 0
    by_lane: Dict[str, Dict[str, int]] = {
        k: {"n": 0, "adaptive_evals": 0} for k in ("FAST", "NORMAL", "SAFE")
    }
    # Per-lane adaptive cost, counted once from the engine (deterministic per lane).
    lane_adaptive_cost = {
        "FAST": _adaptive_evals_for_risk(0.10),
        "NORMAL": _adaptive_evals_for_risk(0.50),
        "SAFE": _adaptive_evals_for_risk(0.90),
    }

    # Latency measured per host, purely for transparency (NOT a manuscript literal).
    lat_by_lane: Dict[str, List[float]] = {"FAST": [], "NORMAL": [], "SAFE": []}

    for sc in cohort:
        before = counter["evals"]
        t0 = time.perf_counter()
        result = router.route(
            action=identity_action,
            input_data={"payload": 1},
            risk_score=sc["risk"],
            human_approved=True,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        lane = result.path.name
        adaptive_this = counter["evals"] - before
        adaptive_evals_total += adaptive_this
        flat_evals_total += flat_per_call
        by_lane[lane]["n"] += 1
        by_lane[lane]["adaptive_evals"] += adaptive_this
        lat_by_lane[lane].append(dt_ms)

    n = len(cohort)
    adaptive_per_call = adaptive_evals_total / n
    flat_per_call_mean = flat_evals_total / n
    gate_work_reduction = 1.0 - (adaptive_evals_total / flat_evals_total)
    throughput_ratio = flat_evals_total / adaptive_evals_total

    # Per-host latency (transparency only).
    def mean(v: List[float]) -> float:
        return round(sum(v) / len(v), 6) if v else 0.0

    lat_overall = [x for v in lat_by_lane.values() for x in v]

    return {
        "seed": SEED,
        "cohort_size": n,
        "n_committed_gates": flat_per_call,
        "lane_adaptive_cost_evals": lane_adaptive_cost,
        "lane_counts": {k: v["n"] for k, v in by_lane.items()},
        "gate_work": {
            "orasr_total_evals": adaptive_evals_total,
            "flat_total_evals": flat_evals_total,
            "orasr_evals_per_call": round(adaptive_per_call, 6),
            "flat_evals_per_call": round(flat_per_call_mean, 6),
            "gate_work_reduction_pct": round(100.0 * gate_work_reduction, 4),
            "throughput_ratio_worknorm": round(throughput_ratio, 6),
            "note": (
                "Counts come from instrumenting the committed SafetyGate.check on "
                "the real ORASRRouter; deterministic and host-independent. "
                "Throughput ratio is work-normalised (flat evals / ORASR evals), "
                "NOT a wall-clock speedup."
            ),
        },
        "latency_host_specific_ms": {
            "overall_mean_ms": mean(lat_overall),
            "by_lane_mean_ms": {k: mean(v) for k, v in lat_by_lane.items()},
            "note": (
                "Wall-clock latency on THIS host only. Absolute ms reductions "
                "(manuscript ~84-86% / 7.3x) are environment-specific and are NOT "
                "reproduced as literals; the gate-work reduction above is the "
                "portable, reproducible quantity."
            ),
        },
        "manuscript_cross_reference": {
            "manuscript_orasr_evals_per_call": 1.94,
            "manuscript_flat_evals_per_call": 4.0,
            "manuscript_gate_work_reduction_pct": 51.0,
            "explanation": (
                "The manuscript's 1.94 evals/call derives from the MIMIC-IV action "
                "mix (58.1/31.5/10.4%): 0.581*1 + 0.315*3 + 0.104*4 = 1.942. The "
                "synthetic seed-42 cohort here uses a different (heavier) mix "
                "(35/45/20%), so its evals/call differs; the same arithmetic is "
                "applied transparently. The MIMIC mix requires credentialed data "
                "(see scripts/extract_mimic.py)."
            ),
            "mimic_mix_evals_per_call_if_regenerated": round(
                0.581 * lane_adaptive_cost["FAST"]
                + 0.315 * lane_adaptive_cost["NORMAL"]
                + 0.104 * lane_adaptive_cost["SAFE"],
                4,
            ),
        },
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


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    res = run()
    out = {"environment": environment_block(), **res}
    (RESULTS / "flat_baseline.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )

    gw = res["gate_work"]
    print("Flat-monitor vs ORASR adaptive routing (seed 42, synthetic cohort)")
    print("  committed gates:", res["n_committed_gates"])
    print("  per-lane adaptive cost (evals):", res["lane_adaptive_cost_evals"])
    print("  ORASR evals/call :", gw["orasr_evals_per_call"])
    print("  flat  evals/call :", gw["flat_evals_per_call"])
    print("  gate-work reduction:", gw["gate_work_reduction_pct"], "%")
    print("  throughput ratio (work-normalised):", gw["throughput_ratio_worknorm"], "x")
    print(
        "  [cross-ref] MIMIC-mix evals/call if regenerated:",
        res["manuscript_cross_reference"]["mimic_mix_evals_per_call_if_regenerated"],
    )
    print("  latency (host-specific, NOT a literal):",
          res["latency_host_specific_ms"]["overall_mean_ms"], "ms mean")
    print("Artifact written to", RESULTS / "flat_baseline.json")


if __name__ == "__main__":
    main()

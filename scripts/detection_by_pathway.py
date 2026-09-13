"""Fault detection by pathway: default vs demonstration configuration.

Deterministic (seed 42, synthetic). Faults are injected on actions drawn from
each stratum of the seed-42 cohort (scripts/latency_benchmark.build_cohort), so
the router selects FAST / NORMAL / SAFE from the action's own risk score -- no
pathway is forced. As in scripts/ablation.py each fault trips exactly one gate's
failure mode, and ``human_approved=True`` is supplied so approval gating does
not mask gate behaviour. A fault is DETECTED when the route returns
``safe == False``.

Fault classes
-------------
G1  input_data=None (malformed input)
G2  action declared with a class whose ceiling is below rho
    (demo policy; default config has no class policy)
G3  caller-reported elapsed_time = 5.0 s > 2.0 s time limit
    (demo constraint; default config has no constraints)
G4  action returns None (invalid result)

Per stratum and class: N_PER_CELL faults. G2 faults need rho above the lowest
ceiling (0.20), so FAST-stratum G2 faults are drawn from rho in (0.20, 0.30).

Also reported: clean-cohort false blocks (all 10,000 actions, well-formed,
approved, admissible class) and gate / constraint evaluations per call.

Output: results/detection_by_pathway.json
"""

from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import latency_benchmark as lb  # noqa: E402
from demo_config import (  # noqa: E402
    CLASS_CEILINGS, MAX_ELAPSED_S, build_default_router, build_demo_router,
    lowest_admissible_class,
)
from orasr import GateType  # noqa: E402

logging.disable(logging.CRITICAL)

SEED = lb.SEED
N_PER_CELL = 500
STRATA = ("FAST", "NORMAL", "SAFE")
FAULTS = ("G1", "G2", "G3", "G4")


def _violating_class(rho: float) -> str:
    """Highest-ceiling class whose ceiling is still strictly below rho."""
    below = [(c, v) for c, v in CLASS_CEILINGS.items() if v < rho]
    return max(below, key=lambda kv: kv[1])[0]


def build_faults(cohort: List[Dict[str, Any]], rng: random.Random) -> List[Dict[str, Any]]:
    faults = []
    for stratum in STRATA:
        members = [c["risk"] for c in cohort if c["stratum"] == stratum]
        g2_pool = [r for r in members if r > min(CLASS_CEILINGS.values())]
        for fault in FAULTS:
            pool = g2_pool if fault == "G2" else members
            for _ in range(N_PER_CELL):
                rho = rng.choice(pool)
                sc = {"stratum": stratum, "fault": fault, "risk": rho,
                      "input_data": {"payload": 1},
                      "action_class": lowest_admissible_class(rho),
                      "elapsed_time": 0.0, "result_valid": True}
                if fault == "G1":
                    sc["input_data"] = None
                elif fault == "G2":
                    sc["action_class"] = _violating_class(rho)
                elif fault == "G3":
                    sc["elapsed_time"] = 5.0
                else:
                    sc["result_valid"] = False
                faults.append(sc)
    return faults


def _instrument(router) -> Dict[str, int]:
    counts = {"gate_evals": 0, "constraint_evals": 0}
    for gtype, gate in router.gates.items():
        orig = gate.check

        def wrapped(ctx, _orig=orig):
            counts["gate_evals"] += 1
            return _orig(ctx)
        gate.check = wrapped
    for con in router.constraints:
        orig_v = con.validate

        def wrapped_v(ctx, _orig=orig_v):
            counts["constraint_evals"] += 1
            return _orig(ctx)
        con.validate = wrapped_v
    return counts


def _route(router, sc):
    valid = sc["result_valid"]
    return router.route(action=lambda d: {"ok": 1} if valid else None,
                        input_data=sc["input_data"], risk_score=sc["risk"],
                        action_class=sc["action_class"],
                        elapsed_time=sc["elapsed_time"], human_approved=True)


def evaluate(name: str, factory: Callable, cohort, faults) -> Dict[str, Any]:
    router = factory(enable_audit=False)
    counts = _instrument(router)

    # Clean cohort: false blocks and evaluation cost per call.
    clean_blocks: Dict[str, int] = {p: 0 for p in STRATA}
    clean_n: Dict[str, int] = {p: 0 for p in STRATA}
    for c in cohort:
        res = _route(router, {"risk": c["risk"], "input_data": {"payload": 1},
                              "action_class": lowest_admissible_class(c["risk"]),
                              "elapsed_time": 0.0, "result_valid": True})
        clean_n[res.path.name] += 1
        clean_blocks[res.path.name] += (not res.safe)
    n = len(cohort)
    per_call = {"gate_evals_per_call": round(counts["gate_evals"] / n, 4),
                "constraint_evals_per_call": round(counts["constraint_evals"] / n, 4)}

    table: Dict[str, Dict[str, Dict[str, int]]] = {
        p: {f: {"injected": 0, "detected": 0, "undetected": 0} for f in FAULTS}
        for p in STRATA}
    path_mismatch = 0
    multi_cause = 0
    for sc in faults:
        res = _route(router, sc)
        p = res.path.name
        path_mismatch += p != sc["stratum"]
        cell = table[p][sc["fault"]]
        cell["injected"] += 1
        if res.safe:
            cell["undetected"] += 1
        else:
            cell["detected"] += 1
            multi_cause += len(res.violations) != 1
    detected_classes = {p: [f for f in FAULTS if table[p][f]["detected"] > 0] for p in STRATA}
    return {
        "configuration": name,
        "clean_cohort": {"n": n, "pathway_counts": clean_n,
                         "false_blocks_by_pathway": clean_blocks, **per_call},
        "faults_by_pathway": table,
        "fault_classes_detected_by_pathway": detected_classes,
        "checks": {"fault_route_pathway_mismatches": path_mismatch,
                   "detected_faults_with_more_than_one_violation": multi_cause},
    }


def run() -> Dict[str, Any]:
    cohort = lb.build_cohort(random.Random(SEED))
    faults = build_faults(cohort, random.Random(SEED))
    return {
        "seed": SEED,
        "n_faults_per_stratum_and_class": N_PER_CELL,
        "n_faults_total": len(faults),
        "fault_definitions": {
            "G1": "input_data=None",
            "G2": "action_class ceiling below rho (FAST-stratum faults use rho in (0.20,0.30))",
            "G3": f"elapsed_time=5.0 s > time_limit {MAX_ELAPSED_S} s",
            "G4": "action returns None",
        },
        "detected_definition": "route() returned safe == False; human_approved=True supplied",
        "demo_policy": {"class_ceilings": CLASS_CEILINGS,
                        "constraints": ["time_limit_constraint(2.0)",
                                        "risk_threshold_constraint(1.0)",
                                        "approval_required_constraint() scoped to escalation|critical"]},
        "configurations": {
            "default": evaluate("default (shipped)", build_default_router, cohort, faults),
            "demo": evaluate("demonstration (scripts/demo_config.py)", build_demo_router,
                             cohort, faults),
        },
    }


def main() -> None:
    out = run()
    path = ROOT / "results" / "detection_by_pathway.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for key, cfg in out["configurations"].items():
        print(key, "classes detected:", cfg["fault_classes_detected_by_pathway"],
              "| clean false blocks:", cfg["clean_cohort"]["false_blocks_by_pathway"],
              "| gate evals/call:", cfg["clean_cohort"]["gate_evals_per_call"],
              "| checks:", cfg["checks"])
        for p in STRATA:
            print("  ", p, {f: (v["detected"], v["undetected"])
                            for f, v in cfg["faults_by_pathway"][p].items()})
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()

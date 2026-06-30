"""Progressive gate-removal ablation with deterministic failure injection.

Fully reproducible (seed 42, SYNTHETIC only -- no MIMIC, no host timing).

Idea
----
Each committed gate detects exactly one failure mode:

  * G1 PRECONDITION         -> malformed / non-dict input_data
  * G2 RISK_ASSESSMENT      -> risk_score above the action's max_risk budget
  * G3 CONSTRAINT_VALIDATION-> a registered routing constraint is violated
  * G4 POSTCONDITION        -> the action result is invalid (None)

For each gate we build 1,000 failure scenarios (seed 42) that trip *only* that
gate's failure mode while leaving the other gates satisfiable, then route them
through a router configured with a chosen subset of gates. A failure is
"undetected" (coverage loss) when the engine returns ``safe == True`` even
though the scenario carries an injected fault -- i.e. the action was allowed to
execute on a faulty premise.

We evaluate several configurations:
  * FULL                : all four gates active (G1,G2,G3,G4) -- the ORASR config
  * minus-G1 .. minus-G4: one gate removed at a time
  * G1-only .. progressive build-up                          (monotonic stack)

Coverage loss per configuration per fault type =
    (# injected faults of that type that passed undetected) / 1000.

Output: results/ablation.csv  +  results/ablation.json

This harness measures *detection coverage* (a structural property of the gate
stack), which is host-independent. It does NOT reproduce the manuscript's
MIMIC-weighted ablation *latency* column (that needs credentialed data + a
specific host) -- see scripts/extract_mimic.py and results/gaps.json.

Usage:
    python scripts/ablation.py
"""

from __future__ import annotations

import csv
import json
import platform
import random
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RESULTS = ROOT / "results"
sys.path.insert(0, str(SRC))

from orasr import ORASRRouter, ReasoningPath, GateType, PathwayConfig  # noqa: E402
from orasr.constraints import RoutingConstraint  # noqa: E402
from orasr.constants import DEFAULT_RANDOM_SEED  # noqa: E402

SEED = DEFAULT_RANDOM_SEED  # 42
N_PER_GATE = 1000

FAULT_GATES = [
    ("G1_precondition", GateType.PRECONDITION),
    ("G2_risk", GateType.RISK_ASSESSMENT),
    ("G3_constraint", GateType.CONSTRAINT_VALIDATION),
    ("G4_postcondition", GateType.POSTCONDITION),
]


def _build_router(active_gates: List[GateType]) -> ORASRRouter:
    """A router whose every pathway evaluates exactly ``active_gates``.

    We reuse the committed engine and validators; we only override the pathway
    gate lists so that one router applies one fixed gate subset to all actions.
    This isolates the ablation from risk-based routing (every scenario gets the
    same gate set), which is exactly what a gate-removal ablation needs.
    """
    router = ORASRRouter(enable_fast_path=False, enable_audit=False)
    cfg = PathwayConfig(
        name="ABLATION",
        gates=list(active_gates),
        max_latency=1.0,
        requires_approval=False,
    )
    for path in (ReasoningPath.FAST, ReasoningPath.NORMAL, ReasoningPath.SAFE):
        router.pathways[path] = cfg
    return router


def _make_scenarios(rng: random.Random) -> Dict[str, List[Dict[str, Any]]]:
    """Build N_PER_GATE deterministic fault scenarios per fault type.

    Each scenario is a dict describing how to invoke the router so that exactly
    one gate's failure mode is tripped.
    """
    scenarios: Dict[str, List[Dict[str, Any]]] = {k: [] for k, _ in FAULT_GATES}

    for _ in range(N_PER_GATE):
        # G1: malformed input (non-dict). Only PRECONDITION rejects this; we keep
        # a valid action result so POSTCONDITION would NOT also fire.
        scenarios["G1_precondition"].append(
            {"input_data": None, "risk_score": rng.uniform(0.0, 0.6),
             "max_risk": 1.0, "result_valid": True, "violate_constraint": False}
        )
        # G2: risk above budget. max_risk < risk_score so RISK_ASSESSMENT rejects.
        r = rng.uniform(0.5, 1.0)
        scenarios["G2_risk"].append(
            {"input_data": {"payload": 1}, "risk_score": r,
             "max_risk": rng.uniform(0.0, r - 1e-6), "result_valid": True,
             "violate_constraint": False}
        )
        # G3: a registered constraint is violated. Only CONSTRAINT_VALIDATION fires.
        scenarios["G3_constraint"].append(
            {"input_data": {"payload": 1}, "risk_score": rng.uniform(0.0, 0.6),
             "max_risk": 1.0, "result_valid": True, "violate_constraint": True}
        )
        # G4: action returns invalid (None) result. Only POSTCONDITION fires.
        scenarios["G4_postcondition"].append(
            {"input_data": {"payload": 1}, "risk_score": rng.uniform(0.0, 0.6),
             "max_risk": 1.0, "result_valid": False, "violate_constraint": False}
        )
    return scenarios


def _route_one(router: ORASRRouter, sc: Dict[str, Any]) -> bool:
    """Route one fault scenario; return True if the fault passed UNDETECTED."""
    # Register / clear the failing constraint as the scenario requires.
    router.constraints = []
    if sc["violate_constraint"]:
        router.add_constraint(
            RoutingConstraint(
                name="injected_fail",
                validator=lambda ctx: False,  # always violated
                description="Injected constraint violation for ablation",
            )
        )

    def action(data: Any) -> Any:
        # Return a fixed VALID result for non-G4 faults so the POSTCONDITION gate
        # does not accidentally catch a G1 malformed-input scenario (whose echoed
        # result would otherwise be None). G4 faults return an invalid (None)
        # result on purpose so ONLY the postcondition gate can detect them.
        return {"ok": 1} if sc["result_valid"] else None

    result = router.route(
        action=action,
        input_data=sc["input_data"],
        risk_score=sc["risk_score"],
        max_risk=sc["max_risk"],
        human_approved=True,  # isolate gate behaviour from approval gating
    )
    # Undetected == engine deemed it safe despite the injected fault.
    return result.safe


def run() -> Dict[str, Any]:
    rng = random.Random(SEED)
    scenarios = _make_scenarios(rng)

    G1, G2, G3, G4 = (
        GateType.PRECONDITION, GateType.RISK_ASSESSMENT,
        GateType.CONSTRAINT_VALIDATION, GateType.POSTCONDITION,
    )

    configs: Dict[str, List[GateType]] = {
        "FULL_G1G2G3G4": [G1, G2, G3, G4],
        "minus_G1": [G2, G3, G4],
        "minus_G2": [G1, G3, G4],
        "minus_G3": [G1, G2, G4],
        "minus_G4": [G1, G2, G3],
        "progressive_G1": [G1],
        "progressive_G1G2": [G1, G2],
        "progressive_G1G2G3": [G1, G2, G3],
        "progressive_G1G2G3G4": [G1, G2, G3, G4],
        "NONE_no_gates": [],
    }

    rows: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}

    for cfg_name, gates in configs.items():
        router = _build_router(gates)
        cfg_summary: Dict[str, Any] = {"active_gates": [g.name for g in gates]}
        total_undetected = 0
        total_faults = 0
        for fault_name, _gtype in FAULT_GATES:
            undetected = sum(
                1 for sc in scenarios[fault_name] if _route_one(router, sc)
            )
            loss = undetected / N_PER_GATE
            cfg_summary[fault_name] = {
                "n": N_PER_GATE,
                "undetected": undetected,
                "coverage_loss": round(loss, 6),
            }
            total_undetected += undetected
            total_faults += N_PER_GATE
            rows.append(
                {
                    "config": cfg_name,
                    "active_gates": "+".join(g.name for g in gates) or "NONE",
                    "fault_type": fault_name,
                    "n": N_PER_GATE,
                    "undetected": undetected,
                    "coverage_loss": round(loss, 6),
                }
            )
        cfg_summary["overall_coverage_loss"] = round(total_undetected / total_faults, 6)
        cfg_summary["overall_detection"] = round(1.0 - total_undetected / total_faults, 6)
        results[cfg_name] = cfg_summary

    return {"seed": SEED, "n_per_gate": N_PER_GATE, "configurations": results, "rows": rows}


def environment_block() -> Dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "seed": SEED,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    res = run()

    (RESULTS / "ablation.json").write_text(
        json.dumps({"environment": environment_block(),
                    "seed": res["seed"], "n_per_gate": res["n_per_gate"],
                    "configurations": res["configurations"]}, indent=2),
        encoding="utf-8",
    )

    with (RESULTS / "ablation.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["config", "active_gates", "fault_type", "n", "undetected", "coverage_loss"]
        )
        for r in res["rows"]:
            writer.writerow(
                [r["config"], r["active_gates"], r["fault_type"], r["n"],
                 r["undetected"], r["coverage_loss"]]
            )

    print("Ablation (seed 42, synthetic, 1000 faults/gate). coverage_loss = undetected/1000")
    for cfg_name, summ in res["configurations"].items():
        line = "  %-22s overall_loss=%.3f | " % (cfg_name, summ["overall_coverage_loss"])
        line += " ".join(
            "%s=%.2f" % (fn.split('_')[0], summ[fn]["coverage_loss"])
            for fn, _ in FAULT_GATES
        )
        print(line)
    print("Artifacts:", RESULTS / "ablation.csv", "and ablation.json")


if __name__ == "__main__":
    main()

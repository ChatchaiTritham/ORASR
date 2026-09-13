"""Adversarial risk-score shift against true-Safe actions (seed 42, synthetic).

Threat model: an attacker (or a biased upstream scorer) subtracts delta from
the risk score of every true-Safe action (original rho >= 0.70) before it reaches
the router. We route each shifted action through the real ``ORASRRouter.route``
and report the fraction that lands in NORMAL or FAST.

Mitigation: the router's existing ``require_human_approval=True`` option forces
the SAFE pathway irrespective of rho. We model a protected action-type list
(assigned deterministically: every true-Safe action alternates between the
protected type "medication_order" and the unprotected type "consult_request")
and route protected types with require_human_approval=True.

Output: results/adversarial_shift.json
"""

from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import latency_benchmark as lb  # noqa: E402
from orasr import ORASRRouter  # noqa: E402

logging.disable(logging.CRITICAL)

SEED = lb.SEED
DELTAS = [round(0.05 * k, 2) for k in range(11)]
PROTECTED_TYPES = {"medication_order"}


def run() -> Dict:
    cohort = lb.build_cohort(random.Random(SEED))
    safe = [c["risk"] for c in cohort if c["risk"] >= ORASRRouter.SAFE_PATH_THRESHOLD]
    types = ["medication_order" if i % 2 == 0 else "consult_request" for i in range(len(safe))]
    router = ORASRRouter(enable_audit=False)
    rows = []
    for delta in DELTAS:
        no_mit = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
        prot = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
        unprot = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
        for rho, t in zip(safe, types):
            shifted = rho - delta
            r0 = router.route(action=lambda d: d, input_data={"a": 1}, risk_score=shifted,
                              human_approved=True)
            no_mit[r0.path.name] += 1
            is_prot = t in PROTECTED_TYPES
            r1 = router.route(action=lambda d: d, input_data={"a": 1}, risk_score=shifted,
                              require_human_approval=is_prot, human_approved=True)
            (prot if is_prot else unprot)[r1.path.name] += 1
        n_p, n_u = sum(prot.values()), sum(unprot.values())
        rows.append({
            "delta": delta,
            "no_mitigation": {"n": len(safe), "counts": no_mit,
                              "down_routed_pct": round(100 * (no_mit["FAST"] + no_mit["NORMAL"]) / len(safe), 3),
                              "to_fast_pct": round(100 * no_mit["FAST"] / len(safe), 3)},
            "mitigation_protected_types": {"n": n_p, "counts": prot,
                                           "down_routed_pct": round(100 * (prot["FAST"] + prot["NORMAL"]) / n_p, 3)},
            "mitigation_unprotected_types": {"n": n_u, "counts": unprot,
                                             "down_routed_pct": round(100 * (unprot["FAST"] + unprot["NORMAL"]) / n_u, 3)},
        })
    return {"seed": SEED, "n_true_safe": len(safe),
            "true_safe_definition": "original rho >= 0.70",
            "protected_types": sorted(PROTECTED_TYPES),
            "type_assignment": "alternating by cohort order (even index protected)",
            "mitigation": "route(..., require_human_approval=True) for protected types",
            "rows": rows}


def main() -> None:
    out = run()
    path = ROOT / "results" / "adversarial_shift.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for r in out["rows"]:
        print(f"delta={r['delta']:.2f} no-mitigation down {r['no_mitigation']['down_routed_pct']}% "
              f"(fast {r['no_mitigation']['to_fast_pct']}%) | protected "
              f"{r['mitigation_protected_types']['down_routed_pct']}% | unprotected "
              f"{r['mitigation_unprotected_types']['down_routed_pct']}%")
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()

"""Supplementary manuscript checks on the seed-42 synthetic cohort.

Reproduces the property checks (P1, P2, P4), per-band mean risk scores,
Clopper-Pearson bounds, threshold sensitivity, the example reasoning trace,
edge-case routing behaviour, and the risk-score noise (misrouting) analysis
reported in the manuscript. Writes results/manuscript_checks.json.

Usage:  python scripts/manuscript_checks.py
"""
import json
import math
import platform
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from scipy.stats import beta  # noqa: E402

import latency_benchmark as lb  # noqa: E402
from orasr import ORASRRouter, ReasoningPath  # noqa: E402
from orasr.gates import GateType  # noqa: E402


def clopper_pearson(x, n):
    lo = 0.0 if x == 0 else float(beta.ppf(0.025, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(0.975, x + 1, n - x))
    return [lo, hi]


def name(v):
    return "NaN" if isinstance(v, float) and math.isnan(v) else v


def main():
    out = {"seed": lb.SEED,
           "environment": {"python": platform.python_version(),
                           "platform": platform.platform(), "seed": lb.SEED}}
    cohort = lb.build_cohort(random.Random(lb.SEED))
    risks = [c["risk"] for c in cohort]

    # Clopper-Pearson 95% intervals for all-pass counts
    out["clopper_pearson"] = {str(n): clopper_pearson(n, n) for n in (10000, 9999, 4000, 1000)}

    # Mean risk score per stratum
    out["mean_risk_by_stratum"] = {
        s: round(sum(c["risk"] for c in cohort if c["stratum"] == s)
                 / sum(1 for c in cohort if c["stratum"] == s), 4)
        for s in ("FAST", "NORMAL", "SAFE")
    }

    # P1 routing agreement, P4 trace length, pathway counts
    r = ORASRRouter()
    p1 = p4 = 0
    counts = {}
    for s in cohort:
        res = r.route(action=lambda d: d, input_data={"x": 1},
                      risk_score=s["risk"], human_approved=True)
        counts[res.path.name] = counts.get(res.path.name, 0) + 1
        p1 += res.path.name != s["stratum"]
        pre = [g for g in r.pathways[res.path].gates if g != GateType.POSTCONDITION]
        p4 += len(res.reasoning_trace.steps) != 1 + len(pre)
    gates = {p: set(r.pathways[p].gates) for p in r.pathways}
    sizes = [len(r.pathways[r._select_pathway(x, False)].gates) for x in sorted(risks)]
    out["properties"] = {
        "P1_pathway_mismatches": p1,
        "pathway_counts": counts,
        "P2_gate_inclusion": gates[ReasoningPath.FAST] <= gates[ReasoningPath.NORMAL] <= gates[ReasoningPath.SAFE],
        "P2_adjacent_monotonic_violations": sum(1 for a, b in zip(sizes, sizes[1:]) if b < a),
        "P2_pairs_checked": len(sizes) - 1,
        "P4_trace_length_violations": p4,
        "history_entries": len(r.routing_history),
    }

    # Threshold sensitivity: pathway shares (%) and expected gate work per call
    thr = []
    for t1, t2 in [(0.3, 0.7), (0.2, 0.5), (0.4, 0.8), (0.33, 0.67)]:
        f = sum(x < t1 for x in risks)
        s = sum(x >= t2 for x in risks)
        n = len(risks) - f - s
        thr.append({"theta1": t1, "theta2": t2, "fast_pct": 100 * f / len(risks),
                    "normal_pct": 100 * n / len(risks), "safe_pct": 100 * s / len(risks),
                    "gate_work_per_call": (f + 3 * n + 4 * s) / len(risks)})
    out["threshold_sensitivity"] = thr

    # Example reasoning trace (Safe pathway, approval supplied); timestamps vary per run
    res = ORASRRouter().route(action=lambda d: {"status": "sent"}, input_data={"action": "consult"},
                              risk_score=0.82, human_approved=True)
    out["example_trace"] = {"path": res.path.name, "safe": res.safe,
                            "gates_passed": res.gates_passed, "violations": res.violations,
                            "trace": res.reasoning_trace.to_dict()}

    # Edge-case routing behaviour
    edges = []
    for rho in (-0.2, float("nan"), 1.3):
        e = ORASRRouter().route(action=lambda d: d, input_data={"a": 1}, risk_score=rho, human_approved=True)
        edges.append({"risk_score": name(rho), "path": e.path.name, "safe": e.safe, "violations": e.violations})
    e = ORASRRouter(enable_fast_path=False).route(action=lambda d: d, input_data={"a": 1}, risk_score=0.1)
    edges.append({"case": "enable_fast_path=False, risk 0.1", "path": e.path.name})
    out["edge_cases"] = edges

    # Misrouting: Gaussian noise on risk scores of the Safe stratum
    safe = [c["risk"] for c in cohort if c["stratum"] == "SAFE"]
    router = ORASRRouter()
    noise = []
    for sigma in (0.05, 0.1, 0.2):
        nrng = random.Random(lb.SEED)
        c = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
        for rho in safe:
            c[router._select_pathway(rho + nrng.gauss(0.0, sigma), False).name] += 1
        noise.append({"sigma": sigma, "n_safe": len(safe), "counts": c,
                      "down_routed_pct": round(100 * (c["FAST"] + c["NORMAL"]) / len(safe), 2),
                      "to_fast_pct": round(100 * c["FAST"] / len(safe), 2)})
    out["misrouting_noise"] = noise

    path = REPO / "results" / "manuscript_checks.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "example_trace"}, indent=2, default=str))
    print(f"wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()

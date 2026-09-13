"""Parametric cost model for ORASR vs flat monitors.

THIS IS A PARAMETRIC MODEL, NOT A MEASUREMENT. It combines the pathway counts
the committed router produces on the seed-42 cohort with ASSUMED per-gate costs
and approval dwell times, to show how the gate-work reduction translates into
expected cost under different cost regimes.

Monitors
--------
ORASR          FAST {G1}, NORMAL {G1,G2,G3}, SAFE {G1,G2,G3,G4}; approval on SAFE
Flat-3         every action {G1,G2,G3}; no approval
Flat-4         every action {G1,G2,G3,G4}; no approval
Flat-4+approval every action {G1,G2,G3,G4}; approval on every action

Parameters
----------
c  per-gate cost (ms) in {0.01, 0.1, 1, 10, 100}
   cost profiles: "uniform"   G1=G2=G3=G4=c
                  "g2g3_10x"  G1=G4=c, G2=G3=10c (model / service calls)
A  approval dwell (s) per approved action in {0, 30, 300}

Outputs per (profile, c, A, monitor): expected automated gate cost per action
(ms), approvals per 1000 actions, expected approval dwell per action (s), and
expected total per action (s) = automated/1000 + dwell.

Output: results/cost_model.json
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import latency_benchmark as lb  # noqa: E402
from orasr import ORASRRouter, GateType  # noqa: E402

SEED = lb.SEED
GATE_COSTS_MS = [0.01, 0.1, 1.0, 10.0, 100.0]
DWELL_S = [0.0, 30.0, 300.0]
PROFILES = {
    "uniform": {"G1": 1.0, "G2": 1.0, "G3": 1.0, "G4": 1.0},
    "g2g3_10x": {"G1": 1.0, "G2": 10.0, "G3": 10.0, "G4": 1.0},
}
GNAME = {GateType.PRECONDITION: "G1", GateType.RISK_ASSESSMENT: "G2",
         GateType.CONSTRAINT_VALIDATION: "G3", GateType.POSTCONDITION: "G4"}


def run() -> Dict:
    cohort = lb.build_cohort(random.Random(SEED))
    router = ORASRRouter(enable_audit=False)
    counts = {"FAST": 0, "NORMAL": 0, "SAFE": 0}
    for c in cohort:
        counts[router._select_pathway(c["risk"], False).name] += 1
    n = len(cohort)
    share = {p: counts[p] / n for p in counts}
    gates = {p.name: [GNAME[g] for g in cfg.gates] for p, cfg in router.pathways.items()}
    approval = {p.name: cfg.requires_approval for p, cfg in router.pathways.items()}

    monitors = {
        "ORASR": {"gate_mix": {p: (share[p], gates[p]) for p in share},
                  "approval_share": sum(share[p] for p in share if approval[p])},
        "Flat-3": {"gate_mix": {"ALL": (1.0, gates["NORMAL"])}, "approval_share": 0.0},
        "Flat-4": {"gate_mix": {"ALL": (1.0, gates["SAFE"])}, "approval_share": 0.0},
        "Flat-4+approval": {"gate_mix": {"ALL": (1.0, gates["SAFE"])}, "approval_share": 1.0},
    }

    rows = []
    for prof_name, weights in PROFILES.items():
        for c in GATE_COSTS_MS:
            for a in DWELL_S:
                for m, spec in monitors.items():
                    auto = sum(s * sum(weights[g] * c for g in gl)
                               for s, gl in spec["gate_mix"].values())
                    dwell = spec["approval_share"] * a
                    rows.append({
                        "profile": prof_name, "gate_cost_ms": c, "approval_dwell_s": a,
                        "monitor": m,
                        "automated_ms_per_action": round(auto, 6),
                        "approvals_per_1000": round(1000 * spec["approval_share"], 3),
                        "approval_dwell_s_per_action": round(dwell, 6),
                        "total_s_per_action": round(auto / 1000.0 + dwell, 6),
                    })

    def pick(profile, c, a, m):
        return next(r for r in rows if r["profile"] == profile and r["gate_cost_ms"] == c
                    and r["approval_dwell_s"] == a and r["monitor"] == m)

    ratios = {prof: round(pick(prof, 1.0, 0.0, "ORASR")["automated_ms_per_action"]
                          / pick(prof, 1.0, 0.0, "Flat-4")["automated_ms_per_action"], 4)
              for prof in PROFILES}
    return {
        "note": "parametric model, not a measurement",
        "seed": SEED,
        "pathway_counts": counts,
        "pathway_gates": gates,
        "pathway_requires_approval": approval,
        "monitor_definitions": {
            "ORASR": "risk-routed pathways; approval on SAFE only",
            "Flat-3": "G1,G2,G3 on every action; no approval",
            "Flat-4": "G1,G2,G3,G4 on every action; no approval",
            "Flat-4+approval": "G1,G2,G3,G4 on every action; approval on every action",
        },
        "cost_profiles": PROFILES,
        "gate_costs_ms": GATE_COSTS_MS,
        "approval_dwell_s": DWELL_S,
        "orasr_to_flat4_automated_cost_ratio": ratios,
        "rows": rows,
    }


def main() -> None:
    out = run()
    path = ROOT / "results" / "cost_model.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("counts", out["pathway_counts"], "ORASR/Flat-4 automated cost ratio",
          out["orasr_to_flat4_automated_cost_ratio"])
    for r in out["rows"]:
        if r["gate_cost_ms"] == 10.0 and r["approval_dwell_s"] == 30.0:
            print(r)
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()

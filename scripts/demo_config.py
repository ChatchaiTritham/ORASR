"""Non-default *demonstration configuration* of the ORASR router.

Why this exists
---------------
With the shipped defaults the NORMAL pathway has no more detection power than
FAST on realistic inputs:

* G2 (RISK_ASSESSMENT) compares ``risk_score <= max_risk`` where ``max_risk``
  defaults to 1.0, so for any rho in [0, 1] it can never fail unless a caller
  passes an explicit per-call budget;
* G3 (CONSTRAINT_VALIDATION) iterates ``router.constraints``, which is empty by
  default, so it always passes.

This module builds a router in which G2 and G3 carry real policy, so the
difference between the pathways is observable. It is a demonstration, NOT the
default and NOT a clinically validated policy. Nothing in ``src/orasr`` changes;
the engine, gate stack and routing thresholds are the committed ones.

Policy
------
(i) G2 per-call ceiling by action class. Each call declares an ``action_class``
    and G2 fails when rho exceeds that class's ceiling:

        lookup      0.20   read-only retrieval
        routine     0.50   routine order / documentation
        escalation  0.90   escalation / consult
        critical    1.00   explicitly critical action

    An unknown or missing class fails closed (ceiling 0.0). If a caller also
    passes ``max_risk`` the stricter of the two ceilings applies. Ceilings are
    round numbers chosen for illustration only.

(ii) G3 constraints built from the SHIPPED factories in ``orasr.constraints``:

    * ``time_limit_constraint(MAX_ELAPSED_S)`` -- the caller-reported
      ``elapsed_time`` (e.g. time the request has already waited upstream)
      must not exceed 2.0 s;
    * ``risk_threshold_constraint(1.0)`` -- rejects out-of-range risk scores
      (rho > 1 or NaN);
    * ``approval_required_constraint()`` -- scoped to the ``escalation`` and
      ``critical`` classes (for other classes it is vacuously satisfied), so
      those classes need ``human_approved=True`` even when routed NORMAL.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from orasr import ORASRRouter, GateType, SafetyGate  # noqa: E402
from orasr.constraints import (  # noqa: E402
    RoutingConstraint,
    approval_required_constraint,
    risk_threshold_constraint,
    time_limit_constraint,
)

CLASS_CEILINGS: Dict[str, float] = {
    "lookup": 0.20,
    "routine": 0.50,
    "escalation": 0.90,
    "critical": 1.00,
}
APPROVAL_CLASSES = ("escalation", "critical")
MAX_ELAPSED_S = 2.0


def ceiling_for(action_class: Any) -> float:
    """Class ceiling; unknown classes fail closed."""
    return CLASS_CEILINGS.get(action_class, 0.0)


def lowest_admissible_class(rho: float) -> str:
    """Smallest-ceiling class whose ceiling admits rho (used for clean calls)."""
    for cls, ceil in sorted(CLASS_CEILINGS.items(), key=lambda kv: kv[1]):
        if rho <= ceil:
            return cls
    return "critical"


def _class_ceiling_validator(context: Dict[str, Any]) -> bool:
    rho = context.get("risk_score", 0)
    ceiling = ceiling_for(context.get("action_class"))
    if "max_risk" in context:
        ceiling = min(ceiling, context["max_risk"])
    if isinstance(rho, float) and math.isnan(rho):
        return False
    return rho <= ceiling


def _scoped_approval() -> RoutingConstraint:
    base = approval_required_constraint()
    return RoutingConstraint(
        name=f"{base.name}[{'|'.join(APPROVAL_CLASSES)}]",
        validator=lambda ctx: ctx.get("action_class") not in APPROVAL_CLASSES
        or base.validator(ctx),
        description=f"{base.description} for classes {APPROVAL_CLASSES}",
    )


def build_demo_router(**router_kwargs: Any) -> ORASRRouter:
    """ORASRRouter with the demonstration G2 ceiling policy and G3 constraints."""
    router = ORASRRouter(**router_kwargs)
    router.gates[GateType.RISK_ASSESSMENT] = SafetyGate(
        gate_type=GateType.RISK_ASSESSMENT,
        validator=_class_ceiling_validator,
        name="G2_RiskAssessment",
        description="Risk must not exceed the action-class ceiling (demo policy)",
    )
    router.add_constraint(time_limit_constraint(MAX_ELAPSED_S))
    router.add_constraint(risk_threshold_constraint(1.0))
    router.add_constraint(_scoped_approval())
    return router


def build_default_router(**router_kwargs: Any) -> ORASRRouter:
    """The shipped default router (for side-by-side comparison)."""
    return ORASRRouter(**router_kwargs)

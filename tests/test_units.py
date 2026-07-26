"""
Focused unit tests for ORASR pure/deterministic logic.

Targets real modules under src/orasr: router pathway selection, constraint
factories, safety gate check logic, and constants. All inputs are tiny and
hand-made; no network, datasets, or training.
"""

import os
import sys

# Make the `src` layout importable (repo_root/src/orasr).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import pytest

from orasr.router import ORASRRouter
from orasr.pathways import ReasoningPath, PathwayConfig
from orasr.gates import SafetyGate, GateType, GateResult
from orasr.constraints import (
    RoutingConstraint,
    ConstraintViolation,
    time_limit_constraint,
    risk_threshold_constraint,
    approval_required_constraint,
)
from orasr import constants


# --------------------------------------------------------------------------
# Router pathway-selection logic (deterministic thresholds)
# --------------------------------------------------------------------------

def test_pathway_selection_threshold_boundaries():
    router = ORASRRouter(enable_fast_path=True)
    # FAST below FAST_PATH_THRESHOLD (0.3)
    assert router._select_pathway(0.0, False) is ReasoningPath.FAST
    assert router._select_pathway(0.29, False) is ReasoningPath.FAST
    # At/above 0.3 but below SAFE_PATH_THRESHOLD (0.7) -> NORMAL
    assert router._select_pathway(0.3, False) is ReasoningPath.NORMAL
    assert router._select_pathway(0.69, False) is ReasoningPath.NORMAL
    # At/above 0.7 -> SAFE
    assert router._select_pathway(0.7, False) is ReasoningPath.SAFE
    assert router._select_pathway(1.0, False) is ReasoningPath.SAFE


def test_pathway_selection_approval_forces_safe():
    router = ORASRRouter(enable_fast_path=True)
    # require_approval overrides even a zero risk score
    assert router._select_pathway(0.0, True) is ReasoningPath.SAFE


def test_fast_path_disabled_falls_back_to_normal():
    router = ORASRRouter(enable_fast_path=False)
    # Low risk would be FAST, but fast path disabled -> NORMAL
    assert router._select_pathway(0.1, False) is ReasoningPath.NORMAL


# --------------------------------------------------------------------------
# End-to-end route() on a trivial deterministic action
# --------------------------------------------------------------------------

def test_route_low_risk_executes_action_safely():
    router = ORASRRouter(enable_fast_path=True, enable_audit=True)
    result = router.route(
        action=lambda d: {"out": d["x"] * 2},
        input_data={"x": 21},
        risk_score=0.05,
    )
    assert result.path is ReasoningPath.FAST
    assert result.safe is True
    assert result.action_result == {"out": 42}
    assert result.violations == []
    assert "G1_Precondition" in result.gates_passed
    # audit history recorded exactly one routing
    assert len(router.routing_history) == 1


def test_route_high_risk_without_approval_is_unsafe():
    router = ORASRRouter()
    result = router.route(
        action=lambda d: {"ok": True},
        input_data={"x": 1},
        risk_score=0.9,  # -> SAFE pathway, requires_approval=True
    )
    assert result.path is ReasoningPath.SAFE
    assert result.safe is False
    assert any("approval" in v.lower() for v in result.violations)
    # action must NOT have executed because gate/approval failed
    assert result.action_result is None


def test_route_precondition_fails_on_bad_input():
    router = ORASRRouter(enable_fast_path=True)
    result = router.route(
        action=lambda d: "ran",
        input_data=None,  # precondition validator rejects None
        risk_score=0.0,
    )
    assert result.safe is False
    assert result.action_result is None
    assert any("G1_Precondition" in v for v in result.violations)


# --------------------------------------------------------------------------
# Constraint factories (pure validators)
# --------------------------------------------------------------------------

def test_time_limit_constraint():
    c = time_limit_constraint(max_time=5.0)
    assert isinstance(c, RoutingConstraint)
    assert c.validate({"elapsed_time": 3.0}) is True
    assert c.validate({"elapsed_time": 5.0}) is True  # boundary inclusive
    assert c.validate({"elapsed_time": 5.1}) is False
    assert c.validate({}) is True  # default elapsed 0 <= 5


def test_risk_threshold_constraint_enforce_raises():
    c = risk_threshold_constraint(max_risk=0.5)
    assert c.validate({"risk_score": 0.4}) is True
    assert c.validate({"risk_score": 0.6}) is False
    with pytest.raises(ConstraintViolation):
        c.enforce({"risk_score": 0.99})
    # within-limit enforce does not raise
    c.enforce({"risk_score": 0.1})


def test_approval_required_constraint():
    c = approval_required_constraint()
    assert c.validate({"human_approved": True}) is True
    assert c.validate({"human_approved": False}) is False
    assert c.validate({}) is False  # missing -> default False


# --------------------------------------------------------------------------
# SafetyGate.check returns structured GateResult; swallows validator errors
# --------------------------------------------------------------------------

def test_safety_gate_pass_and_fail():
    gate = SafetyGate(
        gate_type=GateType.PRECONDITION,
        validator=lambda ctx: ctx.get("ok", False),
        name="G_test",
    )
    passed = gate.check({"ok": True})
    assert isinstance(passed, GateResult)
    assert passed.passed is True and passed.confidence == 1.0

    failed = gate.check({"ok": False})
    assert failed.passed is False and failed.confidence == 0.0


def test_safety_gate_validator_exception_is_caught():
    def boom(ctx):
        raise ValueError("kaboom")

    gate = SafetyGate(GateType.RISK_ASSESSMENT, boom, name="G_err")
    res = gate.check({})
    assert res.passed is False
    assert "error" in res.metadata
    assert "kaboom" in res.message


# --------------------------------------------------------------------------
# Constants / config sanity (seed-42 contract)
# --------------------------------------------------------------------------

def test_constants_seed_and_config():
    assert constants.DEFAULT_RANDOM_SEED == 42
    assert 0.0 < constants.DEFAULT_EPSILON < 1e-6
    assert constants.DEFAULT_CONFIDENCE_LEVEL == 0.95
    assert constants.PACKAGE_NAME == "orasr"
    assert isinstance(constants.DEFAULT_FIGURE_SIZE, tuple)
    assert len(constants.DEFAULT_FIGURE_SIZE) == 2


def test_pathway_config_default_description():
    cfg = PathwayConfig(name="X", gates=[GateType.PRECONDITION], max_latency=0.1,
                        requires_approval=False)
    # __post_init__ fills a description mentioning gate count
    assert "1 gates" in cfg.description

"""
ORASR: Operational Reasoning-Action Safety Routing
===================================================

Safety routing framework for clinical decision-making.
"""

from .constants import FRAMEWORK_NAME, PACKAGE_VERSION

__version__ = PACKAGE_VERSION
__author__ = "Chatchai Tritham"

from .router import ORASRRouter, RoutingResult
from .pathways import ReasoningPath, PathwayConfig
from .gates import SafetyGate, GateResult, GateType
from .reasoning import ReasoningTrace, ReasoningStep
from .constraints import RoutingConstraint, ConstraintViolation

__all__ = [
    "ORASRRouter",
    "RoutingResult",
    "ReasoningPath",
    "PathwayConfig",
    "SafetyGate",
    "GateResult",
    "GateType",
    "ReasoningTrace",
    "ReasoningStep",
    "RoutingConstraint",
    "ConstraintViolation",
    "FRAMEWORK_NAME",
]

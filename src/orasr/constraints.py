"""
Routing Constraints
===================

Constraints for safe routing decisions.
"""

from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConstraintViolation(Exception):
    """Exception for constraint violations"""

    constraint_name: str
    message: str
    metadata: Dict[str, Any]


@dataclass
class RoutingConstraint:
    """
    Constraint for routing decisions.
    """

    name: str
    validator: Callable[[Dict[str, Any]], bool]
    description: str
    severity: str = "error"  # error, warning, info
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Validate constraint against context.

        Args:
            context: Context to validate

        Returns:
            True if constraint satisfied
        """
        try:
            satisfied = self.validator(context)

            if not satisfied:
                logger.warning(f"Constraint violated: {self.name} - {self.description}")

            return satisfied

        except Exception as e:
            logger.error(f"Constraint validation error: {e}")
            return False

    def enforce(self, context: Dict[str, Any]):
        """Enforce constraint, raise exception if violated"""
        if not self.validate(context):
            raise ConstraintViolation(
                constraint_name=self.name,
                message=self.description,
                metadata={**self.metadata, **context},
            )


# Predefined constraint factories


def time_limit_constraint(max_time: float) -> RoutingConstraint:
    """Create time limit constraint"""

    def validator(ctx: Dict) -> bool:
        elapsed = ctx.get("elapsed_time", 0)
        return elapsed <= max_time

    return RoutingConstraint(
        name="time_limit",
        validator=validator,
        description=f"Execution time must be ≤ {max_time}s",
        metadata={"max_time": max_time},
    )


def risk_threshold_constraint(max_risk: float) -> RoutingConstraint:
    """Create risk threshold constraint"""

    def validator(ctx: Dict) -> bool:
        risk = ctx.get("risk_score", 0)
        return risk <= max_risk

    return RoutingConstraint(
        name="risk_threshold",
        validator=validator,
        description=f"Risk score must be ≤ {max_risk}",
        metadata={"max_risk": max_risk},
    )


def approval_required_constraint() -> RoutingConstraint:
    """Create approval requirement constraint"""

    def validator(ctx: Dict) -> bool:
        return ctx.get("human_approved", False)

    return RoutingConstraint(
        name="approval_required", validator=validator, description="Human approval is required"
    )

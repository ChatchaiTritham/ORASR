"""
Safety Gates
============

Safety validation gates for routing decisions.
"""

from enum import Enum
from typing import Callable, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class GateType(Enum):
    """Types of safety gates"""

    PRECONDITION = "precondition"
    RISK_ASSESSMENT = "risk_assessment"
    CONSTRAINT_VALIDATION = "constraint_validation"
    POSTCONDITION = "postcondition"


@dataclass
class GateResult:
    """Result of gate check"""

    passed: bool
    confidence: float
    message: str
    metadata: Dict[str, Any]


class SafetyGate:
    """
    Safety gate for validation.

    Each gate represents a safety check that must pass before
    action execution.
    """

    def __init__(
        self,
        gate_type: GateType,
        validator: Callable[[Dict[str, Any]], bool],
        name: str,
        description: str = "",
    ):
        """
        Initialize safety gate.

        Args:
            gate_type: Type of gate
            validator: Validation function
            name: Gate name
            description: Gate description
        """
        self.gate_type = gate_type
        self.validator = validator
        self.name = name
        self.description = description or f"{gate_type.value} gate"

    def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check gate condition.

        Args:
            context: Context for validation

        Returns:
            GateResult with pass/fail and details
        """
        try:
            passed = self.validator(context)

            result = GateResult(
                passed=passed,
                confidence=1.0 if passed else 0.0,
                message="Gate passed" if passed else "Gate failed",
                metadata={"gate_type": self.gate_type.value, "gate_name": self.name},
            )

            logger.debug(f"Gate {self.name}: {'PASS' if passed else 'FAIL'}")

            return result

        except Exception as e:
            logger.error(f"Gate {self.name} error: {e}")

            return GateResult(
                passed=False,
                confidence=0.0,
                message=f"Gate error: {e}",
                metadata={
                    "gate_type": self.gate_type.value,
                    "gate_name": self.name,
                    "error": str(e),
                },
            )

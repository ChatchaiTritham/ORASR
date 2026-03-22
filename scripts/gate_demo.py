"""ORASR gate demo script."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orasr import GateType, ORASRRouter


def main() -> None:
    """Demonstrate individual ORASR safety gates."""
    print("=" * 60)
    print("ORASR Safety Gates Demo".center(60))
    print("=" * 60)

    router = ORASRRouter()
    gates_to_demo = [
        GateType.PRECONDITION,
        GateType.RISK_ASSESSMENT,
        GateType.CONSTRAINT_VALIDATION,
        GateType.POSTCONDITION,
    ]

    invalid_context_by_gate: Dict[GateType, Dict[str, Any]] = {
        GateType.PRECONDITION: {},
        GateType.RISK_ASSESSMENT: {"risk_score": 1.5, "max_risk": 1.0},
        GateType.CONSTRAINT_VALIDATION: {"constraints": []},
        GateType.POSTCONDITION: {"action_result": None},
    }

    for gate_type in gates_to_demo:
        gate = router.gates[gate_type]
        print("\n" + "-" * 60)
        print(f"Gate: {gate.name}")
        print(f"Type: {gate_type.value}")
        print(f"Description: {gate.description}")
        print("-" * 60)

        valid_context = {
            "input_data": {"value": 42, "patient_id": "PT-001"},
            "risk_score": 0.5,
            "max_risk": 1.0,
            "action_result": {"status": "success"},
        }
        valid_result = gate.check(valid_context)
        print("\nTest 1: Valid Context")
        print(f" Passed: {valid_result.passed}")
        print(f" Confidence: {valid_result.confidence:.3f}")
        print(f" Message: {valid_result.message}")

        invalid_result = gate.check(invalid_context_by_gate.get(gate_type, {}))
        print("\nTest 2: Invalid Context")
        print(f" Passed: {invalid_result.passed}")
        print(f" Confidence: {invalid_result.confidence:.3f}")
        print(f" Message: {invalid_result.message}")

    print("\n" + "=" * 60)
    print("Summary".center(60))
    print("=" * 60)
    print(" G1 (Precondition): validates input prerequisites")
    print(" G2 (Risk Assessment): confirms risk within bounds")
    print(" G3 (Constraint Validation): enforces operational limits")
    print(" G4 (Postcondition): verifies action results")


if __name__ == "__main__":
    main()

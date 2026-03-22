"""ORASR demo script."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orasr import ORASRRouter


def print_header(text: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60)


def print_section(text: str) -> None:
    """Print a formatted subsection header."""
    print("\n" + "-" * 60)
    print(text)
    print("-" * 60)


def simple_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """Low-risk sample action."""
    return {"status": "success", "value": data.get("value", 0) * 2}


def update_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """Medium-risk sample action."""
    time.sleep(0.01)
    return {"status": "updated", "id": data.get("id"), "changes": data.get("changes", {})}


def critical_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """High-risk sample action."""
    time.sleep(0.02)
    return {
        "status": "critical_action_completed",
        "patient_id": data.get("patient_id"),
        "priority": "immediate",
    }


def main() -> None:
    """Run the ORASR routing demo."""
    print_header("ORASR SAFETY ROUTING DEMO")
    print_section("1. Initializing ORASR Router")

    router = ORASRRouter(enable_fast_path=True, enable_audit=True)
    print("[OK] Router initialized")
    print(f" Fast path enabled: {router.enable_fast_path}")
    print(f" Audit enabled: {router.enable_audit}")
    print("\nConfigured pathways:")
    for pathway, config in router.pathways.items():
        print(
            f" - {pathway.name:6s}: {len(config.gates)} gates, max latency: {config.max_latency*1000:.0f}ms"
        )

    print_section("2. Fast Path Demo (Low Risk)")
    fast_result = router.route(action=simple_action, input_data={"value": 42}, risk_score=0.15)
    print(f" Pathway: {fast_result.path.name}")
    print(f" Safe: {fast_result.safe}")
    print(f" Latency: {fast_result.latency*1000:.2f}ms")
    print(f" Gates Passed: {fast_result.gates_passed}")
    print(f" Action Result: {fast_result.action_result}")

    print_section("3. Normal Path Demo (Medium Risk)")
    normal_result = router.route(
        action=update_action,
        input_data={"id": 123, "changes": {"field": "new_value"}},
        risk_score=0.55,
    )
    print(f" Pathway: {normal_result.path.name}")
    print(f" Safe: {normal_result.safe}")
    print(f" Latency: {normal_result.latency*1000:.2f}ms")
    print(f" Gates Passed: {normal_result.gates_passed}")

    print_section("4. Safe Path Demo (High Risk)")
    safe_result = router.route(
        action=critical_action,
        input_data={"patient_id": "PT-001"},
        risk_score=0.88,
        require_human_approval=True,
        human_approved=True,
    )
    print(f" Pathway: {safe_result.path.name}")
    print(f" Safe: {safe_result.safe}")
    print(f" Human Approved: {safe_result.human_approved}")
    print(f" Violations: {safe_result.violations}")

    print_section("5. Risk Level Comparison")
    test_risk_levels = [
        (0.10, "Very low risk"),
        (0.35, "Low-medium risk"),
        (0.55, "Medium risk"),
        (0.75, "High risk"),
        (0.95, "Critical risk"),
    ]
    for risk_score, description in test_risk_levels:
        result = router.route(
            action=lambda payload: {"result": "ok"}, input_data={}, risk_score=risk_score
        )
        print(
            f" {risk_score:4.2f} | {description:16s} | {result.path.name:6s} | safe={result.safe}"
        )

    print_section("6. Router Statistics")
    statistics = router.get_statistics()
    for key, value in statistics.items():
        print(f" {key}: {value}")


if __name__ == "__main__":
    main()

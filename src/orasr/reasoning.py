"""
Reasoning Trace
===============

Transparent reasoning trace for routing decisions.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class ReasoningStep:
    """Single step in reasoning process"""

    timestamp: float
    description: str
    gate: str
    result: str
    confidence: float
    metadata: Dict[str, Any]


class ReasoningTrace:
    """
    Reasoning trace for transparency.

    Records all steps in the routing and decision process.
    """

    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.start_time = time.time()

    def add_step(self, step: ReasoningStep):
        """Add reasoning step"""
        self.steps.append(step)

    def get_steps(self) -> List[ReasoningStep]:
        """Get all reasoning steps"""
        return self.steps.copy()

    def get_elapsed_time(self) -> float:
        """Get elapsed time since trace start"""
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "start_time": self.start_time,
            "elapsed_time": self.get_elapsed_time(),
            "steps": [
                {
                    "timestamp": s.timestamp,
                    "description": s.description,
                    "gate": s.gate,
                    "result": s.result,
                    "confidence": s.confidence,
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
        }

    def __str__(self) -> str:
        """String representation"""
        lines = ["Reasoning Trace:"]
        for i, step in enumerate(self.steps, 1):
            lines.append(
                f"{i}. [{step.gate}] {step.description} → {step.result} "
                f"(confidence: {step.confidence:.2f})"
            )
        return "\n".join(lines)

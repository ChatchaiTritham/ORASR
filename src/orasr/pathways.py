"""
Reasoning Pathways
==================

Different pathways for action routing based on risk.
"""

from enum import Enum
from typing import List
from dataclasses import dataclass

from .gates import GateType


class ReasoningPath(Enum):
    """Available reasoning pathways"""

    FAST = "fast"  # Low risk, minimal gates
    NORMAL = "normal"  # Medium risk, standard gates
    SAFE = "safe"  # High risk, all gates + review


@dataclass
class PathwayConfig:
    """Configuration for a reasoning pathway"""

    name: str
    gates: List[GateType]
    max_latency: float  # Maximum allowed latency (seconds)
    requires_approval: bool  # Requires human approval
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"{self.name} pathway with {len(self.gates)} gates"

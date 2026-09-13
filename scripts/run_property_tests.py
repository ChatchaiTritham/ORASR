"""Run tests/test_properties.py and summarise it in results/property_tests.json.

Usage:  python scripts/run_property_tests.py
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import hypothesis
import pytest

ROOT = Path(__file__).resolve().parents[1]


class _Collector:
    def __init__(self):
        self.outcomes = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.outcome != "passed":
            self.outcomes[report.nodeid.split("::")[-1]] = report.outcome


def main() -> int:
    col = _Collector()
    code = pytest.main(["-q", "-p", "no:cacheprovider", str(ROOT / "tests" / "test_properties.py")],
                       plugins=[col])
    mod = sys.modules["test_properties"]
    counts = dict(mod.COUNTS)
    failures = sum(1 for o in col.outcomes.values() if o != "passed")
    out = {
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "hypothesis": hypothesis.__version__, "pytest": pytest.__version__},
        "settings": {"max_examples": mod.MAX_EXAMPLES, "derandomize": True, "database": None},
        "boundary_values": mod.BOUNDARY,
        "examples_run": {k: v for k, v in counts.items() if isinstance(v, int) and not isinstance(v, bool)},
        "tests": col.outcomes,
        "failures": failures,
        "mutation_detected": counts["mutation_detected"],
        "mutation_counterexample": counts["mutation_counterexample"],
        "pytest_exit_code": int(code),
    }
    path = ROOT / "results" / "property_tests.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())

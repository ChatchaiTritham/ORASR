"""Tests for the reproducibility driver (scripts/run_all.py)."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("run_all", ROOT / "scripts" / "run_all.py")
run_all = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_all)


class TestStructuralVerification(unittest.TestCase):
    def setUp(self):
        self.structure = run_all.verify_structure()

    def test_thresholds(self):
        self.assertEqual(self.structure["thresholds"]["fast_path_threshold"], 0.3)
        self.assertEqual(self.structure["thresholds"]["safe_path_threshold"], 0.7)

    def test_monotonic_gate_inclusion(self):
        self.assertEqual(self.structure["gate_counts"], {"FAST": 1, "NORMAL": 3, "SAFE": 4})
        self.assertTrue(self.structure["monotonic_gate_count"])
        self.assertTrue(self.structure["monotonic_gate_inclusion_chain"])

    def test_partition_and_non_bypass(self):
        self.assertTrue(self.structure["partition_correct"])
        self.assertTrue(self.structure["non_bypass_holds"])
        self.assertTrue(self.structure["all_structural_checks_pass"])


class TestSyntheticCohort(unittest.TestCase):
    def test_distribution_is_deterministic(self):
        first = run_all.run_cohort()
        second = run_all.run_cohort()
        self.assertEqual(first["total_scenarios"], 10000)
        self.assertEqual(
            first["pathway_distribution"], {"FAST": 3500, "NORMAL": 4500, "SAFE": 2000}
        )
        # Structural outcomes are seed-stable across runs (latency is not asserted).
        self.assertEqual(first["pathway_distribution"], second["pathway_distribution"])
        self.assertEqual(first["gate_pass_rate_pct"], second["gate_pass_rate_pct"])

    def test_clean_cohort_passes_all_gates(self):
        # Honest expectation: well-formed inputs pass every committed validator.
        result = run_all.run_cohort()
        self.assertEqual(result["gate_pass_rate_pct"], 100.0)
        self.assertEqual(result["blocked"], 0)


if __name__ == "__main__":
    unittest.main()

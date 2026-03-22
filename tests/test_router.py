import unittest
from typing import Dict, Any
from orasr.router import ORASRRouter, RoutingResult
from orasr.pathways import ReasoningPath

class TestORASRRouter(unittest.TestCase):
    """Test suite for the ORASR Router."""

    def setUp(self):
        """Set up a standard router instance."""
        self.router = ORASRRouter(enable_fast_path=True, enable_audit=True)

    def test_risk_threshold_fast_path(self):
        """Test routing through the FAST path for low-risk actions."""
        def dummy_action(data): return "Success"
        
        # Risk score 0.1 is below FAST_PATH_THRESHOLD (0.3)
        result = self.router.route(
            action=dummy_action,
            input_data={"data": "test"},
            risk_score=0.1
        )
        
        self.assertEqual(result.path, ReasoningPath.FAST)
        self.assertTrue(result.safe)
        self.assertEqual(result.action_result, "Success")
        self.assertIn("G1_Precondition", result.gates_passed)

    def test_risk_threshold_normal_path(self):
        """Test routing through the NORMAL path for medium-risk actions."""
        def dummy_action(data): return "Success"
        
        # Risk score 0.5 is between 0.3 and 0.7
        result = self.router.route(
            action=dummy_action,
            input_data={"data": "test"},
            risk_score=0.5
        )
        
        self.assertEqual(result.path, ReasoningPath.NORMAL)
        self.assertTrue(result.safe)
        
    def test_risk_threshold_safe_path(self):
        """Test routing through the SAFE path for high-risk actions."""
        def dummy_action(data): return "Success"
        
        # Risk score 0.8 is above SAFE_PATH_THRESHOLD (0.7)
        # Safe path requires human approval (human_approved=True needed in kwargs)
        result = self.router.route(
            action=dummy_action,
            input_data={"data": "test"},
            risk_score=0.8,
            human_approved=True
        )
        
        self.assertEqual(result.path, ReasoningPath.SAFE)
        self.assertTrue(result.safe)
        self.assertTrue(result.human_approved)

    def test_high_risk_without_approval_fails(self):
        """Test that high-risk routing fails without human approval."""
        def dummy_action(data): return "Success"
        
        result = self.router.route(
            action=dummy_action,
            input_data={"data": "test"},
            risk_score=0.9,
            human_approved=False
        )
        
        self.assertFalse(result.safe)
        self.assertIn("Human approval required but not provided", result.violations)

    def test_gate_failure(self):
        """Test that a gate failure correctly marks the routing as unsafe."""
        def dummy_action(data): return "Success"
        
        # input_data is not a dict, should fail PRECONDITION gate (G1)
        result = self.router.route(
            action=dummy_action,
            input_data=None, # type: ignore
            risk_score=0.1
        )
        
        self.assertFalse(result.safe)
        self.assertIn("G1_Precondition", result.violations[0])

if __name__ == '__main__':
    unittest.main()

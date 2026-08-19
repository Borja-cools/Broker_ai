"""Test de zichtbare, veilige risk-engine-demo."""

import unittest

from broker_ai.risk.demo import run_risk_demo


class RiskDemoTest(unittest.TestCase):
    def test_demo_shows_approval_rejection_and_kill_switch(self) -> None:
        report = run_risk_demo()

        self.assertIn("RISK DEMO — geen echte orders", report)
        self.assertIn("Order 1: GOEDGEKEURD", report)
        self.assertIn("Order 2: GEWEIGERD", report)
        self.assertIn("Order 3: GEWEIGERD — Kill switch", report)
        self.assertIn("Risicobeslissingen in auditlog: 3", report)


if __name__ == "__main__":
    unittest.main()

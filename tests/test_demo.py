"""Tests voor het zichtbare, volledig lokale demoscenario."""

from decimal import Decimal
import unittest

from broker_ai.simulation.demo import format_euro, run_demo


class DemoTest(unittest.TestCase):
    def test_euro_amount_has_two_decimals(self) -> None:
        self.assertEqual(format_euro(Decimal("12.5")), "€12.50")

    def test_demo_is_explicitly_marked_as_not_real(self) -> None:
        report = run_demo()

        self.assertIn("DEMO — geen echte order", report)

    def test_demo_reports_position_and_remaining_cash(self) -> None:
        report = run_demo()

        self.assertIn("Gekocht: 3 aandelen à €600.00", report)
        self.assertIn("Verkocht: 1 aandeel à €700.00", report)
        self.assertIn("Resterende positie: 2 aandelen", report)
        self.assertIn("Resterende cash: €3898.00", report)
        self.assertIn("Gerealiseerde winst: €98.67", report)
        self.assertIn("Ongerealiseerde winst: €99.33", report)
        self.assertIn("Totale transactiekosten: €2.00", report)
        self.assertIn("Status: FILLED", report)


if __name__ == "__main__":
    unittest.main()

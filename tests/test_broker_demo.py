"""Test de zichtbare lokale paper-brokerdemo."""

import unittest

from broker_ai.brokers.demo import run_broker_demo


class BrokerDemoTest(unittest.TestCase):
    def test_demo_shows_async_lifecycle_and_safety(self) -> None:
        report = run_broker_demo()

        self.assertIn("lokale paper-adapter, geen extern account", report)
        self.assertIn("Eerste status: SUBMITTED", report)
        self.assertIn("Zelfde order opnieuw: GEEN DUPLICAAT", report)
        self.assertIn("Na reconciliatie: FILLED", report)
        self.assertIn("Tweede order: CANCELLED", report)
        self.assertIn("geen netwerk, API-sleutel, brokeraccount of echt geld", report)


if __name__ == "__main__":
    unittest.main()

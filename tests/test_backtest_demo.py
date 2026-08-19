"""Test het leesbare rapport van de vaste backtestdemo."""

import unittest

from broker_ai.backtesting.demo import run_backtest_demo


class BacktestDemoTest(unittest.TestCase):
    def test_report_is_explicitly_historical_and_safe(self) -> None:
        report = run_backtest_demo()

        self.assertIn("BACKTEST — uitsluitend historische simulatie", report)
        self.assertIn("Strategie: SMA 2/3", report)
        self.assertIn("Rendement benchmark:", report)
        self.assertIn("Maximale drawdown:", report)
        self.assertIn("Sharpe-achtige maatstaf:", report)
        self.assertIn("geen netwerk, broker of echt geld", report)


if __name__ == "__main__":
    unittest.main()

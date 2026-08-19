"""Tests voor tijdsvolgorde, kosten en reproduceerbaarheid van backtests."""

from datetime import date, timedelta
from decimal import Decimal
import unittest

from broker_ai.backtesting import BacktestConfig, BacktestEngine
from broker_ai.data import HistoricalBar, HistoricalDataset
from broker_ai.domain import Currency, Exchange, Instrument
from broker_ai.strategies import Signal


class BuyOnceStrategy:
    name = "Eenmalig kopen"

    def decide(self, history, has_position):
        return Signal.BUY if not has_position else Signal.HOLD


class BacktestingTest(unittest.TestCase):
    def setUp(self) -> None:
        instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
        start = date(2025, 1, 1)
        prices = (("10", "10"), ("20", "21"), ("30", "32"))
        self.dataset = HistoricalDataset(
            instrument,
            tuple(
                HistoricalBar(
                    start + timedelta(days=index),
                    Decimal(open_price),
                    Decimal(close) + Decimal("1"),
                    Decimal(open_price) - Decimal("1"),
                    Decimal(close),
                    100,
                )
                for index, (open_price, close) in enumerate(prices)
            ),
        )
        self.config = BacktestConfig(
            initial_cash=Decimal("100.00"),
            fee_per_order=Decimal("1.00"),
            slippage_rate=Decimal("0.10"),
        )

    def test_signal_executes_at_next_open_with_slippage(self) -> None:
        result = BacktestEngine().run(self.dataset, BuyOnceStrategy(), self.config)

        self.assertEqual(len(result.executions), 1)
        transaction = result.executions[0].transaction
        self.assertEqual(transaction.executed_at.date(), date(2025, 1, 2))
        self.assertEqual(transaction.price, Decimal("22.0"))
        self.assertEqual(transaction.quantity, 1)
        self.assertEqual(len(result.risk_assessments), 1)
        self.assertTrue(result.risk_assessments[0].approved)

    def test_result_is_reproducible(self) -> None:
        first = BacktestEngine().run(self.dataset, BuyOnceStrategy(), self.config)
        second = BacktestEngine().run(self.dataset, BuyOnceStrategy(), self.config)

        self.assertEqual(first, second)

    def test_reports_strategy_and_buy_hold_benchmark(self) -> None:
        result = BacktestEngine().run(self.dataset, BuyOnceStrategy(), self.config)

        self.assertGreater(result.metrics.total_return, Decimal("0"))
        self.assertGreater(result.benchmark_metrics.total_return, result.metrics.total_return)
        self.assertIsNotNone(result.metrics.sharpe_ratio)

    def test_rejects_invalid_slippage(self) -> None:
        with self.assertRaisesRegex(ValueError, "kleiner"):
            BacktestConfig(slippage_rate=Decimal("1"))


if __name__ == "__main__":
    unittest.main()

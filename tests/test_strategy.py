"""Tests voor het strategiecontract en de SMA-referentie."""

from datetime import date, timedelta
from decimal import Decimal
import unittest

from broker_ai.data import HistoricalBar
from broker_ai.strategies import MovingAverageStrategy, Signal


def bars(*closes: str) -> tuple[HistoricalBar, ...]:
    return tuple(
        HistoricalBar(
            date(2025, 1, 1) + timedelta(days=index),
            Decimal(close), Decimal(close), Decimal(close), Decimal(close), 1,
        )
        for index, close in enumerate(closes)
    )


class MovingAverageStrategyTest(unittest.TestCase):
    def test_waits_until_long_window_is_available(self) -> None:
        strategy = MovingAverageStrategy(2, 3)
        self.assertIs(strategy.decide(bars("1", "2"), False), Signal.HOLD)

    def test_buys_when_short_average_is_higher(self) -> None:
        strategy = MovingAverageStrategy(2, 3)
        self.assertIs(strategy.decide(bars("1", "2", "3"), False), Signal.BUY)

    def test_sells_when_short_average_is_lower(self) -> None:
        strategy = MovingAverageStrategy(2, 3)
        self.assertIs(strategy.decide(bars("3", "2", "1"), True), Signal.SELL)

    def test_rejects_inverted_windows(self) -> None:
        with self.assertRaisesRegex(ValueError, "kleiner"):
            MovingAverageStrategy(3, 3)


if __name__ == "__main__":
    unittest.main()

"""Tests voor volledige portefeuillewaardering."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from broker_ai.brokers import SimulatedBroker
from broker_ai.domain import (
    Currency,
    Exchange,
    Instrument,
    MarketPrice,
    Order,
    OrderSide,
    Portfolio,
)


class PortfolioValuationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.asml = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )
        self.portfolio = Portfolio(Decimal("5000.00"))
        SimulatedBroker(fee_per_order=Decimal("1.00")).execute(
            Order(self.asml, OrderSide.BUY, 2, Decimal("600.00")),
            self.portfolio,
        )

    def test_value_combines_cash_and_positions(self) -> None:
        quote = MarketPrice(
            self.asml,
            Decimal("650.00"),
            datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
        )

        valuation = self.portfolio.value({"ASML": quote})

        self.assertEqual(valuation.cash_balance, Decimal("3799.00"))
        self.assertEqual(valuation.position_value, Decimal("1300.00"))
        self.assertEqual(valuation.total_equity, Decimal("5099.00"))
        self.assertEqual(valuation.unrealized_profit, Decimal("99.00"))
        self.assertEqual(valuation.total_profit, Decimal("99.00"))
        self.assertEqual(len(valuation.positions), 1)

    def test_missing_price_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "prijs ontbreekt"):
            self.portfolio.value({})

    def test_quote_for_other_instrument_is_rejected(self) -> None:
        other = Instrument(
            symbol="ADYEN",
            name="Adyen",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )
        wrong_quote = MarketPrice(
            other,
            Decimal("1200.00"),
            datetime.now(timezone.utc),
        )

        with self.assertRaisesRegex(ValueError, "hoort niet bij"):
            self.portfolio.value({"ASML": wrong_quote})


if __name__ == "__main__":
    unittest.main()

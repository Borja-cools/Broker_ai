"""Tests voor expliciete en tijdzonebewuste marktprijzen."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from broker_ai.domain import Currency, Exchange, Instrument, MarketPrice


class MarketPriceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.asml = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

    def test_valid_market_price_keeps_timestamp(self) -> None:
        timestamp = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        quote = MarketPrice(self.asml, Decimal("650.00"), timestamp)

        self.assertEqual(quote.price, Decimal("650.00"))
        self.assertEqual(quote.observed_at, timestamp)

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "tijdzone"):
            MarketPrice(
                self.asml,
                Decimal("650.00"),
                datetime(2026, 8, 19, 12, 0),
            )

    def test_non_positive_price_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "groter dan nul"):
            MarketPrice(
                self.asml,
                Decimal("0.00"),
                datetime.now(timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()


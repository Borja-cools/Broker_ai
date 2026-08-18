"""Tests voor verhandelbare instrumenten."""

from dataclasses import FrozenInstanceError
import unittest

from broker_ai.domain import AssetType, Currency, Exchange, Instrument


class InstrumentTest(unittest.TestCase):
    def test_stock_contains_expected_information(self) -> None:
        instrument = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

        self.assertEqual(instrument.symbol, "ASML")
        self.assertEqual(instrument.name, "ASML Holding")
        self.assertEqual(instrument.asset_type, AssetType.STOCK)

    def test_symbol_is_normalized(self) -> None:
        instrument = Instrument(
            symbol="  asml  ",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

        self.assertEqual(instrument.symbol, "ASML")

    def test_empty_symbol_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Symbool mag niet leeg"):
            Instrument(
                symbol="   ",
                name="ASML Holding",
                exchange=Exchange.EURONEXT_AMSTERDAM,
                currency=Currency.EUR,
            )

    def test_symbol_with_special_characters_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "letters en cijfers"):
            Instrument(
                symbol="ASML!",
                name="ASML Holding",
                exchange=Exchange.EURONEXT_AMSTERDAM,
                currency=Currency.EUR,
            )

    def test_instrument_cannot_change_after_creation(self) -> None:
        instrument = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

        with self.assertRaises(FrozenInstanceError):
            instrument.symbol = "OTHER"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()


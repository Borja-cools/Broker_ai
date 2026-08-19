"""Tests voor import en validatie van historische data."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from broker_ai.data import HistoricalBar, HistoricalDataset, load_csv
from broker_ai.domain import Currency, Exchange, Instrument


class HistoricalDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)

    def test_loads_valid_csv_in_chronological_order(self) -> None:
        path = Path(__file__).parent / "fixtures" / "asml_history.csv"
        dataset = load_csv(path, self.instrument)

        self.assertEqual(len(dataset.bars), 5)
        self.assertEqual(dataset.bars[0].trading_date, date(2025, 1, 2))
        self.assertEqual(dataset.bars[-1].close, Decimal("105"))

    def test_rejects_impossible_ohlc_bar(self) -> None:
        with self.assertRaisesRegex(ValueError, "High"):
            HistoricalBar(date(2025, 1, 2), Decimal("10"), Decimal("9"), Decimal("8"), Decimal("10"), 1)

    def test_rejects_duplicate_dates(self) -> None:
        bar = HistoricalBar(date(2025, 1, 2), Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10"), 1)
        with self.assertRaisesRegex(ValueError, "maar één keer"):
            HistoricalDataset(self.instrument, (bar, bar))

    def test_csv_error_includes_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("date,open,high,low,close,volume\n2025-01-02,x,2,1,1,4\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "regel 2"):
                load_csv(path, self.instrument)


if __name__ == "__main__":
    unittest.main()

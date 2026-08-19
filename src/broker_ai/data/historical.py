"""Gevalideerde historische OHLCV-data, zonder externe dataleverancier."""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from broker_ai.domain import Instrument


@dataclass(frozen=True)
class HistoricalBar:
    """Koersinformatie van één volledige handelsdag."""

    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def __post_init__(self) -> None:
        if not isinstance(self.trading_date, date):
            raise TypeError("Handelsdatum moet een date zijn.")

        for field_name in ("open", "high", "low", "close"):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal):
                raise TypeError(f"{field_name} moet een Decimal zijn.")
            if not value.is_finite() or value <= Decimal("0"):
                raise ValueError(f"{field_name} moet eindig en groter dan nul zijn.")

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("High mag niet lager zijn dan open, close of low.")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("Low mag niet hoger zijn dan open, close of high.")
        if isinstance(self.volume, bool) or not isinstance(self.volume, int):
            raise TypeError("Volume moet een geheel getal zijn.")
        if self.volume < 0:
            raise ValueError("Volume mag niet negatief zijn.")


@dataclass(frozen=True)
class HistoricalDataset:
    """Chronologisch gesorteerde koersreeks van precies één instrument."""

    instrument: Instrument
    bars: tuple[HistoricalBar, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise TypeError("Instrument moet een Instrument zijn.")
        if not isinstance(self.bars, tuple):
            raise TypeError("Bars moeten als tuple worden aangeleverd.")
        if len(self.bars) < 2:
            raise ValueError("Een backtestdataset bevat minimaal twee handelsdagen.")
        if not all(isinstance(bar, HistoricalBar) for bar in self.bars):
            raise TypeError("Elke rij moet een HistoricalBar zijn.")

        dates = [bar.trading_date for bar in self.bars]
        if dates != sorted(dates):
            raise ValueError("Historische data moet chronologisch gesorteerd zijn.")
        if len(dates) != len(set(dates)):
            raise ValueError("Een handelsdatum mag maar één keer voorkomen.")

    @classmethod
    def from_bars(
        cls,
        instrument: Instrument,
        bars: Iterable[HistoricalBar],
    ) -> "HistoricalDataset":
        return cls(instrument=instrument, bars=tuple(bars))


def load_csv(path: str | Path, instrument: Instrument) -> HistoricalDataset:
    """Lees date/open/high/low/close/volume uit een lokaal CSV-bestand."""

    csv_path = Path(path)
    bars: list[HistoricalBar] = []
    required_columns = {"date", "open", "high", "low", "close", "volume"}

    try:
        with csv_path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or set(reader.fieldnames) != required_columns:
                raise ValueError(
                    "CSV-koppen moeten exact date, open, high, low, close en volume zijn."
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    bars.append(
                        HistoricalBar(
                            trading_date=date.fromisoformat(row["date"]),
                            open=Decimal(row["open"]),
                            high=Decimal(row["high"]),
                            low=Decimal(row["low"]),
                            close=Decimal(row["close"]),
                            volume=int(row["volume"]),
                        )
                    )
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Ongeldige historische data op CSV-regel {line_number}: {exc}"
                    ) from exc
    except OSError as exc:
        raise ValueError(f"Historisch databestand kan niet worden gelezen: {csv_path}") from exc

    return HistoricalDataset.from_bars(instrument, bars)

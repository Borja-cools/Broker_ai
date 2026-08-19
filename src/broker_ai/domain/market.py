"""Gevalideerde marktprijzen voor waardering en latere backtests."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from broker_ai.domain.instrument import Instrument


@dataclass(frozen=True)
class MarketPrice:
    """De prijs van één instrument op een expliciet tijdstip."""

    instrument: Instrument
    price: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise TypeError("Instrument moet een Instrument zijn.")

        if not isinstance(self.price, Decimal):
            raise TypeError("Prijs moet een Decimal zijn.")

        if not self.price.is_finite() or self.price <= Decimal("0"):
            raise ValueError("Prijs moet een eindig bedrag groter dan nul zijn.")

        if not isinstance(self.observed_at, datetime):
            raise TypeError("Koerstijdstip moet een datetime zijn.")

        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("Koerstijdstip moet een tijdzone bevatten.")


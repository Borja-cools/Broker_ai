"""Beschrijving en validatie van verhandelbare instrumenten."""

from dataclasses import dataclass
from enum import Enum

from broker_ai.domain.portfolio import Currency


class AssetType(str, Enum):
    """Soorten beleggingen die Broker AI momenteel kent."""

    STOCK = "stock"


class Exchange(str, Enum):
    """Beurzen die onze eerste simulator ondersteunt."""

    EURONEXT_AMSTERDAM = "XAMS"


@dataclass(frozen=True)
class Instrument:
    """Een onveranderlijke identiteit van een verhandelbaar instrument."""

    symbol: str
    name: str
    exchange: Exchange
    currency: Currency
    asset_type: AssetType = AssetType.STOCK

    def __post_init__(self) -> None:
        """Normaliseer en valideer de ingevoerde instrumentgegevens."""

        normalized_symbol = self.symbol.strip().upper()
        normalized_name = self.name.strip()

        if not normalized_symbol:
            raise ValueError("Symbool mag niet leeg zijn.")

        if not normalized_symbol.isalnum():
            raise ValueError("Symbool mag alleen letters en cijfers bevatten.")

        if not normalized_name:
            raise ValueError("Naam mag niet leeg zijn.")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "name", normalized_name)


"""Vast contract tussen strategieën en de backtest-engine."""

from enum import Enum
from typing import Protocol

from broker_ai.data import HistoricalBar


class Signal(str, Enum):
    """Een advies; de strategie mag zelf geen portefeuille wijzigen."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Strategy(Protocol):
    """Iedere strategie ziet alleen data tot en met het beslismoment."""

    @property
    def name(self) -> str: ...

    def decide(self, history: tuple[HistoricalBar, ...], has_position: bool) -> Signal:
        """Geef een signaal op basis van reeds afgesloten koersbars."""


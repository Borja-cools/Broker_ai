"""Eenvoudige referentiestrategie op basis van twee gemiddelden."""

from dataclasses import dataclass
from decimal import Decimal

from broker_ai.data import HistoricalBar
from broker_ai.strategies.base import Signal


@dataclass(frozen=True)
class MovingAverageStrategy:
    """Koop boven het lange gemiddelde en verkoop eronder."""

    short_window: int = 3
    long_window: int = 5

    def __post_init__(self) -> None:
        if isinstance(self.short_window, bool) or not isinstance(self.short_window, int):
            raise TypeError("Korte periode moet een geheel getal zijn.")
        if isinstance(self.long_window, bool) or not isinstance(self.long_window, int):
            raise TypeError("Lange periode moet een geheel getal zijn.")
        if self.short_window <= 0 or self.long_window <= 0:
            raise ValueError("Gemiddeldeperiodes moeten groter zijn dan nul.")
        if self.short_window >= self.long_window:
            raise ValueError("Korte periode moet kleiner zijn dan de lange periode.")

    @property
    def name(self) -> str:
        return f"SMA {self.short_window}/{self.long_window}"

    def decide(self, history: tuple[HistoricalBar, ...], has_position: bool) -> Signal:
        if len(history) < self.long_window:
            return Signal.HOLD

        short_average = self._average(history[-self.short_window :])
        long_average = self._average(history[-self.long_window :])
        if short_average > long_average and not has_position:
            return Signal.BUY
        if short_average < long_average and has_position:
            return Signal.SELL
        return Signal.HOLD

    @staticmethod
    def _average(bars: tuple[HistoricalBar, ...]) -> Decimal:
        return sum((bar.close for bar in bars), Decimal("0")) / len(bars)

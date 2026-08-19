"""Gegevensmodellen voor verklaarbare risicobeslissingen."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from broker_ai.domain import Order, Portfolio


class RiskCode(str, Enum):
    """Stabiele codes die later ook via een API kunnen worden getoond."""

    APPROVED = "approved"
    KILL_SWITCH = "kill_switch"
    MAX_ORDER_VALUE = "max_order_value"
    MAX_POSITION_VALUE = "max_position_value"
    MAX_CONCENTRATION = "max_concentration"
    CASH_RESERVE = "cash_reserve"
    DAILY_LOSS = "daily_loss"
    RULE_ERROR = "rule_error"


@dataclass(frozen=True)
class RiskPolicy:
    """Centraal instelbare grenzen; percentages worden als 0..1 opgeslagen."""

    max_order_value: Decimal = Decimal("2500.00")
    max_position_value: Decimal = Decimal("5000.00")
    max_concentration: Decimal = Decimal("0.25")
    min_cash_reserve: Decimal = Decimal("0.10")
    max_daily_loss: Decimal = Decimal("0.03")

    def __post_init__(self) -> None:
        _positive(self.max_order_value, "Maximale orderwaarde")
        _positive(self.max_position_value, "Maximale positiewaarde")
        _rate(self.max_concentration, "Maximale concentratie", allow_zero=False)
        _rate(self.min_cash_reserve, "Minimale cashreserve", allow_zero=True)
        _rate(self.max_daily_loss, "Maximaal dagverlies", allow_zero=False)


@dataclass(frozen=True)
class RiskContext:
    """Portefeuilletoestand die alle regels op hetzelfde moment beoordelen."""

    portfolio: Portfolio
    current_equity: Decimal
    day_start_equity: Decimal
    market_prices: Mapping[str, Decimal]
    fee: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if not isinstance(self.portfolio, Portfolio):
            raise TypeError("Portefeuille moet een Portfolio zijn.")
        _positive(self.current_equity, "Actuele portefeuillewaarde")
        _positive(self.day_start_equity, "Portefeuillewaarde bij dagstart")
        _non_negative(self.fee, "Transactiekosten")

        normalized: dict[str, Decimal] = {}
        for symbol, price in self.market_prices.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError("Marktprijssymbool moet niet-lege tekst zijn.")
            _positive(price, f"Marktprijs voor {symbol}")
            normalized[symbol.strip().upper()] = price
        object.__setattr__(self, "market_prices", MappingProxyType(normalized))

        calculated_equity = self.portfolio.cash_balance
        for symbol, position in self.portfolio.positions.items():
            if symbol not in normalized:
                raise ValueError(f"Marktprijs ontbreekt voor risicopositie {symbol}.")
            calculated_equity += position.quantity * normalized[symbol]
        if calculated_equity != self.current_equity:
            raise ValueError(
                "Actuele portefeuillewaarde komt niet overeen met cash en posities."
            )

    def price_for(self, order: Order) -> Decimal:
        """Gebruik een actuele koers en alleen de orderprijs als veilige fallback."""

        return self.market_prices.get(order.instrument.symbol, order.price)


@dataclass(frozen=True)
class RiskOutcome:
    """Uitkomst van precies één onafhankelijke regel."""

    code: RiskCode
    approved: bool
    reason: str


@dataclass(frozen=True)
class RiskAssessment:
    """Onveranderlijk auditrecord van één volledige pre-tradecontrole."""

    assessment_id: UUID
    order_id: UUID
    approved: bool
    outcomes: tuple[RiskOutcome, ...]
    evaluated_at: datetime

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        return tuple(item.reason for item in self.outcomes if not item.approved)


def _rate(value: Decimal, name: str, *, allow_zero: bool) -> None:
    _non_negative(value, name)
    if not allow_zero and value == Decimal("0"):
        raise ValueError(f"{name} moet groter zijn dan nul.")
    if value > Decimal("1"):
        raise ValueError(f"{name} mag niet groter zijn dan 100%.")


def _positive(value: Decimal, name: str) -> None:
    _non_negative(value, name)
    if value == Decimal("0"):
        raise ValueError(f"{name} moet groter zijn dan nul.")


def _non_negative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} moet een Decimal zijn.")
    if not value.is_finite() or value < Decimal("0"):
        raise ValueError(f"{name} moet eindig en niet-negatief zijn.")

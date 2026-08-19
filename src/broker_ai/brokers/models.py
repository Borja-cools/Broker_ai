"""Brokerneutrale modellen voor lokale en toekomstige externe adapters."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from broker_ai.brokers.simulated import Execution
from broker_ai.domain import Currency, Order


class BrokerMode(str, Enum):
    SIMULATION = "simulation"
    PAPER = "paper"


class ConnectionState(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class BrokerOrderStatus(str, Enum):
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

    @property
    def is_terminal(self) -> bool:
        return self in {self.FILLED, self.CANCELLED, self.REJECTED}


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    quantity: int
    average_price: Decimal

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.strip().upper():
            raise ValueError("Positiesymbool moet genormaliseerde tekst zijn.")
        if self.quantity <= 0:
            raise ValueError("Positieaantal moet groter zijn dan nul.")
        if not isinstance(self.average_price, Decimal):
            raise TypeError("Gemiddelde positieprijs moet een Decimal zijn.")
        if not self.average_price.is_finite() or self.average_price <= 0:
            raise ValueError("Gemiddelde positieprijs moet eindig en positief zijn.")


@dataclass(frozen=True)
class AccountSnapshot:
    cash_balance: Decimal
    currency: Currency
    positions: tuple[PositionSnapshot, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.cash_balance, Decimal):
            raise TypeError("Brokercash moet een Decimal zijn.")
        if not self.cash_balance.is_finite() or self.cash_balance < 0:
            raise ValueError("Brokercash moet eindig en niet-negatief zijn.")
        if not isinstance(self.currency, Currency):
            raise TypeError("Brokervaluta moet een Currency zijn.")
        if not all(isinstance(item, PositionSnapshot) for item in self.positions):
            raise TypeError("Accountposities moeten PositionSnapshots zijn.")
        _aware(self.observed_at)


@dataclass(frozen=True)
class BrokerStatus:
    mode: BrokerMode
    connection: ConnectionState
    checked_at: datetime
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.mode, BrokerMode):
            raise TypeError("Brokermodus moet een BrokerMode zijn.")
        if not isinstance(self.connection, ConnectionState):
            raise TypeError("Verbinding moet een ConnectionState zijn.")
        _aware(self.checked_at)


@dataclass(frozen=True)
class BrokerOrder:
    """Brokerstatus van een order, los van de interne risicobeslissing."""

    broker_order_id: UUID
    order: Order
    status: BrokerOrderStatus
    submitted_at: datetime
    updated_at: datetime
    execution: Execution | None = None
    status_message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.broker_order_id, UUID):
            raise TypeError("Brokerorder-ID moet een UUID zijn.")
        if not isinstance(self.order, Order):
            raise TypeError("Brokerorder moet een Order bevatten.")
        if not isinstance(self.status, BrokerOrderStatus):
            raise TypeError("Orderstatus moet een BrokerOrderStatus zijn.")
        if self.status is BrokerOrderStatus.FILLED and self.execution is None:
            raise ValueError("Een uitgevoerde brokerorder vereist een Execution.")
        if self.status is not BrokerOrderStatus.FILLED and self.execution is not None:
            raise ValueError("Alleen een uitgevoerde brokerorder mag een Execution hebben.")
        for value in (self.submitted_at, self.updated_at):
            _aware(value)
        if self.updated_at < self.submitted_at:
            raise ValueError("Update-tijdstip mag niet vóór indiening liggen.")


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise TypeError("Brokertijdstip moet een datetime zijn.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Brokertijdstippen moeten een tijdzone bevatten.")

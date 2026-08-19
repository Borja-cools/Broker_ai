"""Onveranderlijke vastlegging van gesimuleerde orderuitvoeringen."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from broker_ai.domain.instrument import Instrument
from broker_ai.domain.order import OrderSide


@dataclass(frozen=True)
class Transaction:
    """Auditrecord van één volledig uitgevoerde simulatieorder."""

    transaction_id: UUID
    order_id: UUID
    instrument: Instrument
    side: OrderSide
    quantity: int
    price: Decimal
    gross_value: Decimal
    fee: Decimal
    cash_change: Decimal
    realized_profit: Decimal
    executed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_id, UUID) or not isinstance(
            self.order_id, UUID
        ):
            raise TypeError("Transactie- en order-ID moeten UUID's zijn.")

        if not isinstance(self.instrument, Instrument):
            raise TypeError("Instrument moet een Instrument zijn.")

        if not isinstance(self.side, OrderSide):
            raise TypeError("Orderrichting moet een OrderSide zijn.")

        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise TypeError("Aantal moet een geheel getal zijn.")

        if self.quantity <= 0:
            raise ValueError("Aantal moet groter zijn dan nul.")

        for field_name, amount in (
            ("Prijs", self.price),
            ("Brutowaarde", self.gross_value),
            ("Transactiekosten", self.fee),
            ("Cashmutatie", self.cash_change),
            ("Gerealiseerde winst", self.realized_profit),
        ):
            if not isinstance(amount, Decimal):
                raise TypeError(f"{field_name} moet een Decimal zijn.")

            if not amount.is_finite():
                raise ValueError(f"{field_name} moet eindig zijn.")

        if self.price <= Decimal("0") or self.gross_value <= Decimal("0"):
            raise ValueError("Prijs en brutowaarde moeten groter zijn dan nul.")

        if self.fee < Decimal("0"):
            raise ValueError("Transactiekosten mogen niet negatief zijn.")

        if not isinstance(self.executed_at, datetime):
            raise TypeError("Uitvoeringstijdstip moet een datetime zijn.")

        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("Uitvoeringstijdstip moet een tijdzone bevatten.")

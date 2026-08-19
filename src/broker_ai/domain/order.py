"""Orderverzoeken voor de Broker AI-simulator."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from broker_ai.domain.instrument import Instrument


class OrderSide(str, Enum):
    """Orderrichtingen die de simulator momenteel accepteert."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Order:
    """Een onveranderlijk verzoek om een instrument te kopen of verkopen."""

    instrument: Instrument
    side: OrderSide
    quantity: int
    price: Decimal
    order_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Controleer de order zodra hij wordt aangemaakt."""

        if not isinstance(self.instrument, Instrument):
            raise TypeError("Instrument moet een Instrument zijn.")

        if not isinstance(self.side, OrderSide):
            raise TypeError("Orderrichting moet een OrderSide zijn.")

        if not isinstance(self.order_id, UUID):
            raise TypeError("Order-ID moet een UUID zijn.")

        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise TypeError("Aantal moet een geheel getal zijn.")

        if self.quantity <= 0:
            raise ValueError("Aantal moet groter zijn dan nul.")

        if not isinstance(self.price, Decimal):
            raise TypeError("Prijs moet een Decimal zijn.")

        if not self.price.is_finite():
            raise ValueError("Prijs moet een eindig bedrag zijn.")

        if self.price <= Decimal("0"):
            raise ValueError("Prijs moet groter zijn dan nul.")

        if self.instrument.currency.value != "EUR":
            raise ValueError("Alleen EUR-orders worden momenteel ondersteund.")

    @property
    def total_value(self) -> Decimal:
        """Bereken de orderwaarde zonder de portefeuille te wijzigen."""

        return self.price * self.quantity

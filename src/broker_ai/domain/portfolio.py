"""Een eenvoudige, veilige portefeuille voor onze eerste simulaties."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from broker_ai.domain.instrument import Instrument


class Currency(str, Enum):
    """Valuta's die onze portefeuille momenteel ondersteunt."""

    EUR = "EUR"


@dataclass
class Position:
    """Een verzameling aangekochte eenheden van hetzelfde instrument."""

    instrument: "Instrument"
    quantity: int
    average_price: Decimal

    def add_purchase(self, quantity: int, price: Decimal) -> None:
        """Voeg een aankoop toe en bereken de gewogen gemiddelde prijs."""

        existing_value = self.average_price * self.quantity
        purchase_value = price * quantity
        new_quantity = self.quantity + quantity

        self.average_price = (existing_value + purchase_value) / new_quantity
        self.quantity = new_quantity

    def remove_sale(self, quantity: int) -> Decimal:
        """Verlaag het aantal en geef de historische kostprijs ervan terug."""

        if quantity > self.quantity:
            raise ValueError("Onvoldoende aandelen beschikbaar.")

        cost_basis = self.average_price * quantity
        self.quantity -= quantity
        return cost_basis

    def market_value(self, current_price: Decimal) -> Decimal:
        """Bereken wat de positie tegen een opgegeven marktprijs waard is."""

        return current_price * self.quantity

    def unrealized_profit(self, current_price: Decimal) -> Decimal:
        """Bereken de nog niet gerealiseerde winst of het verlies."""

        return (current_price - self.average_price) * self.quantity


@dataclass
class Portfolio:
    """Beheer het beschikbare cashsaldo van één simulatieportefeuille."""

    cash_balance: Decimal
    currency: Currency = Currency.EUR
    positions: dict[str, Position] = field(default_factory=dict, init=False)
    realized_profit: Decimal = field(
        default=Decimal("0.00"),
        init=False,
    )

    def __post_init__(self) -> None:
        """Controleer de waarden nadat Python het object heeft gemaakt."""

        self._validate_amount(self.cash_balance, field_name="Beginsaldo")

    def deposit(self, amount: Decimal) -> None:
        """Voeg een positief geldbedrag toe aan de portefeuille."""

        self._validate_positive_amount(amount)
        self.cash_balance += amount

    def withdraw(self, amount: Decimal) -> None:
        """Neem geld op als het beschikbare saldo voldoende is."""

        self._validate_positive_amount(amount)

        if amount > self.cash_balance:
            raise ValueError("Onvoldoende cash beschikbaar.")

        self.cash_balance -= amount

    def record_purchase(
        self,
        instrument: "Instrument",
        quantity: int,
        price: Decimal,
    ) -> None:
        """Registreer een reeds gevalideerde, uitgevoerde aankoop."""

        position = self.positions.get(instrument.symbol)

        if position is None:
            self.positions[instrument.symbol] = Position(
                instrument=instrument,
                quantity=quantity,
                average_price=price,
            )
            return

        if position.instrument != instrument:
            raise ValueError(
                f"Symbool {instrument.symbol} verwijst al naar een ander instrument."
            )

        position.add_purchase(quantity=quantity, price=price)

    def record_sale(
        self,
        instrument: "Instrument",
        quantity: int,
        sale_price: Decimal,
    ) -> None:
        """Registreer een reeds gevalideerde verkoop in de posities."""

        position = self.positions.get(instrument.symbol)

        if position is None:
            raise ValueError(f"Geen positie beschikbaar voor {instrument.symbol}.")

        if position.instrument != instrument:
            raise ValueError(
                f"Symbool {instrument.symbol} verwijst naar een ander instrument."
            )

        cost_basis = position.remove_sale(quantity)
        sale_value = sale_price * quantity
        self.realized_profit += sale_value - cost_basis

        if position.quantity == 0:
            del self.positions[instrument.symbol]

    def get_position(self, symbol: str) -> Position | None:
        """Zoek een positie op met een hoofdletterongevoelig symbool."""

        return self.positions.get(symbol.strip().upper())

    @staticmethod
    def _validate_amount(amount: Decimal, *, field_name: str) -> None:
        """Weiger verkeerde types, oneindige waarden en negatieve bedragen."""

        if not isinstance(amount, Decimal):
            raise TypeError(f"{field_name} moet een Decimal zijn.")

        if not amount.is_finite():
            raise ValueError(f"{field_name} moet een eindig bedrag zijn.")

        if amount < Decimal("0"):
            raise ValueError(f"{field_name} mag niet negatief zijn.")

    @classmethod
    def _validate_positive_amount(cls, amount: Decimal) -> None:
        """Controleer dat een mutatie een strikt positief bedrag gebruikt."""

        cls._validate_amount(amount, field_name="Bedrag")

        if amount == Decimal("0"):
            raise ValueError("Bedrag moet groter zijn dan nul.")

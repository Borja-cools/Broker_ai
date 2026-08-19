"""Een eenvoudige, veilige portefeuille voor onze eerste simulaties."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from broker_ai.domain.instrument import Instrument
    from broker_ai.domain.market import MarketPrice


class Currency(str, Enum):
    """Valuta's die onze portefeuille momenteel ondersteunt."""

    EUR = "EUR"
    USD = "USD"


@dataclass
class Position:
    """Een verzameling aangekochte eenheden van hetzelfde instrument."""

    instrument: "Instrument"
    quantity: int
    average_price: Decimal

    def __post_init__(self) -> None:
        """Weiger posities die niet via geldige aantallen en prijzen zijn opgebouwd."""

        from broker_ai.domain.instrument import Instrument

        if not isinstance(self.instrument, Instrument):
            raise TypeError("Instrument moet een Instrument zijn.")

        self._validate_trade_values(self.quantity, self.average_price)

    def add_purchase(self, quantity: int, price: Decimal) -> None:
        """Voeg een aankoop toe en bereken de gewogen gemiddelde prijs."""

        self._validate_trade_values(quantity, price)

        existing_value = self.average_price * self.quantity
        purchase_value = price * quantity
        new_quantity = self.quantity + quantity

        self.average_price = (existing_value + purchase_value) / new_quantity
        self.quantity = new_quantity

    def remove_sale(self, quantity: int) -> Decimal:
        """Verlaag het aantal en geef de historische kostprijs ervan terug."""

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise TypeError("Aantal moet een geheel getal zijn.")

        if quantity <= 0:
            raise ValueError("Aantal moet groter zijn dan nul.")

        if quantity > self.quantity:
            raise ValueError("Onvoldoende aandelen beschikbaar.")

        cost_basis = self.average_price * quantity
        self.quantity -= quantity
        return cost_basis

    def market_value(self, current_price: Decimal) -> Decimal:
        """Bereken wat de positie tegen een opgegeven marktprijs waard is."""

        self._validate_price(current_price)

        return current_price * self.quantity

    def unrealized_profit(self, current_price: Decimal) -> Decimal:
        """Bereken de nog niet gerealiseerde winst of het verlies."""

        self._validate_price(current_price)

        return (current_price - self.average_price) * self.quantity

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if not isinstance(price, Decimal):
            raise TypeError("Prijs moet een Decimal zijn.")

        if not price.is_finite() or price <= Decimal("0"):
            raise ValueError("Prijs moet een eindig bedrag groter dan nul zijn.")

    @classmethod
    def _validate_trade_values(cls, quantity: int, price: Decimal) -> None:
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise TypeError("Aantal moet een geheel getal zijn.")

        if quantity <= 0:
            raise ValueError("Aantal moet groter zijn dan nul.")

        cls._validate_price(price)


@dataclass(frozen=True)
class PositionValuation:
    """Waardering van één positie tegen één gevalideerde marktprijs."""

    symbol: str
    quantity: int
    average_price: Decimal
    current_price: Decimal
    cost_basis: Decimal
    market_value: Decimal
    unrealized_profit: Decimal


@dataclass(frozen=True)
class PortfolioValuation:
    """Volledig waarderingsmoment van cash en alle posities."""

    cash_balance: Decimal
    position_value: Decimal
    total_equity: Decimal
    realized_profit: Decimal
    unrealized_profit: Decimal
    positions: tuple[PositionValuation, ...]

    @property
    def total_profit(self) -> Decimal:
        """Combineer definitieve en nog koersafhankelijke winst."""

        return self.realized_profit + self.unrealized_profit


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

        if not isinstance(self.currency, Currency):
            raise TypeError("Valuta moet een Currency zijn.")

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

        Position._validate_trade_values(quantity, price)

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

        Position._validate_trade_values(quantity, sale_price)

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

        if not isinstance(symbol, str):
            raise TypeError("Symbool moet tekst zijn.")

        return self.positions.get(symbol.strip().upper())

    def value(self, prices: Mapping[str, "MarketPrice"]) -> PortfolioValuation:
        """Waardeer iedere positie; ontbrekende of verkeerde quotes worden geweigerd."""

        position_valuations: list[PositionValuation] = []

        for symbol, position in sorted(self.positions.items()):
            quote = prices.get(symbol)
            if quote is None:
                raise ValueError(f"Actuele prijs ontbreekt voor {symbol}.")

            if quote.instrument != position.instrument:
                raise ValueError(f"Actuele prijs hoort niet bij positie {symbol}.")

            market_value = position.market_value(quote.price)
            cost_basis = position.average_price * position.quantity
            position_valuations.append(
                PositionValuation(
                    symbol=symbol,
                    quantity=position.quantity,
                    average_price=position.average_price,
                    current_price=quote.price,
                    cost_basis=cost_basis,
                    market_value=market_value,
                    unrealized_profit=market_value - cost_basis,
                )
            )

        total_position_value = sum(
            (item.market_value for item in position_valuations),
            start=Decimal("0.00"),
        )
        total_unrealized_profit = sum(
            (item.unrealized_profit for item in position_valuations),
            start=Decimal("0.00"),
        )
        return PortfolioValuation(
            cash_balance=self.cash_balance,
            position_value=total_position_value,
            total_equity=self.cash_balance + total_position_value,
            realized_profit=self.realized_profit,
            unrealized_profit=total_unrealized_profit,
            positions=tuple(position_valuations),
        )

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

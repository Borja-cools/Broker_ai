"""Een lokale broker die nooit verbinding maakt met een echte markt."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from broker_ai.domain import Order, OrderSide, Portfolio, Position


class ExecutionStatus(str, Enum):
    """Mogelijke resultaten van een gesimuleerde uitvoering."""

    FILLED = "filled"


@dataclass(frozen=True)
class Execution:
    """Bewijs dat een order volledig door de simulator werd verwerkt."""

    order: Order
    status: ExecutionStatus
    executed_value: Decimal
    fee: Decimal
    cash_change: Decimal


class SimulatedBroker:
    """Verwerk geldige orders uitsluitend in een lokale portefeuille."""

    def __init__(self, fee_per_order: Decimal = Decimal("0.00")) -> None:
        """Maak een simulator met vaste transactiekosten per order."""

        if not isinstance(fee_per_order, Decimal):
            raise TypeError("Transactiekosten moeten een Decimal zijn.")

        if not fee_per_order.is_finite() or fee_per_order < Decimal("0"):
            raise ValueError("Transactiekosten moeten een eindig, positief bedrag zijn.")

        self.fee_per_order = fee_per_order

    def execute(self, order: Order, portfolio: Portfolio) -> Execution:
        """Voer een kooporder uit nadat alle controles zijn geslaagd."""

        if order.instrument.currency is not portfolio.currency:
            raise ValueError("Valuta van order en portefeuille komt niet overeen.")

        existing_position = portfolio.get_position(order.instrument.symbol)
        if existing_position and existing_position.instrument != order.instrument:
            raise ValueError(
                f"Symbool {order.instrument.symbol} hoort bij een ander instrument."
            )

        if order.side is OrderSide.BUY:
            cash_change = self._execute_buy(order, portfolio)
        elif order.side is OrderSide.SELL:
            cash_change = self._execute_sell(order, portfolio, existing_position)
        else:
            raise ValueError(f"Niet-ondersteunde orderrichting: {order.side!r}.")

        return Execution(
            order=order,
            status=ExecutionStatus.FILLED,
            executed_value=order.total_value,
            fee=self.fee_per_order,
            cash_change=cash_change,
        )

    def _execute_buy(self, order: Order, portfolio: Portfolio) -> Decimal:
        """Controleer en verwerk een kooporder."""

        total_debit = order.total_value + self.fee_per_order

        if total_debit > portfolio.cash_balance:
            raise ValueError("Onvoldoende cash voor deze kooporder.")

        effective_unit_cost = total_debit / order.quantity
        portfolio.withdraw(total_debit)
        portfolio.record_purchase(
            instrument=order.instrument,
            quantity=order.quantity,
            price=effective_unit_cost,
        )
        return -total_debit

    def _execute_sell(
        self,
        order: Order,
        portfolio: Portfolio,
        position: Position | None,
    ) -> Decimal:
        """Controleer en verwerk een verkooporder."""

        if position is None:
            raise ValueError(
                f"Geen positie beschikbaar voor {order.instrument.symbol}."
            )

        if order.quantity > position.quantity:
            raise ValueError("Onvoldoende aandelen beschikbaar.")

        net_proceeds = order.total_value - self.fee_per_order
        if net_proceeds < Decimal("0"):
            raise ValueError("Transactiekosten zijn hoger dan de verkoopwaarde.")

        portfolio.record_sale(
            instrument=order.instrument,
            quantity=order.quantity,
            sale_price=net_proceeds / order.quantity,
        )
        if net_proceeds > Decimal("0"):
            portfolio.deposit(net_proceeds)
        return net_proceeds

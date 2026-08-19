"""Een lokale broker die nooit verbinding maakt met een echte markt."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from broker_ai.domain import Order, OrderSide, Portfolio, Position, Transaction


class ExecutionStatus(str, Enum):
    """Mogelijke resultaten van een gesimuleerde uitvoering."""

    FILLED = "filled"


@dataclass(frozen=True)
class Execution:
    """Bewijs dat een order volledig door de simulator werd verwerkt."""

    order: Order
    status: ExecutionStatus
    transaction: Transaction

    @property
    def executed_value(self) -> Decimal:
        return self.transaction.gross_value

    @property
    def fee(self) -> Decimal:
        return self.transaction.fee

    @property
    def cash_change(self) -> Decimal:
        return self.transaction.cash_change


class SimulatedBroker:
    """Verwerk geldige orders uitsluitend in een lokale portefeuille."""

    def __init__(
        self,
        fee_per_order: Decimal = Decimal("0.00"),
        *,
        clock: Callable[[], datetime] | None = None,
        transaction_id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        """Maak een simulator met vaste transactiekosten per order."""

        if not isinstance(fee_per_order, Decimal):
            raise TypeError("Transactiekosten moeten een Decimal zijn.")

        if not fee_per_order.is_finite() or fee_per_order < Decimal("0"):
            raise ValueError(
                "Transactiekosten moeten een eindig, niet-negatief bedrag zijn."
            )

        self.fee_per_order = fee_per_order
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._transaction_id_factory = transaction_id_factory or uuid4
        self._transactions: list[Transaction] = []

    @property
    def transactions(self) -> tuple[Transaction, ...]:
        """Geef een onveranderlijke momentopname van het transactielog terug."""

        return tuple(self._transactions)

    def execute(self, order: Order, portfolio: Portfolio) -> Execution:
        """Voer een kooporder uit nadat alle controles zijn geslaagd."""

        transaction_id = self._transaction_id_factory()
        executed_at = self._clock()
        self._validate_transaction_metadata(transaction_id, executed_at)

        if order.instrument.currency is not portfolio.currency:
            raise ValueError("Valuta van order en portefeuille komt niet overeen.")

        existing_position = portfolio.get_position(order.instrument.symbol)
        if existing_position and existing_position.instrument != order.instrument:
            raise ValueError(
                f"Symbool {order.instrument.symbol} hoort bij een ander instrument."
            )

        realized_profit_before = portfolio.realized_profit

        if order.side is OrderSide.BUY:
            cash_change = self._execute_buy(order, portfolio)
        elif order.side is OrderSide.SELL:
            cash_change = self._execute_sell(order, portfolio, existing_position)
        else:
            raise ValueError(f"Niet-ondersteunde orderrichting: {order.side!r}.")

        transaction = Transaction(
            transaction_id=transaction_id,
            order_id=order.order_id,
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            gross_value=order.total_value,
            fee=self.fee_per_order,
            cash_change=cash_change,
            realized_profit=portfolio.realized_profit - realized_profit_before,
            executed_at=executed_at,
        )
        self._transactions.append(transaction)

        return Execution(
            order=order,
            status=ExecutionStatus.FILLED,
            transaction=transaction,
        )

    def _validate_transaction_metadata(
        self,
        transaction_id: UUID,
        executed_at: datetime,
    ) -> None:
        """Controleer auditmetadata vóórdat de portefeuille kan veranderen."""

        if not isinstance(transaction_id, UUID):
            raise TypeError("Transactie-ID moet een UUID zijn.")

        if any(
            item.transaction_id == transaction_id for item in self._transactions
        ):
            raise ValueError(f"Dubbele transactie-ID: {transaction_id}.")

        if not isinstance(executed_at, datetime):
            raise TypeError("Uitvoeringstijdstip moet een datetime zijn.")

        if executed_at.tzinfo is None or executed_at.utcoffset() is None:
            raise ValueError("Uitvoeringstijdstip moet een tijdzone bevatten.")

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
        if net_proceeds <= Decimal("0"):
            raise ValueError(
                "Transactiekosten moeten lager zijn dan de verkoopwaarde."
            )

        portfolio.record_sale(
            instrument=order.instrument,
            quantity=order.quantity,
            sale_price=net_proceeds / order.quantity,
        )
        portfolio.deposit(net_proceeds)
        return net_proceeds

"""End-to-endtests voor de eerste gesimuleerde kooporders."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from broker_ai.brokers import ExecutionStatus, SimulatedBroker
from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide, Portfolio


class SimulatedBrokerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.broker = SimulatedBroker()
        self.portfolio = Portfolio(cash_balance=Decimal("5000.00"))
        self.asml = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

    def make_order(
        self,
        quantity: int,
        price: str,
        side: OrderSide = OrderSide.BUY,
    ) -> Order:
        return Order(
            instrument=self.asml,
            side=side,
            quantity=quantity,
            price=Decimal(price),
        )

    def test_buy_order_reduces_cash_and_creates_position(self) -> None:
        order = self.make_order(quantity=2, price="625.50")

        execution = self.broker.execute(order, self.portfolio)

        position = self.portfolio.get_position("ASML")
        self.assertEqual(execution.status, ExecutionStatus.FILLED)
        self.assertEqual(execution.executed_value, Decimal("1251.00"))
        self.assertEqual(self.portfolio.cash_balance, Decimal("3749.00"))
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 2)  # type: ignore[union-attr]
        self.assertEqual(position.average_price, Decimal("625.50"))  # type: ignore[union-attr]

    def test_second_purchase_updates_weighted_average_price(self) -> None:
        self.broker.execute(self.make_order(2, "600.00"), self.portfolio)
        self.broker.execute(self.make_order(1, "900.00"), self.portfolio)

        position = self.portfolio.get_position("asml")
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 3)  # type: ignore[union-attr]
        self.assertEqual(position.average_price, Decimal("700.00"))  # type: ignore[union-attr]

    def test_insufficient_cash_leaves_portfolio_unchanged(self) -> None:
        order = self.make_order(quantity=10, price="625.50")

        with self.assertRaisesRegex(ValueError, "Onvoldoende cash"):
            self.broker.execute(order, self.portfolio)

        self.assertEqual(self.portfolio.cash_balance, Decimal("5000.00"))
        self.assertIsNone(self.portfolio.get_position("ASML"))
        self.assertEqual(self.broker.transactions, ())

    def test_position_lookup_normalizes_symbol(self) -> None:
        self.broker.execute(self.make_order(1, "625.50"), self.portfolio)

        self.assertIsNotNone(self.portfolio.get_position("  asml  "))

    def test_buy_fee_is_deducted_and_added_to_cost_basis(self) -> None:
        broker = SimulatedBroker(fee_per_order=Decimal("1.00"))

        execution = broker.execute(self.make_order(2, "600.00"), self.portfolio)

        position = self.portfolio.get_position("ASML")
        self.assertEqual(execution.fee, Decimal("1.00"))
        self.assertEqual(execution.cash_change, Decimal("-1201.00"))
        self.assertEqual(self.portfolio.cash_balance, Decimal("3799.00"))
        self.assertIsNotNone(position)
        self.assertEqual(position.average_price, Decimal("600.50"))  # type: ignore[union-attr]

    def test_sell_fee_reduces_cash_and_realized_profit(self) -> None:
        broker = SimulatedBroker(fee_per_order=Decimal("1.00"))
        broker.execute(self.make_order(2, "600.00"), self.portfolio)

        execution = broker.execute(
            self.make_order(2, "650.00", side=OrderSide.SELL),
            self.portfolio,
        )

        self.assertEqual(execution.cash_change, Decimal("1299.00"))
        self.assertEqual(self.portfolio.cash_balance, Decimal("5098.00"))
        self.assertEqual(self.portfolio.realized_profit, Decimal("98.00"))

    def test_negative_fee_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Transactiekosten"):
            SimulatedBroker(fee_per_order=Decimal("-0.01"))

    def test_successful_execution_is_added_to_audit_log(self) -> None:
        fixed_time = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
        fixed_id = UUID("11111111-1111-1111-1111-111111111111")
        broker = SimulatedBroker(
            fee_per_order=Decimal("1.00"),
            clock=lambda: fixed_time,
            transaction_id_factory=lambda: fixed_id,
        )
        order = self.make_order(2, "600.00")

        execution = broker.execute(order, self.portfolio)

        self.assertEqual(len(broker.transactions), 1)
        transaction = broker.transactions[0]
        self.assertIs(execution.transaction, transaction)
        self.assertEqual(transaction.transaction_id, fixed_id)
        self.assertEqual(transaction.order_id, order.order_id)
        self.assertEqual(transaction.executed_at, fixed_time)
        self.assertEqual(transaction.gross_value, Decimal("1200.00"))
        self.assertEqual(transaction.fee, Decimal("1.00"))
        self.assertEqual(transaction.cash_change, Decimal("-1201.00"))
        self.assertEqual(transaction.realized_profit, Decimal("0.00"))

    def test_sell_transaction_records_realized_profit(self) -> None:
        broker = SimulatedBroker(fee_per_order=Decimal("1.00"))
        broker.execute(self.make_order(2, "600.00"), self.portfolio)

        execution = broker.execute(
            self.make_order(1, "700.00", side=OrderSide.SELL),
            self.portfolio,
        )

        self.assertEqual(execution.transaction.realized_profit, Decimal("98.50"))
        self.assertEqual(len(broker.transactions), 2)

    def test_naive_clock_fails_before_portfolio_changes(self) -> None:
        broker = SimulatedBroker(clock=lambda: datetime(2026, 8, 19, 12, 0))

        with self.assertRaisesRegex(ValueError, "tijdzone"):
            broker.execute(self.make_order(1, "600.00"), self.portfolio)

        self.assertEqual(self.portfolio.cash_balance, Decimal("5000.00"))
        self.assertIsNone(self.portfolio.get_position("ASML"))
        self.assertEqual(broker.transactions, ())

    def test_duplicate_transaction_id_fails_before_second_change(self) -> None:
        fixed_id = UUID("22222222-2222-2222-2222-222222222222")
        broker = SimulatedBroker(transaction_id_factory=lambda: fixed_id)
        broker.execute(self.make_order(1, "600.00"), self.portfolio)
        cash_after_first_order = self.portfolio.cash_balance

        with self.assertRaisesRegex(ValueError, "Dubbele transactie-ID"):
            broker.execute(self.make_order(1, "600.00"), self.portfolio)

        self.assertEqual(self.portfolio.cash_balance, cash_after_first_order)
        self.assertEqual(self.portfolio.get_position("ASML").quantity, 1)  # type: ignore[union-attr]
        self.assertEqual(len(broker.transactions), 1)

    def test_fee_equal_to_sale_value_leaves_portfolio_unchanged(self) -> None:
        broker = SimulatedBroker(fee_per_order=Decimal("10.00"))
        broker.execute(self.make_order(1, "600.00"), self.portfolio)
        cash_before_sale = self.portfolio.cash_balance

        with self.assertRaisesRegex(ValueError, "lager zijn"):
            broker.execute(
                self.make_order(1, "10.00", side=OrderSide.SELL),
                self.portfolio,
            )

        self.assertEqual(self.portfolio.cash_balance, cash_before_sale)
        self.assertEqual(self.portfolio.get_position("ASML").quantity, 1)  # type: ignore[union-attr]
        self.assertEqual(len(broker.transactions), 1)

    def test_sell_order_increases_cash_and_reduces_position(self) -> None:
        self.broker.execute(self.make_order(3, "600.00"), self.portfolio)

        execution = self.broker.execute(
            self.make_order(1, "700.00", side=OrderSide.SELL),
            self.portfolio,
        )

        position = self.portfolio.get_position("ASML")
        self.assertEqual(execution.status, ExecutionStatus.FILLED)
        self.assertEqual(self.portfolio.cash_balance, Decimal("3900.00"))
        self.assertEqual(self.portfolio.realized_profit, Decimal("100.00"))
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 2)  # type: ignore[union-attr]
        self.assertEqual(position.average_price, Decimal("600.00"))  # type: ignore[union-attr]
        self.assertEqual(
            position.market_value(Decimal("650.00")),  # type: ignore[union-attr]
            Decimal("1300.00"),
        )
        self.assertEqual(
            position.unrealized_profit(Decimal("650.00")),  # type: ignore[union-attr]
            Decimal("100.00"),
        )

    def test_selling_entire_position_removes_it(self) -> None:
        self.broker.execute(self.make_order(2, "600.00"), self.portfolio)

        self.broker.execute(
            self.make_order(2, "650.00", side=OrderSide.SELL),
            self.portfolio,
        )

        self.assertIsNone(self.portfolio.get_position("ASML"))
        self.assertEqual(self.portfolio.cash_balance, Decimal("5100.00"))
        self.assertEqual(self.portfolio.realized_profit, Decimal("100.00"))

    def test_selling_without_position_changes_nothing(self) -> None:
        sell_order = self.make_order(1, "700.00", side=OrderSide.SELL)

        with self.assertRaisesRegex(ValueError, "Geen positie"):
            self.broker.execute(sell_order, self.portfolio)

        self.assertEqual(self.portfolio.cash_balance, Decimal("5000.00"))
        self.assertEqual(self.portfolio.realized_profit, Decimal("0.00"))
        self.assertIsNone(self.portfolio.get_position("ASML"))

    def test_selling_too_many_shares_changes_nothing(self) -> None:
        self.broker.execute(self.make_order(2, "600.00"), self.portfolio)
        cash_before_sale = self.portfolio.cash_balance

        with self.assertRaisesRegex(ValueError, "Onvoldoende aandelen"):
            self.broker.execute(
                self.make_order(3, "700.00", side=OrderSide.SELL),
                self.portfolio,
            )

        position = self.portfolio.get_position("ASML")
        self.assertEqual(self.portfolio.cash_balance, cash_before_sale)
        self.assertEqual(self.portfolio.realized_profit, Decimal("0.00"))
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 2)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()

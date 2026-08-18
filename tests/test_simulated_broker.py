"""End-to-endtests voor de eerste gesimuleerde kooporders."""

from decimal import Decimal
import unittest

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

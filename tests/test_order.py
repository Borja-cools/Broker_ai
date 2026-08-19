"""Tests voor onveranderlijke kooporders."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
import unittest

from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide


class OrderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.asml = Instrument(
            symbol="ASML",
            name="ASML Holding",
            exchange=Exchange.EURONEXT_AMSTERDAM,
            currency=Currency.EUR,
        )

    def test_buy_order_calculates_total_value(self) -> None:
        order = Order(
            instrument=self.asml,
            side=OrderSide.BUY,
            quantity=2,
            price=Decimal("625.50"),
        )

        self.assertEqual(order.total_value, Decimal("1251.00"))

    def test_zero_quantity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Aantal moet groter"):
            Order(
                instrument=self.asml,
                side=OrderSide.BUY,
                quantity=0,
                price=Decimal("625.50"),
            )

    def test_fractional_quantity_is_rejected_for_now(self) -> None:
        with self.assertRaisesRegex(TypeError, "geheel getal"):
            Order(
                instrument=self.asml,
                side=OrderSide.BUY,
                quantity=2.5,  # type: ignore[arg-type]
                price=Decimal("625.50"),
            )

    def test_float_price_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "Decimal"):
            Order(
                instrument=self.asml,
                side=OrderSide.BUY,
                quantity=2,
                price=625.50,  # type: ignore[arg-type]
            )

    def test_zero_price_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Prijs moet groter"):
            Order(
                instrument=self.asml,
                side=OrderSide.BUY,
                quantity=2,
                price=Decimal("0"),
            )

    def test_order_cannot_change_after_creation(self) -> None:
        order = Order(
            instrument=self.asml,
            side=OrderSide.BUY,
            quantity=2,
            price=Decimal("625.50"),
        )

        with self.assertRaises(FrozenInstanceError):
            order.quantity = 3  # type: ignore[misc]

    def test_each_order_gets_a_unique_id(self) -> None:
        first = Order(
            instrument=self.asml,
            side=OrderSide.BUY,
            quantity=1,
            price=Decimal("625.50"),
        )
        second = Order(
            instrument=self.asml,
            side=OrderSide.BUY,
            quantity=1,
            price=Decimal("625.50"),
        )

        self.assertNotEqual(first.order_id, second.order_id)


if __name__ == "__main__":
    unittest.main()

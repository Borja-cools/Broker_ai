"""Tests voor het cashgedeelte van onze simulatieportefeuille."""

from decimal import Decimal
import unittest

from broker_ai.domain import Currency, Portfolio


class PortfolioTest(unittest.TestCase):
    def setUp(self) -> None:
        """Maak vóór iedere test een nieuwe, onafhankelijke portefeuille."""

        self.portfolio = Portfolio(cash_balance=Decimal("1000.00"))

    def test_portfolio_starts_with_euro_balance(self) -> None:
        self.assertEqual(self.portfolio.cash_balance, Decimal("1000.00"))
        self.assertEqual(self.portfolio.currency, Currency.EUR)

    def test_deposit_increases_cash_balance(self) -> None:
        self.portfolio.deposit(Decimal("250.00"))

        self.assertEqual(self.portfolio.cash_balance, Decimal("1250.00"))

    def test_withdraw_decreases_cash_balance(self) -> None:
        self.portfolio.withdraw(Decimal("300.00"))

        self.assertEqual(self.portfolio.cash_balance, Decimal("700.00"))

    def test_withdraw_rejects_insufficient_cash(self) -> None:
        with self.assertRaisesRegex(ValueError, "Onvoldoende cash"):
            self.portfolio.withdraw(Decimal("1000.01"))

        self.assertEqual(self.portfolio.cash_balance, Decimal("1000.00"))

    def test_negative_starting_balance_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "mag niet negatief"):
            Portfolio(cash_balance=Decimal("-0.01"))

    def test_float_amount_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "Decimal"):
            self.portfolio.deposit(10.50)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()


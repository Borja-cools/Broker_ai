"""Kleine, samenstelbare risicoregels met één verantwoordelijkheid."""

from dataclasses import dataclass
from typing import Protocol

from broker_ai.domain import Order, OrderSide
from broker_ai.risk.models import RiskCode, RiskContext, RiskOutcome, RiskPolicy


class RiskRule(Protocol):
    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome: ...


@dataclass
class KillSwitchRule:
    """Operationele noodstop die iedere order blokkeert wanneer hij actief is."""

    active: bool = False

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        return RiskOutcome(
            RiskCode.KILL_SWITCH,
            not self.active,
            (
                "Kill switch is uitgeschakeld."
                if not self.active
                else "Kill switch is actief; iedere order is geblokkeerd."
            ),
        )


@dataclass(frozen=True)
class MaxOrderValueRule:
    policy: RiskPolicy

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        approved = order.side is OrderSide.SELL or order.total_value <= self.policy.max_order_value
        return _outcome(
            RiskCode.MAX_ORDER_VALUE, approved,
            f"Kooporderwaarde €{order.total_value:.2f} overschrijdt limiet €{self.policy.max_order_value:.2f}.",
        )


@dataclass(frozen=True)
class MaxPositionValueRule:
    policy: RiskPolicy

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        position = context.portfolio.get_position(order.instrument.symbol)
        current_value = (position.quantity if position else 0) * context.price_for(order)
        projected = current_value + order.total_value
        approved = order.side is OrderSide.SELL or projected <= self.policy.max_position_value
        return _outcome(
            RiskCode.MAX_POSITION_VALUE, approved,
            f"Verwachte positiewaarde €{projected:.2f} overschrijdt limiet €{self.policy.max_position_value:.2f}.",
        )


@dataclass(frozen=True)
class MaxConcentrationRule:
    policy: RiskPolicy

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        position = context.portfolio.get_position(order.instrument.symbol)
        current_value = (position.quantity if position else 0) * context.price_for(order)
        projected = current_value + order.total_value
        concentration = projected / context.current_equity
        approved = order.side is OrderSide.SELL or concentration <= self.policy.max_concentration
        return _outcome(
            RiskCode.MAX_CONCENTRATION, approved,
            f"Verwachte concentratie {concentration:.2%} overschrijdt limiet {self.policy.max_concentration:.2%}.",
        )


@dataclass(frozen=True)
class CashReserveRule:
    policy: RiskPolicy

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        projected_cash = context.portfolio.cash_balance - order.total_value - context.fee
        minimum = context.current_equity * self.policy.min_cash_reserve
        approved = order.side is OrderSide.SELL or projected_cash >= minimum
        return _outcome(
            RiskCode.CASH_RESERVE, approved,
            f"Verwachte cash €{projected_cash:.2f} is lager dan reserve €{minimum:.2f}.",
        )


@dataclass(frozen=True)
class DailyLossRule:
    policy: RiskPolicy

    def evaluate(self, order: Order, context: RiskContext) -> RiskOutcome:
        loss = context.current_equity / context.day_start_equity - 1
        approved = order.side is OrderSide.SELL or loss > -self.policy.max_daily_loss
        return _outcome(
            RiskCode.DAILY_LOSS, approved,
            f"Dagresultaat {loss:.2%} bereikte verlieslimiet {-self.policy.max_daily_loss:.2%}.",
        )


def _outcome(code: RiskCode, approved: bool, rejection_reason: str) -> RiskOutcome:
    return RiskOutcome(
        code,
        approved,
        "Regel geslaagd." if approved else rejection_reason,
    )

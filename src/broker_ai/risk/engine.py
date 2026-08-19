"""Centrale risk engine die alle regels uitvoert en iedere uitkomst bewaart."""

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from uuid import UUID, uuid4

from broker_ai.domain import Order
from broker_ai.risk.models import (
    RiskAssessment,
    RiskCode,
    RiskContext,
    RiskOutcome,
    RiskPolicy,
)
from broker_ai.risk.rules import (
    CashReserveRule,
    DailyLossRule,
    KillSwitchRule,
    MaxConcentrationRule,
    MaxOrderValueRule,
    MaxPositionValueRule,
    RiskRule,
)


class RiskEngine:
    """Beoordeel orders onafhankelijk van strategie en uitvoerende broker."""

    def __init__(
        self,
        policy: RiskPolicy | None = None,
        *,
        kill_switch: KillSwitchRule | None = None,
        extra_rules: Iterable[RiskRule] = (),
        clock: Callable[[], datetime] | None = None,
        assessment_id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self.policy = policy or RiskPolicy()
        self.kill_switch = kill_switch or KillSwitchRule()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._assessment_id_factory = assessment_id_factory or uuid4
        self._rules: tuple[RiskRule, ...] = (
            self.kill_switch,
            MaxOrderValueRule(self.policy),
            MaxPositionValueRule(self.policy),
            MaxConcentrationRule(self.policy),
            CashReserveRule(self.policy),
            DailyLossRule(self.policy),
            *tuple(extra_rules),
        )
        self._audit_log: list[RiskAssessment] = []

    @property
    def audit_log(self) -> tuple[RiskAssessment, ...]:
        """Geef een onveranderlijke momentopname van alle risicobeslissingen."""

        return tuple(self._audit_log)

    def assess(self, order: Order, context: RiskContext) -> RiskAssessment:
        """Voer iedere regel uit; een technische regelfout wordt veilig afgewezen."""

        if not isinstance(order, Order):
            raise TypeError("Order moet een Order zijn.")
        if not isinstance(context, RiskContext):
            raise TypeError("Risicocontext moet een RiskContext zijn.")

        outcomes: list[RiskOutcome] = []
        for rule in self._rules:
            try:
                outcome = rule.evaluate(order, context)
                if not isinstance(outcome, RiskOutcome):
                    raise TypeError("Regel gaf geen RiskOutcome terug.")
            except Exception as exc:
                outcome = RiskOutcome(
                    RiskCode.RULE_ERROR,
                    False,
                    f"Risicoregel {type(rule).__name__} faalde veilig: {exc}",
                )
            outcomes.append(outcome)

        assessment_id = self._assessment_id_factory()
        evaluated_at = self._clock()
        self._validate_metadata(assessment_id, evaluated_at)
        assessment = RiskAssessment(
            assessment_id=assessment_id,
            order_id=order.order_id,
            approved=all(item.approved for item in outcomes),
            outcomes=tuple(outcomes),
            evaluated_at=evaluated_at,
        )
        self._audit_log.append(assessment)
        return assessment

    def _validate_metadata(self, assessment_id: UUID, evaluated_at: datetime) -> None:
        if not isinstance(assessment_id, UUID):
            raise TypeError("Risicobeoordeling-ID moet een UUID zijn.")
        if any(item.assessment_id == assessment_id for item in self._audit_log):
            raise ValueError(f"Dubbele risicobeoordeling-ID: {assessment_id}.")
        if not isinstance(evaluated_at, datetime):
            raise TypeError("Risicobeoordelingstijdstip moet een datetime zijn.")
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("Risicobeoordelingstijdstip moet een tijdzone bevatten.")

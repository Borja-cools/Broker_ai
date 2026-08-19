"""Verplichte risicopoort vóór toegang tot iedere brokeradapter."""

from typing import Protocol, runtime_checkable

from broker_ai.brokers import Execution
from broker_ai.brokers.interface import BrokerInterface
from broker_ai.brokers.models import BrokerOrder
from broker_ai.domain import Order, Portfolio
from broker_ai.risk.engine import RiskEngine
from broker_ai.risk.models import RiskAssessment, RiskContext


class RiskRejectedError(ValueError):
    """Afwijzing met de volledige, uitlegbare risicobeoordeling."""

    def __init__(self, assessment: RiskAssessment) -> None:
        self.assessment = assessment
        reasons = "; ".join(assessment.rejection_reasons)
        super().__init__(f"Order geweigerd door risk engine: {reasons}")


@runtime_checkable
class ExecutionBroker(Protocol):
    """Minimale brokergrens waarop later ook paper adapters kunnen aansluiten."""

    def execute(self, order: Order, portfolio: Portfolio) -> Execution: ...


class RiskManagedBroker:
    """De enige brokerpoort die applicatie- en backteststromen gebruiken."""

    def __init__(self, broker: ExecutionBroker, risk_engine: RiskEngine) -> None:
        if not isinstance(broker, ExecutionBroker):
            raise TypeError("Broker moet het ExecutionBroker-contract ondersteunen.")
        if not isinstance(risk_engine, RiskEngine):
            raise TypeError("Risk engine moet een RiskEngine zijn.")
        self._broker = broker
        self.risk_engine = risk_engine

    def execute(
        self,
        order: Order,
        portfolio: Portfolio,
        context: RiskContext,
    ) -> Execution:
        """Stop vóór de broker tenzij iedere risicoregel de order goedkeurt."""

        if context.portfolio is not portfolio:
            raise ValueError("Risicocontext hoort niet bij deze portefeuille.")
        assessment = self.risk_engine.assess(order, context)
        if not assessment.approved:
            raise RiskRejectedError(assessment)
        return self._broker.execute(order, portfolio)


class AsyncRiskManagedBroker:
    """Async risicopoort voor het stabiele Fase 4-brokercontract."""

    def __init__(self, broker: BrokerInterface, risk_engine: RiskEngine) -> None:
        if not isinstance(broker, BrokerInterface):
            raise TypeError("Broker moet het BrokerInterface-contract ondersteunen.")
        if not isinstance(risk_engine, RiskEngine):
            raise TypeError("Risk engine moet een RiskEngine zijn.")
        self._broker = broker
        self.risk_engine = risk_engine

    async def submit_order(self, order: Order, context: RiskContext) -> BrokerOrder:
        """Dien pas async in nadat alle bestaande risicoregels slagen."""

        assessment = self.risk_engine.assess(order, context)
        if not assessment.approved:
            raise RiskRejectedError(assessment)
        return await self._broker.submit_order(order)

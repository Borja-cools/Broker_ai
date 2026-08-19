"""Begeleide eerste Alpaca Paper-order met risicopoort en bevestiging."""

from collections.abc import Callable
from decimal import Decimal

from broker_ai.brokers.alpaca import AlpacaPaperBrokerAdapter
from broker_ai.brokers.interface import BrokerInterface
from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide, Portfolio
from broker_ai.risk import AsyncRiskManagedBroker, RiskContext, RiskEngine, RiskPolicy


CONFIRMATION = "PLAATS PAPER ORDER"
AAPL = Instrument("AAPL", "Apple Inc.", Exchange.NASDAQ, Currency.USD)


async def run_first_paper_order(
    adapter: BrokerInterface | None = None,
    *,
    ask: Callable[[str], str] = input,
) -> str:
    """Plaats maximaal één AAPL paper-limitorder na exacte bevestiging."""

    owned_adapter = adapter is None
    broker = adapter or AlpacaPaperBrokerAdapter.from_environment()
    try:
        account = await broker.get_account()
        if account.currency is not Currency.USD:
            raise ValueError("Het Alpaca Paper-account moet in USD staan.")
        if account.positions:
            raise ValueError(
                "De eerste-orderdemo werkt alleen met een leeg paper-account."
            )

        quote = await broker.get_market_price(AAPL)
        order = Order(AAPL, OrderSide.BUY, 1, quote.price)
        portfolio = Portfolio(account.cash_balance, Currency.USD)
        context = RiskContext(
            portfolio=portfolio,
            current_equity=account.cash_balance,
            day_start_equity=account.cash_balance,
            market_prices={AAPL.symbol: quote.price},
        )
        risk_engine = RiskEngine(
            RiskPolicy(
                max_order_value=Decimal("500.00"),
                max_position_value=Decimal("500.00"),
                max_concentration=Decimal("0.01"),
                min_cash_reserve=Decimal("0.50"),
                max_daily_loss=Decimal("0.01"),
            )
        )
        assessment = risk_engine.assess(order, context)
        if not assessment.approved:
            reasons = "; ".join(assessment.rejection_reasons)
            return f"PAPER-ORDER GEBLOKKEERD DOOR RISK ENGINE\n{reasons}"

        prompt = "\n".join(
            (
                "EERSTE ALPACA PAPER-ORDER",
                "Omgeving: PAPER — geen echt geld",
                "Instrument: AAPL (Apple)",
                "Aantal: 1 geheel aandeel",
                f"Limitprijs: USD {quote.price:.2f}",
                f"Maximale orderwaarde: USD {order.total_value:.2f}",
                "Risk engine: GOEDGEKEURD",
                f'Typ exact "{CONFIRMATION}" om te verzenden: ',
            )
        )
        if ask(prompt).strip() != CONFIRMATION:
            return "Paper-order geannuleerd; er is niets naar Alpaca gestuurd."

        # Beoordeel opnieuw vlak vóór verzending; geen pad om de risicopoort heen.
        gateway = AsyncRiskManagedBroker(broker, risk_engine)
        submitted = await gateway.submit_order(order, context)
        return "\n".join(
            (
                "PAPER-ORDER NAAR ALPACA VERZONDEN",
                f"Brokerorder-ID: {submitted.broker_order_id}",
                f"Status: {submitted.status.value}",
                "Controleer dezelfde order nu in het Alpaca Paper-dashboard.",
            )
        )
    finally:
        if owned_adapter and isinstance(broker, AlpacaPaperBrokerAdapter):
            await broker.close()

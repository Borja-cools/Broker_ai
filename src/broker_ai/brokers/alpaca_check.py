"""Veilige, uitsluitend-lezen controle van een Alpaca Paper-account."""

from broker_ai.brokers.alpaca import AlpacaPaperBrokerAdapter


async def run_alpaca_check() -> str:
    """Controleer verbinding en account zonder een order te plaatsen."""

    async with AlpacaPaperBrokerAdapter.from_environment() as adapter:
        status = await adapter.get_status()
        if status.connection.value != "connected":
            return f"Alpaca Paper: NIET VERBONDEN\n{status.message}"
        account = await adapter.get_account()
        return "\n".join(
            (
                "ALPACA PAPER — alleen-lezen controle",
                "Live orders: ONMOGELIJK IN DEZE ADAPTER",
                f"Cash: {account.currency.value} {account.cash_balance:.2f}",
                f"Open posities: {len(account.positions)}",
            )
        )

"""Synchroniseer Alpaca Paper als externe waarheid naar onze lokale database."""

from datetime import datetime, timezone
import os
from uuid import uuid4

from broker_ai.brokers.alpaca import AlpacaPaperBrokerAdapter
from broker_ai.server.database import Database


async def sync_alpaca_paper(
    adapter: AlpacaPaperBrokerAdapter | None = None,
    database: Database | None = None,
) -> dict[str, object]:
    """Upsert orders en vervang de actuele posities in één database-transactie."""

    owned_adapter = adapter is None
    broker = adapter or AlpacaPaperBrokerAdapter.from_environment()
    store = database or Database(os.getenv("BROKER_AI_DATABASE_PATH", "data/broker_ai.db"))
    store.migrate()
    started_at = _now()
    run_id = str(uuid4())
    try:
        account = await broker.get_account()
        orders = await broker.get_recent_order_snapshots()
        synced_at = _now()
        connection = store.connect()
        try:
            connection.execute("BEGIN")
            for order in orders:
                connection.execute(
                    """
                    INSERT INTO broker_orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(broker_order_id) DO UPDATE SET
                     client_order_id=excluded.client_order_id,
                     filled_quantity=excluded.filled_quantity,
                     average_fill_price=excluded.average_fill_price,
                     status=excluded.status, updated_at=excluded.updated_at,
                     synced_at=excluded.synced_at
                    """,
                    (
                        str(order.broker_order_id), "alpaca", "paper",
                        order.client_order_id, order.symbol, order.side,
                        order.order_type, str(order.quantity),
                        str(order.filled_quantity),
                        str(order.limit_price) if order.limit_price is not None else None,
                        str(order.average_fill_price)
                        if order.average_fill_price is not None else None,
                        order.status, order.submitted_at.isoformat(),
                        order.updated_at.isoformat(), synced_at,
                    ),
                )
            connection.execute(
                "DELETE FROM broker_positions WHERE broker = ? AND environment = ?",
                ("alpaca", "paper"),
            )
            for position in account.positions:
                connection.execute(
                    "INSERT INTO broker_positions VALUES(?,?,?,?,?,?)",
                    (
                        "alpaca", "paper", position.symbol, str(position.quantity),
                        str(position.average_price), synced_at,
                    ),
                )
            connection.execute(
                "INSERT INTO broker_sync_runs VALUES(?,?,?,?,?,?,?,?)",
                (
                    run_id, "alpaca", "paper", len(orders), len(account.positions),
                    started_at, synced_at, "completed",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if store.path != ":memory:":
                connection.close()

        store.audit(
            "broker.sync.completed",
            None,
            run_id,
            {
                "broker": "alpaca", "environment": "paper",
                "orders_seen": len(orders), "positions_seen": len(account.positions),
            },
        )
        return {
            "run_id": run_id,
            "orders_seen": len(orders),
            "positions_seen": len(account.positions),
            "cash_balance": str(account.cash_balance),
            "currency": account.currency.value,
            "completed_at": synced_at,
        }
    finally:
        if owned_adapter:
            await broker.close()


async def run_alpaca_sync() -> str:
    result = await sync_alpaca_paper()
    return "\n".join(
        (
            "ALPACA PAPER-SYNCHRONISATIE VOLTOOID",
            f"Orders bijgewerkt: {result['orders_seen']}",
            f"Actuele posities: {result['positions_seen']}",
            f"Cash: {result['currency']} {result['cash_balance']}",
            f"Sync-ID: {result['run_id']}",
        )
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

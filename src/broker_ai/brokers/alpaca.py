"""Strikt paper-only adapter voor Alpaca's Trading API."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import os
from typing import Any
from uuid import UUID

import httpx

from broker_ai.brokers.interface import (
    BrokerError,
    BrokerIdempotencyConflictError,
    BrokerOrderNotFoundError,
    BrokerTransientError,
    BrokerUnavailableError,
)
from broker_ai.brokers.models import (
    AccountSnapshot,
    BrokerMode,
    BrokerOrder,
    BrokerOrderStatus,
    BrokerStatus,
    ConnectionState,
    PositionSnapshot,
)
from broker_ai.brokers.simulated import Execution, ExecutionStatus
from broker_ai.domain import Currency, Instrument, MarketPrice, Order, OrderSide, Transaction


PAPER_TRADING_URL = "https://paper-api.alpaca.markets"
MARKET_DATA_URL = "https://data.alpaca.markets"


@dataclass(frozen=True)
class AlpacaOrderSnapshot:
    broker_order_id: UUID
    client_order_id: str | None
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    limit_price: Decimal | None
    average_fill_price: Decimal | None
    status: str
    submitted_at: datetime
    updated_at: datetime


class AlpacaPaperBrokerAdapter:
    """Vertaal ons brokercontract naar Alpaca zonder live endpoint toe te staan."""

    def __init__(
        self,
        api_key_id: str,
        api_secret_key: str,
        *,
        trading_base_url: str = PAPER_TRADING_URL,
        data_base_url: str = MARKET_DATA_URL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key_id.strip() or not api_secret_key.strip():
            raise ValueError("Alpaca paper key en secret zijn verplicht.")
        if trading_base_url.rstrip("/") != PAPER_TRADING_URL:
            raise ValueError("Deze adapter accepteert uitsluitend Alpaca Paper Trading.")

        self._headers = {
            "APCA-API-KEY-ID": api_key_id,
            "APCA-API-SECRET-KEY": api_secret_key,
        }
        self._trading_url = PAPER_TRADING_URL
        self._data_url = data_base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = client is None
        self._orders: dict[UUID, Order] = {}
        self._broker_id_by_client_id: dict[UUID, UUID] = {}

    @classmethod
    def from_environment(cls) -> "AlpacaPaperBrokerAdapter":
        """Bouw de adapter met paper-credentials die nooit in broncode staan."""

        key_id = os.getenv("ALPACA_API_KEY_ID", "")
        secret = os.getenv("ALPACA_API_SECRET_KEY", "")
        base_url = os.getenv("ALPACA_TRADING_BASE_URL", PAPER_TRADING_URL)
        return cls(key_id, secret, trading_base_url=base_url)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AlpacaPaperBrokerAdapter":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def get_status(self) -> BrokerStatus:
        try:
            await self._request("GET", f"{self._trading_url}/v2/account")
        except BrokerError as exc:
            return BrokerStatus(
                BrokerMode.PAPER,
                ConnectionState.DISCONNECTED,
                self._now(),
                f"Alpaca Paper niet beschikbaar: {exc}",
            )
        return BrokerStatus(
            BrokerMode.PAPER,
            ConnectionState.CONNECTED,
            self._now(),
            "Verbonden met Alpaca Paper Trading.",
        )

    async def get_market_price(self, instrument: Instrument) -> MarketPrice:
        self._require_usd(instrument)
        payload = await self._request(
            "GET",
            f"{self._data_url}/v2/stocks/{instrument.symbol}/trades/latest",
            params={"feed": "iex"},
        )
        trade = payload.get("trade", {})
        try:
            price = Decimal(str(trade["p"]))
            observed_at = self._parse_time(trade["t"])
        except (KeyError, TypeError, InvalidOperation, ValueError) as exc:
            raise BrokerError("Ongeldig marktdata-antwoord van Alpaca.") from exc
        return MarketPrice(instrument, price, observed_at)

    async def get_account(self) -> AccountSnapshot:
        account = await self._request("GET", f"{self._trading_url}/v2/account")
        positions_payload = await self._request("GET", f"{self._trading_url}/v2/positions")
        if not isinstance(positions_payload, list):
            raise BrokerError("Ongeldig positieantwoord van Alpaca.")

        positions: list[PositionSnapshot] = []
        for item in positions_payload:
            quantity = self._whole_number(item.get("qty"), "positieaantal")
            positions.append(
                PositionSnapshot(
                    str(item["symbol"]).strip().upper(),
                    quantity,
                    self._decimal(item.get("avg_entry_price"), "gemiddelde prijs"),
                )
            )
        return AccountSnapshot(
            self._decimal(account.get("cash"), "cashsaldo"),
            Currency.USD,
            tuple(positions),
            self._now(),
        )

    async def submit_order(self, order: Order) -> BrokerOrder:
        self._require_usd(order.instrument)
        existing_id = self._broker_id_by_client_id.get(order.order_id)
        if existing_id is not None:
            if self._orders[existing_id] != order:
                raise BrokerIdempotencyConflictError(
                    f"Client-order-ID {order.order_id} hoort al bij andere orderinhoud."
                )
            return await self.get_order(existing_id)
        payload = await self._request(
            "POST",
            f"{self._trading_url}/v2/orders",
            json={
                "symbol": order.instrument.symbol,
                "qty": str(order.quantity),
                "side": order.side.value,
                "type": "limit",
                "time_in_force": "day",
                "limit_price": str(order.price),
                "client_order_id": str(order.order_id),
            },
        )
        result = self._to_broker_order(payload, order)
        self._orders[result.broker_order_id] = order
        self._broker_id_by_client_id[order.order_id] = result.broker_order_id
        return result

    async def get_order(self, order_id: UUID) -> BrokerOrder:
        order = self._orders.get(order_id)
        if order is None:
            raise BrokerOrderNotFoundError(
                "Order is niet door deze actieve Broker AI-sessie ingediend."
            )
        payload = await self._request("GET", f"{self._trading_url}/v2/orders/{order_id}")
        return self._to_broker_order(payload, order)

    async def cancel_order(self, order_id: UUID) -> BrokerOrder:
        order = self._orders.get(order_id)
        if order is None:
            raise BrokerOrderNotFoundError(f"Alpaca-order {order_id} is lokaal onbekend.")
        await self._request("DELETE", f"{self._trading_url}/v2/orders/{order_id}", empty_ok=True)
        return await self.get_order(order_id)

    async def reconcile_orders(self) -> tuple[BrokerOrder, ...]:
        results = []
        for order_id in tuple(self._orders):
            results.append(await self.get_order(order_id))
        return tuple(results)

    async def get_recent_order_snapshots(self) -> tuple[AlpacaOrderSnapshot, ...]:
        """Lees recente paper-orders, ook uit eerdere Broker AI-processen."""

        payload = await self._request(
            "GET",
            f"{self._trading_url}/v2/orders",
            params={"status": "all", "limit": "100", "direction": "desc"},
        )
        if not isinstance(payload, list):
            raise BrokerError("Ongeldig orderlijstantwoord van Alpaca.")
        snapshots = []
        for item in payload:
            try:
                snapshots.append(
                    AlpacaOrderSnapshot(
                        broker_order_id=UUID(str(item["id"])),
                        client_order_id=item.get("client_order_id"),
                        symbol=str(item["symbol"]).strip().upper(),
                        side=str(item["side"]),
                        order_type=str(item["type"]),
                        quantity=self._decimal(item["qty"], "orderaantal"),
                        filled_quantity=self._decimal(
                            item.get("filled_qty", "0"), "uitgevoerd aantal"
                        ),
                        limit_price=self._optional_decimal(item.get("limit_price")),
                        average_fill_price=self._optional_decimal(
                            item.get("filled_avg_price")
                        ),
                        status=str(item["status"]),
                        submitted_at=self._parse_time(item["submitted_at"]),
                        updated_at=self._parse_time(
                            item.get("updated_at") or item["submitted_at"]
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise BrokerError("Ongeldige order in Alpaca-orderlijst.") from exc
        return tuple(snapshots)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
        empty_ok: bool = False,
    ) -> Any:
        try:
            response = await self._client.request(
                method, url, headers=self._headers, params=params, json=json
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise BrokerTransientError(f"Tijdelijke Alpaca-netwerkfout: {exc}") from exc

        if response.status_code == 404:
            raise BrokerOrderNotFoundError("De gevraagde Alpaca-resource bestaat niet.")
        if response.status_code in {429, 500, 502, 503, 504}:
            raise BrokerTransientError(
                f"Alpaca antwoordde tijdelijk met HTTP {response.status_code}."
            )
        if response.status_code in {401, 403}:
            raise BrokerUnavailableError("Alpaca paper-inloggegevens zijn ongeldig of geweigerd.")
        if response.is_error:
            message = response.text[:300] or "onbekende brokerfout"
            raise BrokerError(f"Alpaca weigerde het verzoek ({response.status_code}): {message}")
        if empty_ok and not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise BrokerError("Alpaca stuurde geen geldig JSON-antwoord.") from exc

    def _to_broker_order(self, payload: dict[str, Any], order: Order) -> BrokerOrder:
        try:
            broker_id = UUID(str(payload["id"]))
            status = self._map_status(str(payload["status"]))
            submitted_at = self._parse_time(payload["submitted_at"])
            updated_at = self._parse_time(payload.get("updated_at") or payload["submitted_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BrokerError("Ongeldig orderantwoord van Alpaca.") from exc

        execution = None
        if status is BrokerOrderStatus.FILLED:
            filled_quantity = self._whole_number(payload.get("filled_qty"), "uitgevoerd aantal")
            if filled_quantity != order.quantity:
                raise BrokerError("Een als gevuld gemelde Alpaca-order is niet volledig uitgevoerd.")
            fill_price = self._decimal(payload.get("filled_avg_price"), "uitvoeringsprijs")
            executed_at = self._parse_time(payload.get("filled_at") or payload["updated_at"])
            gross = fill_price * filled_quantity
            cash_change = -gross if order.side is OrderSide.BUY else gross
            execution = Execution(
                order,
                ExecutionStatus.FILLED,
                Transaction(
                    broker_id,
                    order.order_id,
                    order.instrument,
                    order.side,
                    filled_quantity,
                    fill_price,
                    gross,
                    Decimal("0"),
                    cash_change,
                    Decimal("0"),
                    executed_at,
                ),
            )
        return BrokerOrder(
            broker_id,
            order,
            status,
            submitted_at,
            updated_at,
            execution,
            f"Alpaca Paper-status: {payload.get('status', 'onbekend')}",
        )

    @staticmethod
    def _map_status(value: str) -> BrokerOrderStatus:
        if value == "filled":
            return BrokerOrderStatus.FILLED
        if value in {"canceled", "expired", "replaced"}:
            return BrokerOrderStatus.CANCELLED
        if value in {"rejected", "suspended"}:
            return BrokerOrderStatus.REJECTED
        return BrokerOrderStatus.SUBMITTED

    @staticmethod
    def _require_usd(instrument: Instrument) -> None:
        if instrument.currency is not Currency.USD:
            raise BrokerError("Alpaca-adapter accepteert momenteel alleen USD-instrumenten.")

    @staticmethod
    def _decimal(value: object, name: str) -> Decimal:
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise BrokerError(f"Ongeldige {name} in Alpaca-antwoord.") from exc
        if not result.is_finite():
            raise BrokerError(f"Niet-eindige {name} in Alpaca-antwoord.")
        return result

    @classmethod
    def _whole_number(cls, value: object, name: str) -> int:
        number = cls._decimal(value, name)
        if number != number.to_integral_value() or number <= 0:
            raise BrokerError(f"{name.capitalize()} moet voorlopig een positief geheel getal zijn.")
        return int(number)

    @classmethod
    def _optional_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return cls._decimal(value, "optioneel bedrag")

    @staticmethod
    def _parse_time(value: object) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Tijdstip ontbreekt.")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Tijdstip mist tijdzone.")
        return parsed

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

"""FastAPI-applicatie als veilige bron van waarheid voor toekomstige clients."""

from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import logging
import os
from pathlib import Path
import secrets
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from broker_ai import __version__
from broker_ai.server.database import Database
from broker_ai.server.schemas import ApprovalMode, BotCreate, DecisionCreate, ProposalCreate
from broker_ai.server.sync_worker import BrokerSyncWorker


LOGGER = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        requests = self._requests[key]
        while requests and requests[0] <= now - self.window:
            requests.popleft()
        if len(requests) >= self.limit:
            raise HTTPException(status_code=429, detail="Te veel API-verzoeken; probeer later opnieuw.")
        requests.append(now)


def create_app(
    database_path: str | Path | None = None,
    api_token: str | None = None,
    *,
    rate_limit: int = 60,
    sync_enabled: bool | None = None,
    sync_interval_seconds: int | None = None,
) -> FastAPI:
    token = api_token or os.getenv("BROKER_AI_API_TOKEN")
    if not token or len(token) < 32:
        raise RuntimeError("BROKER_AI_API_TOKEN moet minimaal 32 tekens bevatten.")
    database = Database(database_path or os.getenv("BROKER_AI_DATABASE_PATH", "data/broker_ai.db"))
    limiter = RateLimiter(rate_limit)
    bearer_scheme = HTTPBearer(auto_error=False)
    counters = {"requests": 0, "errors": 0}
    automatic_sync = (
        _environment_bool("BROKER_AI_ALPACA_SYNC_ENABLED", False)
        if sync_enabled is None else sync_enabled
    )
    interval = sync_interval_seconds or int(
        os.getenv("BROKER_AI_ALPACA_SYNC_INTERVAL_SECONDS", "300")
    )

    async def sync_operation() -> dict[str, object]:
        from broker_ai.brokers.alpaca_sync import sync_alpaca_paper

        return await sync_alpaca_paper(database=database)

    sync_worker = BrokerSyncWorker(sync_operation, interval)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.migrate()
        app.state.admin = database.seed_admin(token)
        if automatic_sync:
            sync_worker.start()
        try:
            yield
        finally:
            await sync_worker.stop()

    app = FastAPI(
        title="Broker AI API",
        version=__version__,
        description="Lokale, simulation-first API voor dashboard en mobiele app.",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.sync_worker = sync_worker

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started = time.monotonic()
        counters["requests"] += 1
        try:
            response = await call_next(request)
            if response.status_code >= 400:
                counters["errors"] += 1
        except Exception:
            counters["errors"] += 1
            raise
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(json.dumps({
            "event": "http_request", "request_id": request_id,
            "method": request.method, "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
        }))
        return response

    def current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict:
        client_host = request.client.host if request.client else "unknown"
        limiter.check(f"auth:{client_host}")
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Bearer-token ontbreekt.")
        supplied = credentials.credentials.strip()
        supplied_hash = hashlib.sha256(supplied.encode()).hexdigest()
        user = next(
            (
                candidate
                for candidate in database.fetchall("SELECT * FROM users")
                if secrets.compare_digest(supplied_hash, candidate["token_hash"])
            ),
            None,
        )
        if not user:
            raise HTTPException(status_code=401, detail="Ongeldig API-token.")
        return user

    def require_admin(user: dict = Depends(current_user)) -> dict:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Beheerdersrechten vereist.")
        return user

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok" if database.healthy() else "error", "mode": "simulation"}

    @app.get("/metrics", response_class=PlainTextResponse, tags=["system"])
    def metrics(user: dict = Depends(current_user)) -> str:
        return (
            f"broker_ai_http_requests_total {counters['requests']}\n"
            f"broker_ai_http_errors_total {counters['errors']}\n"
        )

    @app.get("/api/v1/status", tags=["system"])
    def api_status(user: dict = Depends(current_user)) -> dict:
        return {"version": __version__, "mode": "simulation", "live_trading": False}

    @app.post("/api/v1/bots", status_code=201, tags=["bots"])
    def create_bot(payload: BotCreate, user: dict = Depends(require_admin)) -> dict:
        bot_id, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
        try:
            database.execute(
                "INSERT INTO bots VALUES(?,?,?,?,?,?,?)",
                (bot_id, payload.name, payload.specialization, payload.approval_mode.value,
                 "active", str(payload.max_auto_order_value), now),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise HTTPException(status_code=409, detail="Botnaam bestaat al.") from exc
            raise
        database.audit("bot.created", user["id"], bot_id, payload.model_dump(mode="json"))
        return database.fetchone("SELECT * FROM bots WHERE id = ?", (bot_id,))

    @app.get("/api/v1/bots", tags=["bots"])
    def list_bots(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM bots ORDER BY created_at")

    @app.post("/api/v1/order-proposals", status_code=201, tags=["orders"])
    def propose(payload: ProposalCreate, user: dict = Depends(require_admin)) -> dict:
        bot = database.fetchone("SELECT * FROM bots WHERE id = ?", (payload.bot_id,))
        if not bot:
            raise HTTPException(status_code=404, detail="Bot bestaat niet.")
        value = payload.quantity * payload.price
        if bot["status"] != "active" or bot["approval_mode"] == ApprovalMode.DISABLED.value:
            proposal_status = "rejected"
        elif (
            bot["approval_mode"] == ApprovalMode.AUTOMATIC_LIMITED.value
            and value <= Decimal(bot["max_auto_order_value"])
        ):
            proposal_status = "auto_approved"
        else:
            proposal_status = "pending_approval"
        proposal_id, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
        database.execute(
            "INSERT INTO order_proposals VALUES(?,?,?,?,?,?,?,?,?,?)",
            (proposal_id, payload.bot_id, payload.symbol.upper(), payload.side,
             str(payload.quantity), str(payload.price), payload.rationale,
             proposal_status, now, None),
        )
        database.audit("proposal.created", user["id"], proposal_id, {
            "status": proposal_status, "order_value": str(value), "bot_id": payload.bot_id,
        })
        return database.fetchone("SELECT * FROM order_proposals WHERE id = ?", (proposal_id,))

    @app.get("/api/v1/order-proposals", tags=["orders"])
    def list_proposals(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM order_proposals ORDER BY created_at DESC")

    @app.post("/api/v1/order-proposals/{proposal_id}/decision", tags=["orders"])
    def decide(proposal_id: str, payload: DecisionCreate, user: dict = Depends(require_admin)) -> dict:
        proposal = database.fetchone("SELECT * FROM order_proposals WHERE id = ?", (proposal_id,))
        if not proposal:
            raise HTTPException(status_code=404, detail="Voorstel bestaat niet.")
        if proposal["status"] != "pending_approval":
            raise HTTPException(status_code=409, detail="Voorstel wacht niet op goedkeuring.")
        new_status = "approved" if payload.decision == "approve" else "rejected"
        reviewed_at = datetime.now(timezone.utc).isoformat()
        database.execute(
            "UPDATE order_proposals SET status = ?, reviewed_at = ? WHERE id = ?",
            (new_status, reviewed_at, proposal_id),
        )
        database.audit(f"proposal.{new_status}", user["id"], proposal_id, {})
        return database.fetchone("SELECT * FROM order_proposals WHERE id = ?", (proposal_id,))

    @app.get("/api/v1/audit-logs", tags=["audit"])
    def audit_logs(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100")

    @app.get("/api/v1/portfolio-snapshots", tags=["portfolio"])
    def snapshots(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM portfolio_snapshots ORDER BY observed_at DESC")

    @app.get("/api/v1/analyses", tags=["analysis"])
    def analyses(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM analyses ORDER BY created_at DESC")

    @app.get("/api/v1/broker-orders", tags=["broker"])
    def broker_orders(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall(
            "SELECT * FROM broker_orders ORDER BY submitted_at DESC LIMIT 100"
        )

    @app.get("/api/v1/broker-positions", tags=["broker"])
    def broker_positions(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall("SELECT * FROM broker_positions ORDER BY symbol")

    @app.get("/api/v1/broker-sync-runs", tags=["broker"])
    def broker_sync_runs(user: dict = Depends(current_user)) -> list[dict]:
        return database.fetchall(
            "SELECT * FROM broker_sync_runs ORDER BY completed_at DESC LIMIT 100"
        )

    @app.get("/api/v1/broker-sync-status", tags=["broker"])
    def broker_sync_status(user: dict = Depends(current_user)) -> dict:
        return sync_worker.status(enabled=automatic_sync)

    return app


def _environment_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise RuntimeError(f"{name} moet true of false zijn, niet {raw!r}.")

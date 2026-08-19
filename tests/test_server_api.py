"""End-to-endtests voor authenticatie, bots en ordervoorstellen."""

from pathlib import Path
import hashlib
import tempfile
import unittest

from fastapi.testclient import TestClient

from broker_ai.server import create_app


TOKEN = "local-test-token-with-32-characters"


class ServerApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "broker_ai.db"
        self.client_context = TestClient(create_app(self.database_path, TOKEN))
        self.client = self.client_context.__enter__()
        self.headers = {"Authorization": f"Bearer {TOKEN}"}

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temporary.cleanup()

    def create_bot(self, mode: str = "manual") -> dict:
        response = self.client.post(
            "/api/v1/bots",
            headers=self.headers,
            json={
                "name": f"{mode}-bot",
                "specialization": "Bitcoin momentum",
                "approval_mode": mode,
                "max_auto_order_value": "50",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def propose(self, bot_id: str, quantity: str = "0.1"):
        return self.client.post(
            "/api/v1/order-proposals",
            headers=self.headers,
            json={
                "bot_id": bot_id,
                "symbol": "BTC",
                "side": "buy",
                "quantity": quantity,
                "price": "100",
                "rationale": "Getest lokaal momentumvoorstel.",
            },
        )

    def test_health_and_openapi_are_public(self) -> None:
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        openapi = self.client.get("/openapi.json")
        self.assertEqual(openapi.status_code, 200)
        self.assertEqual(
            openapi.json()["components"]["securitySchemes"]["HTTPBearer"]["scheme"],
            "bearer",
        )

    def test_protected_endpoint_requires_valid_bearer_token(self) -> None:
        self.assertEqual(self.client.get("/api/v1/status").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/v1/status",
                headers={"Authorization": "Bearer wrong-token-value"},
            ).status_code,
            401,
        )
        self.assertEqual(self.client.get("/api/v1/status", headers=self.headers).status_code, 200)

    def test_viewer_can_read_but_cannot_create_bot(self) -> None:
        viewer_token = "viewer-test-token-with-32-characters"
        self.client.app.state.database.execute(
            "INSERT INTO users VALUES(?,?,?,?,?)",
            ("viewer-id", "viewer", hashlib.sha256(viewer_token.encode()).hexdigest(),
             "viewer", "2026-01-01T00:00:00+00:00"),
        )
        headers = {"Authorization": f"Bearer {viewer_token}"}
        self.assertEqual(self.client.get("/api/v1/bots", headers=headers).status_code, 200)
        response = self.client.post(
            "/api/v1/bots",
            headers=headers,
            json={"name": "No access", "specialization": "Test"},
        )
        self.assertEqual(response.status_code, 403)

    def test_manual_bot_creates_pending_proposal_and_decision(self) -> None:
        bot = self.create_bot("manual")
        proposal = self.propose(bot["id"])
        self.assertEqual(proposal.status_code, 201)
        self.assertEqual(proposal.json()["status"], "pending_approval")

        decision = self.client.post(
            f"/api/v1/order-proposals/{proposal.json()['id']}/decision",
            headers=self.headers,
            json={"decision": "approve"},
        )
        self.assertEqual(decision.json()["status"], "approved")

    def test_small_automatic_order_is_auto_approved(self) -> None:
        bot = self.create_bot("automatic_limited")
        self.assertEqual(self.propose(bot["id"]).json()["status"], "auto_approved")

    def test_large_automatic_order_falls_back_to_manual(self) -> None:
        bot = self.create_bot("automatic_limited")
        self.assertEqual(
            self.propose(bot["id"], quantity="1").json()["status"],
            "pending_approval",
        )

    def test_disabled_bot_rejects_proposal(self) -> None:
        bot = self.create_bot("disabled")
        self.assertEqual(self.propose(bot["id"]).json()["status"], "rejected")

    def test_invalid_financial_input_is_rejected(self) -> None:
        bot = self.create_bot("manual")
        self.assertEqual(self.propose(bot["id"], quantity="-1").status_code, 422)

    def test_actions_are_written_to_audit_log(self) -> None:
        bot = self.create_bot("manual")
        self.propose(bot["id"])
        logs = self.client.get("/api/v1/audit-logs", headers=self.headers).json()
        self.assertEqual({item["event_type"] for item in logs}, {"bot.created", "proposal.created"})

    def test_required_tables_are_migrated(self) -> None:
        database = self.client.app.state.database
        names = {
            row["name"] for row in database.fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({
            "users", "bots", "portfolio_snapshots", "analyses",
            "order_proposals", "audit_logs", "schema_migrations",
            "broker_orders", "broker_positions", "broker_sync_runs",
        }.issubset(names))

    def test_broker_sync_data_is_available_read_only(self) -> None:
        database = self.client.app.state.database
        database.execute(
            "INSERT INTO broker_sync_runs VALUES(?,?,?,?,?,?,?,?)",
            ("sync-1", "alpaca", "paper", 1, 1, "start", "end", "completed"),
        )
        response = self.client.get("/api/v1/broker-sync-runs", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["environment"], "paper")

    def test_automatic_sync_is_disabled_by_default(self) -> None:
        response = self.client.get("/api/v1/broker-sync-status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["enabled"])
        self.assertTrue(response.json()["paper_only"])

    def test_database_backup_contains_persisted_bot(self) -> None:
        self.create_bot("manual")
        backup_path = Path(self.temporary.name) / "backups" / "copy.db"
        self.client.app.state.database.backup(backup_path)

        from broker_ai.server.database import Database

        backup = Database(backup_path)
        self.assertEqual(len(backup.fetchall("SELECT * FROM bots")), 1)


class RateLimitTest(unittest.TestCase):
    def test_authenticated_rate_limit_is_enforced(self) -> None:
        with TestClient(create_app(":memory:", TOKEN, rate_limit=2)) as client:
            headers = {"Authorization": f"Bearer {TOKEN}"}
            self.assertEqual(client.get("/api/v1/status", headers=headers).status_code, 200)
            self.assertEqual(client.get("/api/v1/status", headers=headers).status_code, 200)
            self.assertEqual(client.get("/api/v1/status", headers=headers).status_code, 429)


if __name__ == "__main__":
    unittest.main()

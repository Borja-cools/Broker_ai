"""Tests voor begrensde automatische brokersynchronisatie."""

import asyncio
import unittest

from broker_ai.server.sync_worker import BrokerSyncWorker


class BrokerSyncWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_interval_below_one_minute(self) -> None:
        async def operation():
            return {}

        with self.assertRaisesRegex(ValueError, "60 seconden"):
            BrokerSyncWorker(operation, 59)

    async def test_success_updates_observable_status(self) -> None:
        async def operation():
            return {"orders_seen": 1}

        worker = BrokerSyncWorker(operation, 60)
        result = await worker.run_once()
        status = worker.status(enabled=True)

        self.assertEqual(result["orders_seen"], 1)
        self.assertEqual(status["runs_completed"], 1)
        self.assertEqual(status["consecutive_failures"], 0)
        self.assertIsNotNone(status["last_success_at"])

    async def test_failure_is_recorded_without_crashing_worker(self) -> None:
        async def operation():
            raise RuntimeError("tijdelijke teststoring")

        worker = BrokerSyncWorker(operation, 60)
        result = await worker.run_once()
        status = worker.status(enabled=True)

        self.assertIsNone(result)
        self.assertEqual(status["consecutive_failures"], 1)
        self.assertIn("tijdelijke teststoring", status["last_error"])

    async def test_overlapping_run_is_skipped(self) -> None:
        release = asyncio.Event()

        async def operation():
            await release.wait()
            return {}

        worker = BrokerSyncWorker(operation, 60)
        first = asyncio.create_task(worker.run_once())
        await asyncio.sleep(0)
        self.assertIsNone(await worker.run_once())
        release.set()
        await first


if __name__ == "__main__":
    unittest.main()

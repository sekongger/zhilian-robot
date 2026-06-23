import unittest

from fastapi import HTTPException

from api import graph_routes


class CrawlerOctopusFullApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._orig_create_task = graph_routes.asyncio.create_task
        self._orig_run_once_sync = graph_routes._run_crawler_once_sync
        self._orig_run_retry_sync = graph_routes._run_crawler_retry_ingest_failed_sync
        def _drop_task(coro):  # type: ignore[no-untyped-def]
            coro.close()
            return None
        graph_routes.asyncio.create_task = _drop_task  # type: ignore[assignment]

    async def asyncTearDown(self) -> None:
        graph_routes.asyncio.create_task = self._orig_create_task  # type: ignore[assignment]
        graph_routes._run_crawler_once_sync = self._orig_run_once_sync  # type: ignore[assignment]
        graph_routes._run_crawler_retry_ingest_failed_sync = self._orig_run_retry_sync  # type: ignore[assignment]

    async def test_run_octopus_full_rejects_invalid_limits(self) -> None:
        req = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=0,
            since_hours=24,
            process_limit=100,
        )
        with self.assertRaises(HTTPException) as ctx:
            await graph_routes.crawler_run_octopus_full(req)
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_run_octopus_full_accepts_large_limit(self) -> None:
        req = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=117,
            since_hours=24,
            process_limit=100,
            rebuild_storylines=False,
        )
        result = await graph_routes.crawler_run_octopus_full(req)
        self.assertEqual(result.get("status"), "accepted")

    async def test_run_octopus_full_rejects_invalid_ingest_retry_limit(self) -> None:
        req = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=24,
            process_limit=100,
            ingest_retry_limit=999,
        )
        with self.assertRaises(HTTPException) as ctx:
            await graph_routes.crawler_run_octopus_full(req)
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_run_octopus_full_returns_run_id(self) -> None:
        req = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=1,
            process_limit=1,
            rebuild_storylines=False,
        )
        result = await graph_routes.crawler_run_octopus_full(req)
        self.assertEqual(result.get("status"), "accepted")
        self.assertTrue(str(result.get("run_id", "")).startswith("octopus_full_"))

    async def test_full_run_query_not_found(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await graph_routes.crawler_get_full_run("not_exists")
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_ingest_stage_marks_failed_when_all_failed(self) -> None:
        run_id = "octopus_full_test_failed"
        request = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=1,
            process_limit=1,
            rebuild_storylines=False,
        )
        state = graph_routes._new_full_run_state(run_id, request)
        await graph_routes._save_full_run_state(state)

        def _fake_run_once(req):  # type: ignore[no-untyped-def]
            return {
                "fetch": {"total": 0, "inserted": 0, "touched": 0},
                "compress": {"compressed": 0, "failed": 0, "total": 0},
                "ingest": {"ingested": 0, "failed": 3, "total": 3},
            }

        def _fake_retry(*, process_limit: int, force_ingest: bool):  # type: ignore[no-untyped-def]
            return {"ingest_retry": {"ingested": 0, "failed": 0, "total": 0}}

        graph_routes._run_crawler_once_sync = _fake_run_once  # type: ignore[assignment]
        graph_routes._run_crawler_retry_ingest_failed_sync = _fake_retry  # type: ignore[assignment]
        await graph_routes._execute_octopus_full_run(run_id, request)

        saved = await graph_routes._load_full_run_state(run_id)
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["stages"]["ingest"]["status"], "failed")

    async def test_ingest_stage_marks_partial_success(self) -> None:
        run_id = "octopus_full_test_partial"
        request = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=1,
            process_limit=1,
            rebuild_storylines=False,
        )
        state = graph_routes._new_full_run_state(run_id, request)
        await graph_routes._save_full_run_state(state)

        def _fake_run_once(req):  # type: ignore[no-untyped-def]
            return {
                "fetch": {"total": 1, "inserted": 1, "touched": 1},
                "compress": {"compressed": 1, "failed": 0, "total": 1},
                "ingest": {"ingested": 2, "failed": 1, "total": 3},
            }

        def _fake_retry(*, process_limit: int, force_ingest: bool):  # type: ignore[no-untyped-def]
            return {"ingest_retry": {"ingested": 0, "failed": 0, "total": 0}}

        graph_routes._run_crawler_once_sync = _fake_run_once  # type: ignore[assignment]
        graph_routes._run_crawler_retry_ingest_failed_sync = _fake_retry  # type: ignore[assignment]
        await graph_routes._execute_octopus_full_run(run_id, request)

        saved = await graph_routes._load_full_run_state(run_id)
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["stages"]["ingest"]["status"], "partial_success")

    async def test_full_run_merges_primary_and_retry_ingest_details(self) -> None:
        run_id = "octopus_full_test_merge"
        request = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=1,
            process_limit=1,
            rebuild_storylines=False,
        )
        state = graph_routes._new_full_run_state(run_id, request)
        await graph_routes._save_full_run_state(state)

        def _fake_run_once(req):  # type: ignore[no-untyped-def]
            return {
                "fetch": {"total": 1, "inserted": 0, "touched": 1},
                "compress": {"compressed": 0, "failed": 0, "total": 0},
                "ingest": {"ingested": 0, "failed": 0, "total": 0},
            }

        def _fake_retry(*, process_limit: int, force_ingest: bool):  # type: ignore[no-untyped-def]
            return {
                "ingest_retry": {"ingested": 2, "failed": 1, "total": 3},
            }

        graph_routes._run_crawler_once_sync = _fake_run_once  # type: ignore[assignment]
        graph_routes._run_crawler_retry_ingest_failed_sync = _fake_retry  # type: ignore[assignment]

        await graph_routes._execute_octopus_full_run(run_id, request)
        saved = await graph_routes._load_full_run_state(run_id)
        self.assertIsNotNone(saved)
        assert saved is not None
        ingest_details = saved["stages"]["ingest"]["details"]
        self.assertEqual(ingest_details["ingested"], 2)
        self.assertEqual(ingest_details["failed"], 1)
        self.assertEqual(ingest_details["total"], 3)
        self.assertEqual(saved["stages"]["ingest"]["status"], "partial_success")

    async def test_full_run_skips_retry_when_retry_limit_zero(self) -> None:
        run_id = "octopus_full_test_skip_retry"
        request = graph_routes.CrawlerOctopusFullRunRequest(
            max_items_per_source=1,
            since_hours=1,
            process_limit=10,
            ingest_retry_limit=0,
            rebuild_storylines=False,
        )
        state = graph_routes._new_full_run_state(run_id, request)
        await graph_routes._save_full_run_state(state)

        def _fake_run_once(req):  # type: ignore[no-untyped-def]
            return {
                "fetch": {"total": 1, "inserted": 1, "touched": 1},
                "compress": {"compressed": 1, "failed": 0, "total": 1},
                "ingest": {"ingested": 1, "failed": 0, "total": 1},
            }

        graph_routes._run_crawler_once_sync = _fake_run_once  # type: ignore[assignment]
        await graph_routes._execute_octopus_full_run(run_id, request)
        saved = await graph_routes._load_full_run_state(run_id)
        self.assertIsNotNone(saved)
        assert saved is not None
        ingest_details = saved["stages"]["ingest"]["details"]
        self.assertEqual(ingest_details["retry_limit"], 0)
        self.assertEqual(
            ingest_details["retry_ingest_failed"].get("reason"),
            "ingest_retry_limit_zero",
        )


if __name__ == "__main__":
    unittest.main()

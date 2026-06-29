from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_facade import MemoryFacade
from brain.memory.memory_models import (
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
    DryRunReplanPlanEvidenceRecord,
)
from brain.memory.sqlite_adapter import SQLiteAdapter


class DryRunReplanEvidenceFacadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-replan-evidence-test-"))
        self._audit_path = self._tmp / "audit.jsonl"
        self._sqlite_path = self._tmp / "memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _record(self, plan_id: str = "plan-1", session_id: str = "session-1") -> DryRunReplanPlanEvidenceRecord:
        return DryRunReplanPlanEvidenceRecord(
            plan_id=plan_id,
            would_replan=True,
            replan_reason="replan_eligible",
            blocked=False,
            block_reasons=[],
            replan_eligibility_score=0.9,
            risk_level="low",
            source_decision="REPLAN",
            fingerprint_id="fp-1",
            stagnation_score=8,
            progress_score=2,
            repeated_strategy_count=3,
            suggested_strategy="change_safe_strategy_category",
            evidence_summary="safe metadata only",
            created_at="2026-06-29T00:00:00+00:00",
            session_id=session_id,
            request_id="request-1",
            trace_id="trace-1",
        )

    def test_jsonl_default_records_safe_evidence_without_sqlite(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path, sqlite_path=self._sqlite_path)
        facade.record_dry_run_replan_plan_evidence(self._record())

        self.assertFalse(facade.sqlite_enabled)
        self.assertFalse(facade.is_sqlite_connected)
        records = facade.audit_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)
        payload = records[0]["payload"]
        self.assertEqual(payload["event_type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertEqual(payload["plan_id"], "plan-1")
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("provider_payload", payload)

    def test_sqlite_opt_in_records_and_lists_evidence(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.record_dry_run_replan_plan_evidence(self._record())

        results = facade.list_dry_run_replan_plan_evidence()
        self.assertEqual(len(results), 1)
        payload = results[0].as_dict()
        self.assertEqual(payload["plan_id"], "plan-1")
        self.assertEqual(payload["event_type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)
        self.assertTrue(payload["advisory"])
        self.assertEqual(payload["session_id"], "session-1")

    def test_sqlite_list_can_filter_by_safe_session_id(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.record_dry_run_replan_plan_evidence(self._record("plan-1", "session-1"))
        facade.record_dry_run_replan_plan_evidence(self._record("plan-2", "session-2"))

        results = facade.list_dry_run_replan_plan_evidence(session_id="session-2")
        self.assertEqual([record.plan_id for record in results], ["plan-2"])

    def test_sqlite_schema_creates_evidence_table(self) -> None:
        adapter = SQLiteAdapter(self._sqlite_path)
        try:
            adapter.connect()
            self.assertTrue(adapter.table_exists("dry_run_replan_plan_evidence"))
        finally:
            adapter.close()

    def test_sqlite_adapter_insert_and_list_degrades_corrupt_rows(self) -> None:
        adapter = SQLiteAdapter(self._sqlite_path)
        try:
            adapter.connect()
            adapter.insert_dry_run_replan_plan_evidence(self._record())
            self.assertEqual(len(adapter.list_dry_run_replan_plan_evidence()), 1)
            adapter._execute(
                "UPDATE dry_run_replan_plan_evidence SET block_reasons = ? WHERE plan_id = ?",
                "{not-json",
                "plan-1",
            )
            self.assertEqual(adapter.list_dry_run_replan_plan_evidence(), [])
        finally:
            adapter.close()

    def test_memory_facade_write_failure_degrades_safely(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()

        class FailingSQLite:
            def insert_dry_run_replan_plan_evidence(self, record: DryRunReplanPlanEvidenceRecord) -> None:
                raise RuntimeError("raw_prompt secret should not escape")

            def list_dry_run_replan_plan_evidence(
                self,
                limit: int = 50,
                session_id: str = "",
            ) -> list[DryRunReplanPlanEvidenceRecord]:
                raise RuntimeError("provider_payload should not escape")

        facade._sqlite = FailingSQLite()  # type: ignore[assignment]
        facade.record_dry_run_replan_plan_evidence(self._record())
        self.assertEqual(facade.list_dry_run_replan_plan_evidence(), [])

        records = facade.audit_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE)


if __name__ == "__main__":
    unittest.main()

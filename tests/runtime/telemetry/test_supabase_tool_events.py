from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from brain.runtime.telemetry.supabase_tool_events import (
    error_code_from_tool_result,
    record_runtime_tool_event,
)


class SupabaseToolEventsTest(unittest.TestCase):
    def test_error_code_ok(self) -> None:
        self.assertIsNone(error_code_from_tool_result({"ok": True}))

    def test_error_code_from_payload(self) -> None:
        self.assertEqual(
            error_code_from_tool_result(
                {"ok": False, "error_payload": {"kind": "policy_stop"}}
            ),
            "policy_stop",
        )

    def test_record_skips_without_env(self) -> None:
        self.assertFalse(
            record_runtime_tool_event(
                session_id="s",
                task_id="t",
                run_id="r",
                tool_name="read_file",
                success=True,
                error_code=None,
                latency_ms=12,
            )
        )

    @patch("brain.runtime.telemetry.supabase_tool_events.urllib.request.urlopen")
    def test_record_posts_json(self, mock_urlopen: MagicMock) -> None:
        inner = MagicMock()
        inner.status = 201
        inner.getcode.return_value = 201
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = inner
        mock_cm.__exit__.return_value = False
        mock_urlopen.return_value = mock_cm
        prev_url = os.environ.get("SUPABASE_URL")
        prev_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        try:
            os.environ["SUPABASE_URL"] = "https://abc.supabase.co"
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "secret-service-key"
            ok = record_runtime_tool_event(
                session_id="sess-1",
                task_id="task-1",
                run_id="run-1",
                tool_name="grep_search",
                success=False,
                error_code="timeout",
                latency_ms=99,
                metadata={"k": "v"},
            )
            self.assertTrue(ok)
            self.assertEqual(mock_urlopen.call_count, 1)
            req = mock_urlopen.call_args[0][0]
            url = getattr(req, "full_url", None) or req.get_full_url()
            self.assertEqual(url, "https://abc.supabase.co/rest/v1/runtime_tool_events")
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(len(body), 1)
            self.assertEqual(body[0]["tool_name"], "grep_search")
            self.assertFalse(body[0]["success"])
            self.assertEqual(body[0]["error_code"], "timeout")
        finally:
            if prev_url is None:
                os.environ.pop("SUPABASE_URL", None)
            else:
                os.environ["SUPABASE_URL"] = prev_url
            if prev_key is None:
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            else:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = prev_key


if __name__ == "__main__":
    unittest.main()

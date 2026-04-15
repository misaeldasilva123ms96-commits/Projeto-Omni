from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import Goal, GoalStore  # noqa: E402
from brain.runtime.language import (  # noqa: E402
    OILError,
    OILHandoffProtocol,
    OILRequest,
    OILResult,
    OILTrace,
    OIL_PROTOCOL_VERSION,
    OILCommunicationEnvelope,
    OILRuntimeProtocolEnvelope,
    build_memory_result,
    build_memory_lookup,
    build_planner_request,
    build_planner_result,
    build_specialist_request,
    build_specialist_result,
    build_tool_execution,
    build_tool_result,
    runtime_protocol_from_legacy_dict,
    runtime_protocol_to_communication_envelope,
    runtime_protocol_to_legacy_dict,
    runtime_protocol_to_oil_request,
)
from brain.runtime.language.types import OILErrorDetails, OIL_VERSION  # noqa: E402
from brain.runtime.specialists import SpecialistCoordinator  # noqa: E402


class OilTransportEnvelopeTest(unittest.TestCase):
    """OILCommunicationEnvelope + OILHandoffProtocol (transport layer)."""

    def test_transport_request_round_trip(self) -> None:
        req = OILRequest.deserialize(
            {
                "oil_version": OIL_VERSION,
                "intent": "plan",
                "entities": {"topic": "runtime"},
                "constraints": {},
                "context": {"session_id": "s1"},
                "requested_output": "plan",
                "execution": {"priority": "normal", "complexity": "light", "mode": "interactive"},
            }
        )
        env = OILHandoffProtocol.wrap_request(
            req,
            source="orchestrator",
            destination="planner",
            correlation_id="corr-fixed",
            capability_path="planning.default",
        )
        wire = json.dumps(env.serialize())
        back = OILCommunicationEnvelope.deserialize(json.loads(wire))
        out = OILHandoffProtocol.unwrap_request(back)
        self.assertEqual(out.serialize(), req.serialize())
        self.assertEqual(back.protocol_version, OIL_PROTOCOL_VERSION)

    def test_transport_relay_chain(self) -> None:
        req = OILRequest.deserialize({"oil_version": OIL_VERSION, "intent": "ask_question"})
        env = OILHandoffProtocol.wrap_request(req, source="runtime", destination="planner")
        e3 = OILHandoffProtocol.relay(
            OILHandoffProtocol.relay(env, new_destination="specialist:governance"),
            new_destination="memory",
        )
        self.assertEqual(e3.trace.correlation_id, env.trace.correlation_id)
        self.assertEqual(e3.trace.hop, env.trace.hop + 2)

    def test_transport_result_and_error_round_trip(self) -> None:
        res = OILResult(
            oil_version=OIL_VERSION,
            result_type="plan",
            status="success",
            data={"steps": ["a"]},
            confidence=0.9,
            trace=OILTrace(planner="planner_v1"),
        )
        env_r = OILHandoffProtocol.wrap_result(
            res,
            source="planner",
            destination="orchestrator",
            correlation_id="c1",
            trace_id="t1",
            parent_span_id="span-parent",
            hop=2,
        )
        r2 = OILHandoffProtocol.unwrap_result(OILCommunicationEnvelope.deserialize(env_r.serialize()))
        self.assertEqual(r2.serialize(), res.serialize())
        err = OILError(
            oil_version=OIL_VERSION,
            error=OILErrorDetails(code="X", message="m", recoverable=False),
        )
        env_e = OILHandoffProtocol.wrap_error(
            err,
            source="planner",
            destination="orchestrator",
            correlation_id="c1",
            trace_id="t1",
            parent_span_id="span-parent",
            hop=2,
        )
        e2 = OILHandoffProtocol.unwrap_error(OILCommunicationEnvelope.deserialize(env_e.serialize()))
        self.assertEqual(e2.serialize(), err.serialize())

    def test_transport_invalid_kind_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OILCommunicationEnvelope.deserialize({"protocol_version": "1.0", "message_kind": "unknown", "oil": {}})


class OilRuntimeProtocolTest(unittest.TestCase):
    """OILRuntimeProtocolEnvelope + builders + shims (Phase 30.3)."""

    def test_gate_30_3_1_runtime_envelope_integrity(self) -> None:
        proto = build_planner_request(
            source_component="orchestrator",
            target_component="planner",
            session_id="s1",
            run_id="run-1",
            trace_id="trace-xyz",
            intent="generate_business_idea",
            payload={"entities": {"domain": "digital"}, "constraints": {"budget": "low"}},
            routing={"path": "planning.default"},
        )
        wire = json.dumps(proto.serialize())
        back = OILRuntimeProtocolEnvelope.deserialize(json.loads(wire))
        self.assertEqual(back.protocol_type, "planner_request")
        self.assertEqual(back.payload["entities"]["domain"], "digital")

    def test_result_envelope_builders(self) -> None:
        pr = build_planner_result(
            source_component="planner",
            target_component="orchestrator",
            session_id="s",
            run_id="r",
            trace_id="t",
            intent="plan",
            payload={"entities": {"ok": True}},
            routing={},
        )
        self.assertEqual(pr.protocol_type, "planner_result")
        sr = build_specialist_result(
            source_component="s1",
            target_component="s2",
            session_id="s",
            run_id="r",
            trace_id="t",
            intent="x",
            payload={},
            routing={},
        )
        self.assertEqual(sr.protocol_type, "specialist_result")
        mr = build_memory_result(
            source_component="memory",
            target_component="runtime",
            session_id="s",
            run_id="r",
            trace_id="t",
            intent="retrieve",
            payload={},
            routing={},
        )
        self.assertEqual(mr.protocol_type, "memory_result")
        tr = build_tool_result(
            source_component="executor",
            target_component="orchestrator",
            session_id="s",
            run_id="r",
            trace_id="t",
            intent="tool",
            payload={},
            routing={},
        )
        self.assertEqual(tr.protocol_type, "tool_result")

    def test_gate_30_3_3_metadata_preserved_specialist_and_memory(self) -> None:
        sp = build_specialist_request(
            source_component="planner",
            target_component="startup_advisor",
            session_id="abc",
            run_id=None,
            trace_id="t-1",
            intent="generate_business_idea",
            payload={"entities": {"domain": "digital"}},
            routing={"priority": "normal"},
        )
        self.assertEqual(sp.source_component, "planner")
        self.assertEqual(sp.trace_id, "t-1")
        mem = build_memory_lookup(
            source_component="runtime",
            target_component="memory_facade",
            session_id="abc",
            run_id="run-001",
            trace_id="t-1",
            intent="retrieve_context",
            payload={"entities": {"query": "run registry"}},
            routing={"layer": "semantic"},
        )
        self.assertEqual(mem.protocol_type, "memory_lookup")
        self.assertEqual(mem.run_id, "run-001")

    def test_gate_30_3_3_legacy_shim_round_trip(self) -> None:
        proto = build_tool_execution(
            source_component="planner",
            target_component="trusted_executor",
            session_id="s",
            run_id="r",
            trace_id="t",
            intent="execute_tool_like_action",
            payload={"entities": {"tool": "read_file"}},
            routing={},
        )
        legacy = runtime_protocol_to_legacy_dict(proto)
        back = runtime_protocol_from_legacy_dict(legacy)
        self.assertEqual(back.serialize(), proto.serialize())
        nested = {"_oil_runtime_protocol": proto.serialize()}
        self.assertEqual(runtime_protocol_from_legacy_dict(nested).trace_id, proto.trace_id)

    def test_runtime_protocol_maps_to_oil_request_and_transport(self) -> None:
        proto = build_specialist_request(
            source_component="a",
            target_component="b",
            session_id="s",
            run_id=None,
            trace_id="tid",
            intent="summarize",
            payload={"entities": {"topic": "x"}, "constraints": {"length": "short"}},
            routing={"hop": 0},
        )
        oil_req = runtime_protocol_to_oil_request(proto)
        self.assertEqual(oil_req.intent, "summarize")
        self.assertEqual(oil_req.entities.get("topic"), "x")
        comm = runtime_protocol_to_communication_envelope(proto)
        self.assertEqual(comm.message_kind, "oil_request")
        self.assertEqual(OILHandoffProtocol.unwrap_request(comm).intent, "summarize")


class SpecialistCoordinatorProtocolAdoptionTest(unittest.TestCase):
    """Gate 30.3.2 — internal handoff records OIL-compatible protocol on coordination trace."""

    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-protocol-coordinator"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"coord-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_coordinator_attaches_protocol_envelopes(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = Goal.build(
                description="Stay safe.",
                intent="safety",
                subgoals=[],
                constraints=[],
                success_criteria=[],
                failure_tolerances=[],
                stop_conditions=[],
                priority=1,
            )
            GoalStore(workspace_root).save_goal(goal)
            coordinator = SpecialistCoordinator(workspace_root)
            trace = coordinator.coordinate(
                session_id="sess-1",
                goal_id=goal.goal_id,
                action={"step_id": "step-1", "run_id": "run-42", "intent": "test_intent", "hard_constraint_violation": True},
                plan=None,
                execute_callback=lambda: {"ok": True},
            )
            envs = trace.metadata.get("oil_runtime_protocol_envelopes")
            self.assertIsInstance(envs, list)
            self.assertGreaterEqual(len(envs), 1)
            first = OILRuntimeProtocolEnvelope.deserialize(envs[0])
            self.assertEqual(first.protocol_type, "specialist_request")
            self.assertEqual(first.trace_id, trace.trace_id)
            self.assertEqual(first.session_id, "sess-1")
            self.assertEqual(first.run_id, "run-42")
            legacy = trace.metadata.get("oil_runtime_protocol_open_legacy")
            self.assertIsInstance(legacy, dict)
            self.assertEqual(legacy.get("trace"), trace.trace_id)


if __name__ == "__main__":
    unittest.main()

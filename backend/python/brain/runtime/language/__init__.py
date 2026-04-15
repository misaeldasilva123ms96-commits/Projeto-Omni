"""Omni Internal Language (OIL) — runtime language layer (Phase 30.x)."""

from brain.runtime.language.envelopes import (
    OILCommunicationEnvelope,
    OILRuntimeProtocolEnvelope,
    OILRoutingMetadata,
    OILTraceMetadata,
)
from brain.runtime.language.oil_schema import OILError, OILRequest, OILResult
from brain.runtime.language.input_interpreter import InputInterpreter, interpret_input
from brain.runtime.language.output_composer import OutputComposer, compose_output
from brain.runtime.language.protocol import (
    OILHandoffProtocol,
    OIL_PROTOCOL_VERSION,
    build_memory_lookup,
    build_memory_result,
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
from brain.runtime.language.types import (
    OIL_VERSION,
    OILContext,
    OILExecution,
    OILErrorDetails,
    OILTrace,
)

__all__ = [
    "OIL_VERSION",
    "OILContext",
    "OILExecution",
    "OILTrace",
    "OILErrorDetails",
    "OILRequest",
    "OILResult",
    "OILError",
    "InputInterpreter",
    "interpret_input",
    "OutputComposer",
    "compose_output",
    "OIL_PROTOCOL_VERSION",
    "OILRoutingMetadata",
    "OILTraceMetadata",
    "OILCommunicationEnvelope",
    "OILRuntimeProtocolEnvelope",
    "OILHandoffProtocol",
    "build_planner_request",
    "build_planner_result",
    "build_specialist_request",
    "build_specialist_result",
    "build_memory_lookup",
    "build_memory_result",
    "build_tool_execution",
    "build_tool_result",
    "runtime_protocol_to_legacy_dict",
    "runtime_protocol_from_legacy_dict",
    "runtime_protocol_to_oil_request",
    "runtime_protocol_to_communication_envelope",
]

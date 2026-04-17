"""Omni Internal Language (OIL) — runtime language layer (Phase 30.x)."""

# Closed convergence band with runtime governance/control plane (30.1–30.9); informational only.
OMNI_OIL_PROGRAM_RANGE = "30.1-30.9"

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
from brain.runtime.language.reasoning_contract import (
    ReasoningHandoffContract,
    build_reasoning_oil_result,
    normalize_input_to_oil_request,
)
from brain.runtime.language.types import (
    OIL_VERSION,
    OILContext,
    OILExecution,
    OILErrorDetails,
    OILTrace,
)

__all__ = [
    "OMNI_OIL_PROGRAM_RANGE",
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
    "ReasoningHandoffContract",
    "normalize_input_to_oil_request",
    "build_reasoning_oil_result",
]

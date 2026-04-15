"""Omni Internal Language (OIL) — runtime language layer (Phase 30.x)."""

from brain.runtime.language.oil_schema import OILError, OILRequest, OILResult
from brain.runtime.language.input_interpreter import InputInterpreter, interpret_input
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
]

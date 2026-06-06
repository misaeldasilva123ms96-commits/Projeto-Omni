import asyncio
from pathlib import Path
from typing import Any

import pytest

from brain.swarm.base_agent import SwarmMessage


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def swarm_queue():
    return asyncio.Queue()


@pytest.fixture
def session_id():
    return "test-session-001"


@pytest.fixture
def base_context() -> dict[str, Any]:
    return {
        "message": "qual a melhor forma de aprender programacao?",
        "memory": {},
        "history": [],
        "summary": "",
        "capabilities": [],
    }


@pytest.fixture
def sample_message(swarm_queue, session_id) -> SwarmMessage:
    return SwarmMessage(
        from_agent="test_agent",
        to_agent="test_agent",
        type="task",
        payload={"key": "value"},
        timestamp="2026-01-01T00:00:00+00:00",
        session_id=session_id,
    )


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path

import pytest

from brain.swarm.memory_agent import MemoryAgent


@pytest.mark.asyncio
async def test_memory_consolidates_user_data(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": {"nome": "Misael", "preferencias": ["python", "rust"]}, "history": [], "summary": ""}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["memory_signal"]["known_name"] == "Misael"
    assert "python" in result["memory_signal"]["preferences"]


@pytest.mark.asyncio
async def test_memory_empty_context(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": {}, "history": [], "summary": ""}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["memory_signal"]["known_name"] == ""
    assert result["memory_signal"]["preferences"] == []


@pytest.mark.asyncio
async def test_memory_tracks_history_size(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": {}, "history": [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "ola"}], "summary": ""}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["memory_signal"]["history_size"] == 2


@pytest.mark.asyncio
async def test_memory_includes_summary(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": {}, "history": [], "summary": "usuario quer aprender rust"}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["memory_signal"]["summary"] == "usuario quer aprender rust"


@pytest.mark.asyncio
async def test_memory_non_dict_user(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": None, "history": [], "summary": ""}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["memory_signal"]["known_name"] == ""


@pytest.mark.asyncio
async def test_memory_summary_returned(swarm_queue, session_id):
    agent = MemoryAgent("memory", swarm_queue)
    context = {"memory": {}, "history": [], "summary": ""}
    msg = await agent.publish(to_agent="memory", message_type="memory_op", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert "consolidada" in result["summary"].lower()

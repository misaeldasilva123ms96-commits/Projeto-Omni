import pytest

from brain.swarm.executor_agent import ExecutorAgent


@pytest.mark.asyncio
async def test_executor_planning_kind(swarm_queue, base_context, session_id):
    agent = ExecutorAgent("executor", swarm_queue)
    context = {**base_context, "intent": "decision"}
    msg = await agent.publish(to_agent="executor", message_type="task", payload={"kind": "planning", "goal": "quebrar tarefa", "id": "plan_outline"}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["delegate"] == "planner_agent"
    assert "plano" in result["result"].lower()


@pytest.mark.asyncio
async def test_executor_analysis_kind(swarm_queue, base_context, session_id):
    agent = ExecutorAgent("executor", swarm_queue)
    context = {**base_context, "intent": "conversa"}
    msg = await agent.publish(to_agent="executor", message_type="task", payload={"kind": "analysis", "goal": "analisar contexto", "id": "context_alignment"}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["delegate"] == "memory_agent"


@pytest.mark.asyncio
async def test_executor_review_kind(swarm_queue, base_context, session_id):
    agent = ExecutorAgent("executor", swarm_queue)
    context = {**base_context, "intent": "conversa"}
    msg = await agent.publish(to_agent="executor", message_type="task", payload={"kind": "review", "goal": "avaliar qualidade", "id": "quality_review"}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["delegate"] == "critic_agent"


@pytest.mark.asyncio
async def test_executor_default_kind(swarm_queue, base_context, session_id):
    agent = ExecutorAgent("executor", swarm_queue)
    context = {**base_context, "intent": "conversa"}
    msg = await agent.publish(to_agent="executor", message_type="task", payload={"kind": "unknown", "goal": "fazer algo", "id": "task_001"}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["delegate"] == "executor_agent"


@pytest.mark.asyncio
async def test_executor_empty_payload_defaults_to_analysis(swarm_queue, base_context, session_id):
    agent = ExecutorAgent("executor", swarm_queue)
    context = {**base_context, "intent": "conversa"}
    msg = await agent.publish(to_agent="executor", message_type="task", payload={}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["delegate"] == "memory_agent"

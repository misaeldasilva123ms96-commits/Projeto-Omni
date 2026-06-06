import pytest

from brain.swarm.planner_agent import PlannerAgent


@pytest.mark.asyncio
async def test_planner_always_creates_context_alignment(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "conversa", "delegates": ["executor_agent"], "complex": False}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    subtask_ids = [s["id"] for s in result["subtasks"]]
    assert "context_alignment" in subtask_ids
    assert "response_execution" in subtask_ids
    assert "quality_review" in subtask_ids


@pytest.mark.asyncio
async def test_planner_complex_adds_plan_outline(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "decision", "delegates": ["planner_agent", "executor_agent"], "complex": True}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    subtask_ids = [s["id"] for s in result["subtasks"]]
    assert "plan_outline" in subtask_ids


@pytest.mark.asyncio
async def test_planner_simple_has_no_plan_outline(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "conversa", "delegates": ["executor_agent"], "complex": False}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    subtask_ids = [s["id"] for s in result["subtasks"]]
    assert "plan_outline" not in subtask_ids


@pytest.mark.asyncio
async def test_planner_delegate_order_deduplicates(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "conversa", "delegates": ["memory_agent", "executor_agent"], "complex": False}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert len(result["delegates"]) == len(set(result["delegates"]))


@pytest.mark.asyncio
async def test_planner_summary_count(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "decision", "delegates": ["planner_agent"], "complex": True}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert str(len(result["subtasks"])) in result["summary"]


@pytest.mark.asyncio
async def test_planner_intent_preserved(swarm_queue, base_context, session_id):
    agent = PlannerAgent("planner", swarm_queue)
    msg = await agent.publish(to_agent="planner", message_type="task", payload={"intent": "explicacao", "delegates": [], "complex": False}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "explicacao"

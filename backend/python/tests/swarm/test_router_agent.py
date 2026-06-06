import pytest

from brain.swarm.router_agent import RouterAgent


@pytest.mark.asyncio
async def test_router_intent_conversa(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    context = {**base_context, "message": "ola tudo bem?"}
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "ola tudo bem?"}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["intent"] == "conversa"
    assert result["complex"] is False


@pytest.mark.asyncio
async def test_router_intent_decisao(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "devo investir ou poupar?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "decision"
    assert result["complex"] is True


@pytest.mark.asyncio
async def test_router_intent_dinheiro(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "como ganhar dinheiro rapido?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "dinheiro"
    assert result["complex"] is True


@pytest.mark.asyncio
async def test_router_intent_aprendizado(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "por onde comeco a programar?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "aprendizado"
    assert result["complex"] is True


@pytest.mark.asyncio
async def test_router_intent_aprendizado_from_history(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    context = {**base_context, "history": [{"role": "user", "content": "quero aprender python"}]}
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "e depois?"}, session_id=session_id)
    result = await agent.receive(msg, context=context)
    assert result["intent"] == "aprendizado"


@pytest.mark.asyncio
async def test_router_intent_explicacao(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "o que e machine learning?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "explicacao"


@pytest.mark.asyncio
async def test_router_intent_pessoal(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "quem e voce?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "pessoal"


@pytest.mark.asyncio
async def test_router_complex_short_message(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "oi"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["complex"] is False


@pytest.mark.asyncio
async def test_router_delegates_by_intent(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "como ganhar dinheiro?"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert "planner_agent" in result["delegates"]
    assert "executor_agent" in result["delegates"]
    assert "critic_agent" in result["delegates"]
    assert "memory_agent" in result["delegates"]


@pytest.mark.asyncio
async def test_router_unknown_payload(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["intent"] == "conversa"


@pytest.mark.asyncio
async def test_router_summary_contains_intent(swarm_queue, base_context, session_id):
    agent = RouterAgent("router", swarm_queue)
    msg = await agent.publish(to_agent="router", message_type="task", payload={"message": "explique quantica"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert "explicacao" in result["summary"]

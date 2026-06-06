import pytest

from brain.swarm.critic_agent import CriticAgent


@pytest.mark.asyncio
async def test_critic_approves_long_response(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    context = {**base_context, "intent": "conversa", "message": "fale sobre python"}
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": "Python e uma linguagem de programacao versatil e poderosa, usada em web, dados e automacao."}, session_id=session_id)
    result = await agent.receive(msg, context)
    assert result["approved"] is True
    assert result["score"] >= 0.8


@pytest.mark.asyncio
async def test_critic_short_response_flagged(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": "ok"}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["approved"] is True
    assert result["score"] == 0.45
    assert "resposta curta demais" in result["issues"]


@pytest.mark.asyncio
async def test_critic_rejects_empty_response(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": ""}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["approved"] is False
    assert result["score"] <= 0.1


@pytest.mark.asyncio
async def test_critic_detects_fallback(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": "Nao consegui processar sua solicitacao. Tente reformular."}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert "fallback detectado" in result["issues"]
    if result["score"] >= 0.4:
        assert "Proximo passo" in result["response"]


@pytest.mark.asyncio
async def test_critic_empty_response_has_no_proximo_passo(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": ""}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert "Proximo passo" not in result["response"]


@pytest.mark.asyncio
async def test_critic_score_threshold_edge(swarm_queue, base_context, session_id):
    agent = CriticAgent("critic", swarm_queue)
    response = "palavra " * 3
    msg = await agent.publish(to_agent="critic", message_type="critique", payload={"response": response.strip()}, session_id=session_id)
    result = await agent.receive(msg, context=base_context)
    assert result["score"] < 0.5

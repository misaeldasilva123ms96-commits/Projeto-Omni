import pytest

from brain.swarm.swarm_orchestrator import SwarmOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_run_returns_expected_keys(temp_dir, session_id):
    log_path = temp_dir / "swarm_log.json"
    orch = SwarmOrchestrator(log_path)

    async def fake_executor(ctx):
        return "Resposta simulada do executor"

    result = await orch.run(
        message="qual a melhor forma de aprender python?",
        session_id=session_id,
        memory_store={"user": {"name": "Misael"}},
        history=[],
        summary="",
        capabilities=[],
        executor=fake_executor,
    )

    assert "response" in result
    assert "intent" in result
    assert "delegates" in result
    assert "agent_trace" in result
    assert "memory_signal" in result
    assert len(result["agent_trace"]) >= 5
    assert result["intent"] is not None


@pytest.mark.asyncio
async def test_orchestrator_log_file_created(temp_dir, session_id):
    log_path = temp_dir / "swarm_log.json"
    orch = SwarmOrchestrator(log_path)

    async def fake_executor(ctx):
        return "resposta"

    await orch.run(
        message="ola",
        session_id=session_id,
        memory_store={},
        history=[],
        summary="",
        capabilities=[],
        executor=fake_executor,
    )

    assert log_path.exists()
    raw = log_path.read_text(encoding="utf-8")
    assert "session_id" in raw


@pytest.mark.asyncio
async def test_orchestrator_invalid_executor(temp_dir, session_id):
    log_path = temp_dir / "swarm_log.json"
    orch = SwarmOrchestrator(log_path)

    with pytest.raises(Exception):
        await orch.run(
            message="teste",
            session_id=session_id,
            memory_store={},
            history=[],
            summary="",
            capabilities=[],
            executor=None,
        )


@pytest.mark.asyncio
async def test_orchestrator_log_append_truncates(temp_dir, session_id):
    log_path = temp_dir / "swarm_log.json"
    orch = SwarmOrchestrator(log_path)

    async def fake_executor(ctx):
        return "r"

    for i in range(55):
        await orch.run(
            message=f"msg-{i}",
            session_id=session_id,
            memory_store={},
            history=[],
            summary="",
            capabilities=[],
            executor=fake_executor,
        )

    raw = log_path.read_text(encoding="utf-8")
    import json
    data = json.loads(raw)
    assert len(data["events"]) <= 55


@pytest.mark.asyncio
async def test_orchestrator_memory_context_injected(temp_dir, session_id):
    log_path = temp_dir / "swarm_log.json"
    orch = SwarmOrchestrator(log_path)

    async def fake_executor(ctx):
        return f"memoria: {ctx.get('memory', {})}"

    result = await orch.run(
        message="teste memoria",
        session_id=session_id,
        memory_store={"user": {"nome": "Misael"}},
        history=[],
        summary="",
        capabilities=[],
        executor=fake_executor,
    )

    assert "Misael" in result["memory_signal"]["known_name"]

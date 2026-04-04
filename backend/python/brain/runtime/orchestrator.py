from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from brain.evolution.evaluator import ResponseEvaluator
from brain.evolution.pattern_analyzer import PatternAnalyzer
from brain.evolution.strategy_updater import StrategyUpdater
from brain.memory.hybrid import HybridMemory
from brain.memory.store import (
    DEFAULT_HISTORY_LIMIT,
    append_history,
    load_memory_store,
    normalize_user_profile,
    save_memory_store,
)
from brain.registry import describe_agents, describe_capabilities, recommend_capabilities
from brain.runtime.session_store import SessionStore
from brain.runtime.transcript_store import TranscriptStore
from brain.swarm.swarm_orchestrator import SwarmOrchestrator


SAFE_FALLBACK_RESPONSE = "Nao consegui processar isso ainda, mas estou aprendendo."
SUBPROCESS_TIMEOUT_SECONDS = 10
DEFAULT_SESSION_ID = "python-session"
MAX_TURNS_PER_SESSION = 25
SESSION_TITLE_LIMIT = 60


@dataclass(frozen=True)
class BrainRequest:
    message: str
    user_id: str = ""
    session_id: str = ""
    turn_id: str = ""


@dataclass(frozen=True)
class FeedbackRequest:
    turn_id: str
    value: str
    text: str = ""
    user_id: str = ""
    session_id: str = ""


@dataclass(frozen=True)
class BrainPaths:
    root: Path
    python_root: Path
    memory_json: Path
    memory_dir: Path
    transcripts_dir: Path
    sessions_dir: Path
    js_runner: Path
    swarm_log: Path
    evolution_dir: Path
    strategy_state_path: Path
    loop_log_path: Path
    snapshots_dir: Path

    @classmethod
    def from_entrypoint(cls, entrypoint: Path) -> "BrainPaths":
        project_root = (
            Path(os.environ["BASE_DIR"]).resolve()
            if os.getenv("BASE_DIR")
            else entrypoint.resolve().parents[4]
        )
        python_root = (
            Path(os.environ["PYTHON_BASE_DIR"]).resolve()
            if os.getenv("PYTHON_BASE_DIR")
            else project_root / "backend" / "python"
        )
        evolution_dir = python_root / "brain" / "evolution"
        return cls(
            root=project_root,
            python_root=python_root,
            memory_json=Path(os.getenv("MEMORY_JSON_PATH", str(python_root / "memory.json"))),
            memory_dir=Path(os.getenv("MEMORY_DIR", str(python_root / "memory"))),
            transcripts_dir=Path(os.getenv("TRANSCRIPTS_DIR", str(python_root / "transcripts"))),
            sessions_dir=Path(os.getenv("SESSIONS_DIR", str(python_root / "brain" / "runtime" / "sessions"))),
            js_runner=python_root / "js-runner" / "queryEngineRunner.js",
            swarm_log=python_root / "brain" / "runtime" / "swarm_log.json",
            evolution_dir=evolution_dir,
            strategy_state_path=evolution_dir / "strategy_state.json",
            loop_log_path=evolution_dir / "loop_log.json",
            snapshots_dir=evolution_dir / "snapshots",
        )

    def for_user(self, user_id: str) -> "BrainPaths":
        safe_user_id = _safe_identifier(user_id)
        if not safe_user_id:
            return self

        user_root = self.python_root / "users" / safe_user_id
        evolution_dir = user_root / "evolution"
        return BrainPaths(
            root=self.root,
            python_root=self.python_root,
            memory_json=user_root / "memory.json",
            memory_dir=user_root / "memory",
            transcripts_dir=user_root / "transcripts",
            sessions_dir=user_root / "sessions",
            js_runner=self.js_runner,
            swarm_log=user_root / "swarm_log.json",
            evolution_dir=evolution_dir,
            strategy_state_path=evolution_dir / "strategy_state.json",
            loop_log_path=evolution_dir / "loop_log.json",
            snapshots_dir=evolution_dir / "snapshots",
        )


def _safe_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip())
    return cleaned.strip("-_.")


class BrainOrchestrator:
    def __init__(self, paths: BrainPaths) -> None:
        self.paths = paths
        self.evaluator = ResponseEvaluator()
        self.analyzer = PatternAnalyzer()
        self._runtime_meta_by_turn: dict[str, dict[str, Any]] = {}

    def run(self, message: str) -> str:
        return self.run_request(BrainRequest(message=message)).get("response", SAFE_FALLBACK_RESPONSE)

    def run_request(self, request: BrainRequest) -> dict[str, Any]:
        scoped_paths = self.paths.for_user(request.user_id)
        hybrid_memory = HybridMemory(scoped_paths.memory_dir)
        transcript_store = TranscriptStore(scoped_paths.transcripts_dir)
        session_store = SessionStore(scoped_paths.sessions_dir)
        swarm_orchestrator = SwarmOrchestrator(scoped_paths.swarm_log)
        strategy_updater = StrategyUpdater(scoped_paths.snapshots_dir)
        self._ensure_evolution_files(scoped_paths)

        message = self._repair_text(request.message.strip())
        if not message:
            return {
                "response": SAFE_FALLBACK_RESPONSE,
                "turn_id": request.turn_id or str(uuid4()),
                "session_id": request.session_id or self._session_id(request.user_id),
                "user_id": request.user_id,
                "evolution_version": 1,
            }

        turn_id = request.turn_id or str(uuid4())
        session_id = request.session_id or self._session_id(request.user_id)

        memory_store = load_memory_store(scoped_paths.memory_json, history_limit=DEFAULT_HISTORY_LIMIT)
        transcript_history = transcript_store.load_recent_history(session_id, limit=DEFAULT_HISTORY_LIMIT)
        memory_store["history"] = self._merge_recent_history(
            transcript_history,
            memory_store.get("history", []) if isinstance(memory_store.get("history", []), list) else [],
        )

        user_profile = normalize_user_profile(memory_store.get("user", {}))
        if request.user_id and not user_profile.get("id"):
            user_profile["id"] = request.user_id
        memory_store["user"] = user_profile

        self._extract_user_learning(memory_store, message)
        append_history(memory_store, "user", message, history_limit=DEFAULT_HISTORY_LIMIT)

        available_capabilities = describe_capabilities()
        suggested_capabilities = recommend_capabilities(message)
        predicted_intent = self._predict_intent(message)
        current_strategy = self._load_strategy_state(scoped_paths)
        summary = self.summarize_history(memory_store.get("history", []))
        session_payload = session_store.load(session_id)
        existing_created_at = str(session_payload.get("created_at", "")).strip()
        existing_title = str(session_payload.get("title", "")).strip()
        direct_response = self._answer_from_memory(memory_store, message) or self._acknowledge_user_facts(memory_store, message)
        strategy_name = "memory_recall" if direct_response else predicted_intent

        swarm_result: dict[str, Any] = {
            "response": direct_response,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
        }

        if not direct_response:
            swarm_result = asyncio.run(
                swarm_orchestrator.run(
                    message=message,
                    session_id=session_id,
                    memory_store=memory_store,
                    history=memory_store.get("history", []),
                    summary=summary,
                    capabilities=available_capabilities,
                    executor=lambda payload: self._async_node_execution(
                        scoped_paths=scoped_paths,
                        session_store=session_store,
                        session_id=session_id,
                        user_id=request.user_id,
                        turn_id=turn_id,
                        message=message,
                        memory_store=memory_store,
                        available_capabilities=available_capabilities,
                        swarm_payload=payload,
                    ),
                )
            )
            runtime_meta = self._runtime_meta_by_turn.pop(turn_id, {})
            strategy_name = str(runtime_meta.get("strategy") or swarm_result.get("strategy") or swarm_result.get("intent") or predicted_intent)
        else:
            runtime_meta = {
                "strategy": strategy_name,
                "intent": predicted_intent,
                "provider": "local",
                "selected_mode": "heuristic",
                "fallback_used": False,
                "task_category": "memory" if strategy_name == "memory_recall" else predicted_intent,
                "latency_ms": 0,
            }

        response = self._repair_text(str(swarm_result.get("response", "")).strip()) or SAFE_FALLBACK_RESPONSE
        append_history(memory_store, "assistant", response, history_limit=DEFAULT_HISTORY_LIMIT)

        safe_store = save_memory_store(scoped_paths.memory_json, memory_store, history_limit=DEFAULT_HISTORY_LIMIT)
        hybrid_memory.sync_from_store(safe_store)
        transcript_store.append_turn(
            session_id,
            message,
            response,
            turn_id=turn_id,
            user_id=request.user_id,
            metadata={"intent": strategy_name},
        )

        evaluation = self.evaluator.evaluate(
            session_id=session_id,
            turn_id=turn_id,
            input_text=message,
            output_text=response,
            history=safe_store.get("history", []),
        )
        evaluation["strategy"] = strategy_name
        evaluation["intent"] = str(runtime_meta.get("intent") or predicted_intent)
        evaluation["provider"] = str(runtime_meta.get("provider") or "local")
        evaluation["selected_mode"] = str(runtime_meta.get("selected_mode") or "heuristic")
        evaluation["used_fallback"] = bool(runtime_meta.get("fallback_used"))
        evaluation["latency_ms"] = int(runtime_meta.get("latency_ms", 0) or 0)
        if runtime_meta.get("task_category"):
            evaluation["task_category"] = str(runtime_meta.get("task_category"))
        learning_data = hybrid_memory.record_learning(
            message=message,
            response=response,
            intent=strategy_name,
            capabilities=suggested_capabilities,
            evaluation=evaluation,
            strategy_version=int(current_strategy.get("version", 1)),
            strategy_name=strategy_name,
            turn_id=turn_id,
            session_id=session_id,
            user_id=request.user_id,
            profile=safe_store.get("user", {}),
            strategy_meta=runtime_meta,
        )
        strategy_state = self._update_evolution_state(scoped_paths, hybrid_memory, strategy_updater, learning_data)

        turn_record = {
            "turn_id": turn_id,
            "message": message,
            "response": response,
            "intent": strategy_name,
            "route_intent": str(runtime_meta.get("intent") or predicted_intent),
            "capabilities": suggested_capabilities,
            "strategy": strategy_name,
            "provider": str(runtime_meta.get("provider") or "local"),
            "selected_mode": str(runtime_meta.get("selected_mode") or "heuristic"),
            "fallback_used": bool(runtime_meta.get("fallback_used")),
            "task_category": str(runtime_meta.get("task_category") or evaluation.get("task_category") or predicted_intent),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "feedback": None,
        }
        turns = session_payload.get("turns", []) if isinstance(session_payload.get("turns", []), list) else []
        turns = [item for item in turns if isinstance(item, dict) and item.get("turn_id") != turn_id]
        turns.append(turn_record)
        session_created_at = existing_created_at or turn_record["created_at"]
        session_title = existing_title or self._generate_session_title(turns, safe_store.get("history", []))

        session_payload = {
            "session_id": session_id,
            "user_id": request.user_id,
            "title": session_title,
            "created_at": session_created_at,
            "updated_at": turn_record["created_at"],
            "turn_id": turn_id,
            "history": safe_store.get("history", []),
            "user": safe_store.get("user", {}),
            "summary": self.summarize_history(safe_store.get("history", [])),
            "capabilities": available_capabilities,
            "agent_registry": describe_agents(),
            "agent_trace": swarm_result.get("agent_trace", []),
            "evaluation": evaluation,
            "evolution_version": int(strategy_state.get("version", 1)),
            "turns": turns[-MAX_TURNS_PER_SESSION:],
            "swarm": {
                "intent": swarm_result.get("intent", predicted_intent),
                "strategy": strategy_name,
                "delegates": swarm_result.get("delegates", []),
                "memory_signal": swarm_result.get("memory_signal", {}),
            },
        }
        session_store.save(session_id, session_payload)

        return {
            "response": response,
            "turn_id": turn_id,
            "session_id": session_id,
            "user_id": request.user_id,
            "evolution_version": int(strategy_state.get("version", 1)),
        }

    def submit_feedback(self, request: FeedbackRequest) -> dict[str, Any]:
        scoped_paths = self.paths.for_user(request.user_id)
        hybrid_memory = HybridMemory(scoped_paths.memory_dir)
        session_store = SessionStore(scoped_paths.sessions_dir)
        self._ensure_evolution_files(scoped_paths)

        session_id = request.session_id or self._session_id(request.user_id)
        session_payload = session_store.load(session_id)
        turns = session_payload.get("turns", []) if isinstance(session_payload.get("turns", []), list) else []
        matched_turn = next((turn for turn in turns if isinstance(turn, dict) and turn.get("turn_id") == request.turn_id), {})

        strategy_name = str(matched_turn.get("strategy") or matched_turn.get("intent", "contextual_conversation"))
        capabilities = matched_turn.get("capabilities", []) if isinstance(matched_turn.get("capabilities", []), list) else []
        feedback_entry = hybrid_memory.record_feedback(
            turn_id=request.turn_id,
            session_id=session_id,
            user_id=request.user_id,
            value=request.value,
            text=request.text,
            strategy_name=strategy_name,
            capabilities=capabilities,
        )

        strategy_state = self._load_strategy_state(scoped_paths)
        strategy_feedback = strategy_state.get("feedback_scores", {})
        if not isinstance(strategy_feedback, dict):
            strategy_feedback = {}
        delta = 0.1 if request.value == "up" else -0.1
        strategy_feedback[strategy_name] = round(float(strategy_feedback.get(strategy_name, 0.0)) + delta, 3)
        strategy_state["feedback_scores"] = strategy_feedback
        strategy_state["last_feedback_at"] = datetime.now(timezone.utc).isoformat()
        strategies = strategy_state.get("strategies", {})
        if not isinstance(strategies, dict):
            strategies = {}
        strategy_entry = strategies.get(strategy_name, {})
        if not isinstance(strategy_entry, dict):
            strategy_entry = {}
        if request.value == "up":
            strategy_entry["positive_feedback"] = int(strategy_entry.get("positive_feedback", 0)) + 1
        else:
            strategy_entry["negative_feedback"] = int(strategy_entry.get("negative_feedback", 0)) + 1
        strategy_entry["feedback_score"] = round(float(strategy_entry.get("feedback_score", 0.0)) + delta, 3)
        strategy_entry["last_feedback_at"] = strategy_state["last_feedback_at"]
        strategies[strategy_name] = strategy_entry
        strategy_state["strategies"] = strategies
        scoped_paths.strategy_state_path.write_text(
            json.dumps(strategy_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for turn in turns:
            if isinstance(turn, dict) and turn.get("turn_id") == request.turn_id:
                turn["feedback"] = {
                    "value": request.value,
                    "text": request.text,
                    "submitted_at": feedback_entry.get("timestamp"),
                }
        session_payload["turns"] = turns[-MAX_TURNS_PER_SESSION:]
        session_payload["last_feedback"] = feedback_entry
        session_payload["evolution_version"] = int(strategy_state.get("version", 1))
        session_store.save(session_id, session_payload)

        return {
            "status": "recorded",
            "turn_id": request.turn_id,
            "session_id": session_id,
            "user_id": request.user_id,
            "strategy": strategy_name,
        }

    async def _async_node_execution(
        self,
        *,
        scoped_paths: BrainPaths,
        session_store: SessionStore,
        session_id: str,
        user_id: str,
        turn_id: str,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        swarm_payload: dict[str, Any],
    ) -> str:
        return self._call_node_query_engine(
            scoped_paths=scoped_paths,
            session_store=session_store,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            message=message,
            memory_store=memory_store,
            available_capabilities=available_capabilities,
            extra_session={"swarm_request": swarm_payload},
        )

    def _session_id(self, user_id: str = "") -> str:
        configured = os.getenv("AI_SESSION_ID", "").strip()
        if configured:
            return configured
        safe_user_id = _safe_identifier(user_id)
        return f"user-{safe_user_id}" if safe_user_id else DEFAULT_SESSION_ID

    def _resolve_node_bin(self) -> str | None:
        configured = os.getenv("NODE_BIN", "").strip()
        if configured:
            return configured
        return shutil.which("node")

    def _call_node_query_engine(
        self,
        *,
        scoped_paths: BrainPaths,
        session_store: SessionStore,
        session_id: str,
        user_id: str,
        turn_id: str,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        extra_session: dict[str, Any] | None = None,
    ) -> str:
        node_bin = self._resolve_node_bin()
        if not node_bin or not scoped_paths.js_runner.exists():
            return ""

        session_payload = session_store.load(session_id)
        runtime_meta_path = self._runtime_meta_path(scoped_paths, turn_id)
        self._runtime_meta_by_turn.pop(turn_id, None)
        try:
            runtime_meta_path.unlink(missing_ok=True)
        except Exception:
            pass

        session_payload.update(
            {
                "turn_id": turn_id,
                "user_id": user_id,
                "runtime_meta_path": str(runtime_meta_path),
                "strategy_state": self._load_strategy_state(scoped_paths),
            }
        )
        if extra_session:
            session_payload.update(extra_session)

        payload = json.dumps(
            {
                "message": message,
                "memory": memory_store.get("user", {}),
                "history": memory_store.get("history", []),
                "summary": self.summarize_history(memory_store.get("history", [])),
                "capabilities": available_capabilities,
                "session": session_payload,
            },
            ensure_ascii=False,
        )

        try:
            completed = subprocess.run(
                [node_bin, str(scoped_paths.js_runner), payload],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
                cwd=str(scoped_paths.root),
            )
        except Exception:
            return ""

        if completed.returncode != 0:
            return ""

        self._runtime_meta_by_turn[turn_id] = self._read_runtime_meta(runtime_meta_path)
        return self._repair_text(completed.stdout.strip())

    @staticmethod
    def summarize_history(history: object) -> str:
        if not isinstance(history, list) or len(history) <= 2:
            return ""

        summary_parts: list[str] = []
        for item in history[-4:]:
            if not isinstance(item, dict):
                continue
            role = "Usuario" if item.get("role") == "user" else "Assistente"
            content = str(item.get("content", "")).strip()
            if content:
                summary_parts.append(f"{role}: {content}")
        return " | ".join(summary_parts)

    @staticmethod
    def _runtime_meta_path(scoped_paths: BrainPaths, turn_id: str) -> Path:
        runtime_meta_dir = scoped_paths.sessions_dir / ".runtime_meta"
        runtime_meta_dir.mkdir(parents=True, exist_ok=True)
        return runtime_meta_dir / f"{turn_id}.json"

    @staticmethod
    def _read_runtime_meta(meta_path: Path) -> dict[str, Any]:
        try:
            if not meta_path.exists():
                return {}
            raw = meta_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _merge_recent_history(
        transcript_history: list[dict[str, str]],
        memory_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        merged = transcript_history + memory_history
        normalized: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in merged:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            key = (role, content)
            if key in seen:
                continue
            seen.add(key)
            normalized.append({"role": role, "content": content})
        return normalized[-DEFAULT_HISTORY_LIMIT:]

    @staticmethod
    def _repair_text(value: str) -> str:
        if not value:
            return ""
        if any(marker in value for marker in ("Ã", "ï¿½")):
            try:
                repaired = value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
                if repaired:
                    return repaired
            except Exception:
                return value
        return value

    def _extract_user_learning(self, memory_store: dict[str, object], message: str) -> None:
        user = normalize_user_profile(memory_store.get("user", {}))
        normalized = self._normalize_text(message)

        nome_match = re.search(r"\bmeu nome [eé]\s+([a-zà-ÿ][a-zà-ÿ\s'-]{1,80})", message, flags=re.IGNORECASE)
        if not nome_match:
            nome_match = re.search(r"\beu sou\s+([a-zà-ÿ][a-zà-ÿ\s'-]{1,80})", message, flags=re.IGNORECASE)
        if nome_match:
            nome = self._clean_name(nome_match.group(1))
            if nome:
                user["nome"] = nome

        trabalho_match = re.search(r"\btrabalho com\s+(.+?)(?:[,.!?]|$)", message, flags=re.IGNORECASE)
        if not trabalho_match:
            trabalho_match = re.search(r"\beu trabalho com\s+(.+?)(?:[,.!?]|$)", message, flags=re.IGNORECASE)
        if trabalho_match:
            trabalho = self._clean_fact(trabalho_match.group(1))
            if trabalho:
                user["trabalho"] = trabalho

        if "prefiro resposta" in normalized or "responda de forma" in normalized:
            if any(keyword in normalized for keyword in ("curta", "objetiva", "direta", "concisa")):
                user["response_style"] = "concise"
            elif any(keyword in normalized for keyword in ("estrategica", "consultiva", "analitica")):
                user["response_style"] = "strategic"
            else:
                user["response_style"] = "balanced"

        if any(keyword in normalized for keyword in ("mais profundo", "detalhado", "profundidade", "explique melhor", "mais detalhe")):
            user["depth_preference"] = "deep"
        elif any(keyword in normalized for keyword in ("resumo", "curto", "rapido", "breve")):
            user["depth_preference"] = "light"

        preference_patterns = [
            r"\bgosto de\s+(.+?)(?:[,.!?]|$)",
            r"\bprefiro\s+(.+?)(?:[,.!?]|$)",
        ]
        preferences = list(user.get("preferencias", []))
        for pattern in preference_patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if not match:
                continue
            value = self._clean_fact(match.group(1))
            if value:
                preferences = self._merge_unique(preferences, [value], limit=8)
        user["preferencias"] = preferences

        goals = list(user.get("goals", []))
        goal_patterns = [
            r"\bquero\s+(.+?)(?:[,.!?]|$)",
            r"\bmeu objetivo [eé]\s+(.+?)(?:[,.!?]|$)",
            r"\bpreciso\s+(.+?)(?:[,.!?]|$)",
        ]
        for pattern in goal_patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if not match:
                continue
            value = self._clean_fact(match.group(1))
            if value:
                goals = self._merge_unique(goals, [value], limit=6)
        user["goals"] = goals

        topics = self._extract_topics(message)
        user["recurring_topics"] = self._merge_unique(list(user.get("recurring_topics", [])), topics, limit=8)
        memory_store["user"] = normalize_user_profile(user)

    def _answer_from_memory(self, memory_store: dict[str, object], message: str) -> str:
        user = normalize_user_profile(memory_store.get("user", {}))
        normalized = self._normalize_text(message)
        nome = str(user.get("nome", "")).strip()
        trabalho = str(user.get("trabalho", "")).strip()

        if any(pattern in normalized for pattern in ("qual e meu nome", "qual e o meu nome", "quem sou eu", "voce lembra meu nome")):
            return f"Seu nome é {nome}." if nome else "Ainda nao sei seu nome."

        if any(pattern in normalized for pattern in ("com o que eu trabalho", "qual meu trabalho", "voce lembra com o que eu trabalho")):
            return f"Você trabalha com {trabalho}." if trabalho else "Ainda nao sei com o que voce trabalha."

        if "quais sao meus objetivos" in normalized or "lembra meus objetivos" in normalized:
            goals = user.get("goals", [])
            if goals:
                return "Seus objetivos atuais incluem: " + "; ".join(str(goal) for goal in goals) + "."
            return "Ainda nao tenho objetivos suficientes registrados sobre voce."

        return ""

    def _acknowledge_user_facts(self, memory_store: dict[str, object], message: str) -> str:
        user = normalize_user_profile(memory_store.get("user", {}))
        normalized = self._normalize_text(message)
        nome = str(user.get("nome", "")).strip()
        trabalho = str(user.get("trabalho", "")).strip()

        if any(phrase in normalized for phrase in ("meu nome e", "meu nome é", "eu sou", "trabalho com", "eu trabalho com")):
            if nome and trabalho:
                return f"Entendi. Vou lembrar que seu nome é {nome} e que voce trabalha com {trabalho}."
            if nome:
                return f"Entendi. Vou lembrar que seu nome é {nome}."
            if trabalho:
                return f"Entendi. Vou lembrar que voce trabalha com {trabalho}."
        return ""

    def _predict_intent(self, message: str) -> str:
        normalized = self._normalize_text(message)

        if re.match(r"^(ola|oi|bom dia|boa tarde|boa noite)(\b|[!,.?\s])", normalized):
            return "saudacao"
        if any(token in normalized for token in ("pros e contras", "vantagens e desvantagens", " vs ", " versus ", "compare", "analise ")):
            return "comparativo"
        if any(token in normalized for token in ("plano de negocio", "modelo de negocio", "crie um plano", "monte um plano")):
            return "planejamento"
        if any(token in normalized for token in ("ideias de startup", "ideia de startup", "me de 3 ideias", "gere ideias")):
            return "ideacao"
        if any(token in normalized for token in ("devo", "vale a pena", "qual e melhor", "o que eu faco", "o que fazer")):
            return "decision"
        if any(token in normalized for token in ("dinheiro", "negocio", "renda", "ganhar dinheiro")):
            return "dinheiro"
        if any(token in normalized for token in ("quero aprender", "por onde comeco", "programacao", "estudar")):
            return "aprendizado"
        if any(token in normalized for token in ("conselho", "dica", "como melhorar")):
            return "conselho"
        if any(token in normalized for token in ("o que e", "oque e", "explique", "como funciona", "me diga o que e")):
            return "explicacao"
        if any(token in normalized for token in ("quem e voce", "como voce funciona", "como voce responde")):
            return "pessoal"
        if "?" in message:
            return "pergunta_direta"
        return "conversa"
    @staticmethod
    def _normalize_text(value: str) -> str:
        repaired = BrainOrchestrator._repair_text(value)
        normalized = unicodedata.normalize("NFD", repaired)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return re.sub(r"\s+", " ", normalized.strip().lower())

    @staticmethod
    def _merge_unique(current: list[str], new_values: list[str], limit: int) -> list[str]:
        combined = list(current)
        seen = {item.casefold() for item in current}
        for value in new_values:
            cleaned = BrainOrchestrator._repair_text(str(value).strip())
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            combined.append(cleaned)
        return combined[-limit:]

    @staticmethod
    def _clean_name(value: str) -> str:
        cleaned = re.split(r"\s+e\s+|,|\.|;|!|\?", value, maxsplit=1)[0].strip(" -")
        if len(cleaned) < 2:
            return ""
        if any(bad in cleaned.casefold() for bad in ("gosto", "prefiro", "quero", "trabalho")):
            return ""
        return cleaned.title()

    @staticmethod
    def _clean_fact(value: str) -> str:
        cleaned = re.split(r",|\.|;|!|\?", value, maxsplit=1)[0].strip(" -")
        return BrainOrchestrator._repair_text(cleaned)

    def _extract_topics(self, message: str) -> list[str]:
        normalized = self._normalize_text(message)
        known_topics = [
            "ia",
            "inteligencia artificial",
            "machine learning",
            "blockchain",
            "bitcoin",
            "criptomoeda",
            "python",
            "rust",
            "startup",
            "delivery",
            "programacao",
            "negocio",
        ]
        return [topic for topic in known_topics if topic in normalized]

    def _generate_session_title(self, turns: list[dict[str, Any]], history: object) -> str:
        if isinstance(turns, list):
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                message = turn.get("message")
                if isinstance(message, str) and message.strip():
                    return self._short_session_title(message)

        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                if item.get("role") != "user":
                    continue
                content = item.get("content")
                if isinstance(content, str) and content.strip():
                    return self._short_session_title(content)

        return "Nova conversa"

    @staticmethod
    def _short_session_title(value: str) -> str:
        cleaned = BrainOrchestrator._repair_text(value).replace("\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        if not cleaned:
            return "Nova conversa"
        if len(cleaned) <= SESSION_TITLE_LIMIT:
            return cleaned
        return cleaned[: SESSION_TITLE_LIMIT - 1].rstrip() + "…"

    def _ensure_evolution_files(self, scoped_paths: BrainPaths) -> None:
        scoped_paths.evolution_dir.mkdir(parents=True, exist_ok=True)
        scoped_paths.snapshots_dir.mkdir(parents=True, exist_ok=True)

        default_state = {
            "version": 1,
            "last_update": None,
            "adjustments": [],
            "params": {
                "max_length_threshold": 500,
                "direct_memory_strictness": 0.5,
                "complex_prompt_word_threshold": 20,
                "heuristic_success_floor": 0.72,
                "llm_success_floor": 0.68,
                "prefer_llm_margin": 0.05,
            },
            "registry_overrides": {},
            "feedback_scores": {},
            "strategies": {},
            "intent_profiles": {},
            "category_scores": {},
        }
        if not scoped_paths.strategy_state_path.exists():
            scoped_paths.strategy_state_path.write_text(
                json.dumps(default_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        snapshot_v1 = scoped_paths.snapshots_dir / "strategy_v1.json"
        if not snapshot_v1.exists():
            snapshot_v1.write_text(
                json.dumps(default_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not scoped_paths.loop_log_path.exists():
            scoped_paths.loop_log_path.write_text("[]", encoding="utf-8")

    def _load_strategy_state(self, scoped_paths: BrainPaths) -> dict[str, Any]:
        self._ensure_evolution_files(scoped_paths)
        default_state = {
            "version": 1,
            "last_update": None,
            "adjustments": [],
            "params": {
                "max_length_threshold": 500,
                "direct_memory_strictness": 0.5,
                "complex_prompt_word_threshold": 20,
                "heuristic_success_floor": 0.72,
                "llm_success_floor": 0.68,
                "prefer_llm_margin": 0.05,
            },
            "registry_overrides": {},
            "feedback_scores": {},
            "strategies": {},
            "intent_profiles": {},
            "category_scores": {},
        }
        try:
            raw = scoped_paths.strategy_state_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict) and parsed:
                merged = dict(default_state)
                merged.update(parsed)
                merged["params"] = {**default_state["params"], **dict(parsed.get("params", {}))}
                return merged
        except Exception:
            pass
        return default_state

    def _update_evolution_state(
        self,
        scoped_paths: BrainPaths,
        hybrid_memory: HybridMemory,
        strategy_updater: StrategyUpdater,
        learning_data: dict[str, object],
    ) -> dict[str, Any]:
        current_strategy = self._load_strategy_state(scoped_paths)
        evaluations = learning_data.get("evaluations", []) if isinstance(learning_data, dict) else []
        if not isinstance(evaluations, list):
            evaluations = []
        analysis = self.analyzer.analyze(
            evaluations[-40:],
            strategy_stats=learning_data.get("strategy_stats", {}) if isinstance(learning_data, dict) else {},
            explicit_feedback=learning_data.get("explicit_feedback", []) if isinstance(learning_data, dict) else [],
        )
        updated_strategy = strategy_updater.update(
            current_strategy=current_strategy,
            analysis=analysis,
            learning_data=learning_data if isinstance(learning_data, dict) else {},
        )
        if not updated_strategy:
            updated_strategy = current_strategy

        scoped_paths.strategy_state_path.write_text(
            json.dumps(updated_strategy, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        loop_log: list[dict[str, Any]] = []
        if scoped_paths.loop_log_path.exists():
            try:
                raw = scoped_paths.loop_log_path.read_text(encoding="utf-8").strip()
                parsed = json.loads(raw) if raw else []
                if isinstance(parsed, list):
                    loop_log = parsed
            except Exception:
                loop_log = []

        loop_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluation_count": len(evaluations),
                "analysis": analysis,
                "strategy_version": int(updated_strategy.get("version", 1)),
                "strategy_summary": updated_strategy.get("strategies", {}),
                "intent_profiles": updated_strategy.get("intent_profiles", {}),
                "category_scores": updated_strategy.get("category_scores", {}),
            }
        )
        scoped_paths.loop_log_path.write_text(
            json.dumps(loop_log[-50:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        strategy_stats = learning_data.get("strategy_stats", {}) if isinstance(learning_data, dict) else {}
        if not isinstance(strategy_stats, dict):
            strategy_stats = {}
        strategy_stats["current_version"] = int(updated_strategy.get("version", 1))
        learning_data["strategy_stats"] = strategy_stats
        learning_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        hybrid_memory.learning_path.write_text(
            json.dumps(learning_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return updated_strategy






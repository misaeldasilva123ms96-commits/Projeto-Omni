from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brain.memory.hybrid import HybridMemory
from brain.memory.store import (
    DEFAULT_HISTORY_LIMIT,
    append_history,
    load_memory_store,
    save_memory_store,
)
from brain.registry import describe_agents, describe_capabilities, recommend_capabilities
from brain.runtime.session_store import SessionStore
from brain.runtime.transcript_store import TranscriptStore
from brain.swarm.swarm_orchestrator import SwarmOrchestrator


SAFE_FALLBACK_RESPONSE = "Nao consegui processar isso ainda, mas estou aprendendo."
SUBPROCESS_TIMEOUT_SECONDS = 10
DEFAULT_SESSION_ID = "python-session"


@dataclass
class BrainPaths:
    root: Path
    python_root: Path
    memory_json: Path
    memory_dir: Path
    transcripts_dir: Path
    sessions_dir: Path
    js_runner: Path
    swarm_log: Path

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
        return cls(
            root=project_root,
            python_root=python_root,
            memory_json=Path(os.getenv("MEMORY_JSON_PATH", str(python_root / "memory.json"))),
            memory_dir=Path(os.getenv("MEMORY_DIR", str(python_root / "memory"))),
            transcripts_dir=Path(os.getenv("TRANSCRIPTS_DIR", str(python_root / "transcripts"))),
            sessions_dir=Path(
                os.getenv(
                    "SESSIONS_DIR",
                    str(python_root / "brain" / "runtime" / "sessions"),
                )
            ),
            js_runner=project_root / "js-runner" / "queryEngineRunner.js",
            swarm_log=python_root / "brain" / "runtime" / "swarm_log.json",
        )


class BrainOrchestrator:
    def __init__(self, paths: BrainPaths) -> None:
        self.paths = paths
        self.hybrid_memory = HybridMemory(paths.memory_dir)
        self.transcript_store = TranscriptStore(paths.transcripts_dir)
        self.session_store = SessionStore(paths.sessions_dir)
        self.swarm_orchestrator = SwarmOrchestrator(paths.swarm_log)

    def run(self, message: str) -> str:
        session_id = self._session_id()
        memory_store = load_memory_store(
            self.paths.memory_json,
            history_limit=DEFAULT_HISTORY_LIMIT,
        )
        transcript_history = self.transcript_store.load_recent_history(
            session_id,
            limit=DEFAULT_HISTORY_LIMIT,
        )
        memory_store["history"] = self._merge_recent_history(
            transcript_history,
            memory_store.get("history", [])
            if isinstance(memory_store.get("history", []), list)
            else [],
        )

        if not message.strip():
            return SAFE_FALLBACK_RESPONSE

        self._extract_user_learning(memory_store, message)
        append_history(
            memory_store,
            "user",
            message,
            history_limit=DEFAULT_HISTORY_LIMIT,
        )

        available_capabilities = describe_capabilities()
        suggested_capabilities = recommend_capabilities(message)
        predicted_intent = self._predict_intent(message)
        summary = self.summarize_history(memory_store.get("history", []))
        direct_response = self._answer_from_memory(memory_store, message)

        swarm_result: dict[str, Any] = {
            "response": direct_response,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
        }

        if not direct_response:
            swarm_result = asyncio.run(
                self.swarm_orchestrator.run(
                    message=message,
                    session_id=session_id,
                    memory_store=memory_store,
                    history=memory_store.get("history", []),
                    summary=summary,
                    capabilities=available_capabilities,
                    executor=lambda payload: self._async_node_execution(
                        message=message,
                        memory_store=memory_store,
                        available_capabilities=available_capabilities,
                        session_id=session_id,
                        swarm_payload=payload,
                    ),
                )
            )

        response = str(swarm_result.get("response", "")).strip() or SAFE_FALLBACK_RESPONSE

        append_history(
            memory_store,
            "assistant",
            response,
            history_limit=DEFAULT_HISTORY_LIMIT,
        )
        safe_store = save_memory_store(
            self.paths.memory_json,
            memory_store,
            history_limit=DEFAULT_HISTORY_LIMIT,
        )
        self.hybrid_memory.sync_from_store(safe_store)
        self.hybrid_memory.record_learning(
            message=message,
            response=response,
            intent=str(swarm_result.get("intent", predicted_intent)),
            capabilities=suggested_capabilities,
        )
        self.transcript_store.append_turn(session_id, message, response)

        session_payload = {
            "session_id": session_id,
            "history": safe_store.get("history", []),
            "user": safe_store.get("user", {}),
            "summary": self.summarize_history(safe_store.get("history", [])),
            "capabilities": available_capabilities,
            "agent_registry": describe_agents(),
            "agent_trace": swarm_result.get("agent_trace", []),
            "swarm": {
                "intent": swarm_result.get("intent", predicted_intent),
                "delegates": swarm_result.get("delegates", []),
                "memory_signal": swarm_result.get("memory_signal", {}),
            },
        }
        self.session_store.save(session_id, session_payload)
        return response

    async def _async_node_execution(
        self,
        *,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        session_id: str,
        swarm_payload: dict[str, Any],
    ) -> str:
        return self._call_node_query_engine(
            message=message,
            memory_store=memory_store,
            available_capabilities=available_capabilities,
            session_id=session_id,
            extra_session={
                "swarm_request": swarm_payload,
            },
        )

    def _session_id(self) -> str:
        configured = os.getenv("AI_SESSION_ID", "").strip()
        return configured or DEFAULT_SESSION_ID

    def _resolve_node_bin(self) -> str | None:
        configured = os.getenv("NODE_BIN", "").strip()
        if configured:
            return configured
        return shutil.which("node")

    def _call_node_query_engine(
        self,
        *,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        session_id: str,
        extra_session: dict[str, Any] | None = None,
    ) -> str:
        node_bin = self._resolve_node_bin()
        if not node_bin or not self.paths.js_runner.exists():
            return ""

        session_payload = self.session_store.load(session_id)
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
                [node_bin, str(self.paths.js_runner), payload],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
                cwd=str(self.paths.root),
            )
        except Exception:
            return ""

        if completed.returncode != 0:
            return ""

        return completed.stdout.strip()

    @staticmethod
    def summarize_history(history: object) -> str:
        if not isinstance(history, list) or len(history) <= 4:
            return ""

        summary_parts: list[str] = []
        for item in history[-4:]:
            if not isinstance(item, dict):
                continue
            role = "Usuario" if item.get("role") == "user" else "Assistente"
            content = str(item.get("content", "")).strip()
            if content:
                summary_parts.append(f"{role}: {content}")
        return "\n".join(summary_parts)

    @staticmethod
    def _merge_recent_history(
        transcript_history: list[dict[str, str]],
        memory_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if transcript_history:
            return transcript_history[-DEFAULT_HISTORY_LIMIT:]
        return memory_history[-DEFAULT_HISTORY_LIMIT:]

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip().lower())
        return re.sub(r"[?.!,:;]+$", "", normalized).strip()

    def _clean_extracted_name(self, raw_name: str) -> str:
        name = raw_name.strip()
        if not name:
            return ""
        name = re.split(r"\s+e\s+|,|\.", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if len(name) < 2:
            return ""

        invalid_tokens = {"gosto", "prefiro", "quero"}
        normalized = self._normalize_text(name)
        if any(token in normalized.split() for token in invalid_tokens):
            return ""
        return name

    def _extract_user_learning(self, memory_store: dict[str, object], message: str) -> None:
        user = memory_store.setdefault("user", {})
        if not isinstance(user, dict):
            user = {"nome": "", "preferencias": []}
            memory_store["user"] = user

        preferencias = user.get("preferencias", [])
        if not isinstance(preferencias, list):
            preferencias = []
            user["preferencias"] = preferencias

        nome_match = re.search(
            r"\bmeu nome [eé]\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})",
            message,
            flags=re.IGNORECASE,
        )
        if nome_match:
            cleaned_name = self._clean_extracted_name(nome_match.group(1).strip(" .,!?:;"))
            if cleaned_name:
                user["nome"] = cleaned_name

        sou_match = re.search(
            r"\beu sou\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})",
            message,
            flags=re.IGNORECASE,
        )
        if sou_match and not str(user.get("nome", "")).strip():
            possible_identity = self._clean_extracted_name(sou_match.group(1).strip(" .,!?:;"))
            if possible_identity and "um " not in possible_identity.lower() and "uma " not in possible_identity.lower():
                user["nome"] = possible_identity

        pref_match = re.search(r"\bprefiro\s+(.+)$", message, flags=re.IGNORECASE)
        if pref_match:
            preference = pref_match.group(1).strip(" .,!?:;")
            if preference:
                existing = {str(item).lower(): item for item in preferencias}
                if preference.lower() not in existing:
                    preferencias.append(preference)
                user["preferencias"] = preferencias

    def _answer_from_memory(self, memory_store: dict[str, object], message: str) -> str:
        user = memory_store.get("user", {})
        if not isinstance(user, dict):
            return ""

        normalized = self._normalize_text(message)
        nome = str(user.get("nome", "")).strip()
        if normalized in {
            "qual meu nome",
            "qual e meu nome",
            "qual é meu nome",
            "quem sou eu",
            "quem eu sou",
        }:
            if nome:
                return f"Seu nome é {nome}."
            return "Ainda nao sei seu nome."
        return ""

    def _predict_intent(self, message: str) -> str:
        lowered = self._normalize_text(message)
        if any(term in lowered for term in ("devo", " qual e melhor", " o que fazer", " ou ")):
            return "decision"
        if any(term in lowered for term in ("dinheiro", "negocio", "renda", "ganhar dinheiro")):
            return "dinheiro"
        if any(term in lowered for term in ("aprender", "programacao", "por onde comeco", "por onde começo")):
            return "aprendizado"
        if any(term in lowered for term in ("como funciona", "o que e", "o que é", "explique")):
            return "explicacao"
        if any(term in lowered for term in ("quem e voce", "quem é você", "como voce responde")):
            return "pessoal"
        return "conversa"

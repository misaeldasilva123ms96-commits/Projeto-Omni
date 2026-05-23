from __future__ import annotations

import hashlib
from typing import Any

from brain.runtime.language.oil_schema import OILRequest
from brain.runtime.memory.models import MemorySignal, UnifiedMemoryContext


class UnifiedMemoryLayer:
    """Phase 32 runtime-facing unified memory interface for reasoning enrichment."""

    def __init__(
        self,
        *,
        transcript_store: Any,
        memory_facade: Any,
        working_store: Any,
        decision_store: Any,
        evidence_store: Any,
        run_registry: Any | None = None,
    ) -> None:
        self.transcript_store = transcript_store
        self.memory_facade = memory_facade
        self.working_store = working_store
        self.decision_store = decision_store
        self.evidence_store = evidence_store
        self.run_registry = run_registry

    def build_reasoning_context(
        self,
        *,
        session_id: str,
        run_id: str | None,
        query: str,
        oil_request: OILRequest,
        memory_store: dict[str, object] | None = None,
        max_items: int = 8,
    ) -> UnifiedMemoryContext:
        safe_max = max(1, min(20, int(max_items or 8)))
        short_term = self._collect_short_term(session_id=session_id, query=query, memory_store=memory_store)
        long_term = self._collect_long_term(query=query, memory_store=memory_store)
        semantic = self._collect_semantic(oil_request=oil_request, query=query)
        operational = self._collect_operational(session_id=session_id, run_id=run_id)
        candidates = self._to_candidates(short_term=short_term, long_term=long_term, semantic=semantic, operational=operational)
        ranked = self._rank(candidates=candidates, query=query)
        selected = ranked[:safe_max]
        context_id = hashlib.sha1(f"{session_id}:{run_id or ''}:{query}".encode("utf-8")).hexdigest()[:16]
        sources_used = sorted({item.memory_type for item in selected})
        summary = self._summary(selected=selected, total=len(candidates))
        score_values = [item.score for item in selected]
        return UnifiedMemoryContext(
            context_id=f"mem-{context_id}",
            session_id=session_id,
            run_id=run_id,
            query=query,
            sources_used=sources_used,
            selected_signals=selected,
            selected_count=len(selected),
            total_candidates=len(candidates),
            context_summary=summary,
            short_term=short_term[:safe_max],
            long_term=long_term[:safe_max],
            semantic=semantic[:safe_max],
            operational=operational[:safe_max],
            scoring={
                "max_score": max(score_values) if score_values else 0.0,
                "min_score": min(score_values) if score_values else 0.0,
                "strategy": "deterministic_relevance_rank",
            },
        )

    def _collect_short_term(
        self,
        *,
        session_id: str,
        query: str,
        memory_store: dict[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        short: list[dict[str, Any]] = []
        transcript = self.transcript_store.load_recent_history(session_id, limit=6)
        for idx, item in enumerate(transcript):
            short.append(
                {
                    "source": "transcript",
                    "signal_id": f"transcript-{idx}",
                    "summary": str(item.get("content", "")).strip()[:180],
                    "metadata": {"role": item.get("role")},
                }
            )
        working = self.working_store.load_session(session_id)
        if isinstance(working, dict) and working:
            short.append(
                {
                    "source": "working_memory",
                    "signal_id": f"working-{session_id}",
                    "summary": str(working.get("current_task_summary", "")).strip()[:180],
                    "metadata": {
                        "execution_strategy": working.get("current_execution_strategy"),
                        "context_budget_level": working.get("context_budget_level"),
                    },
                }
            )
        if isinstance(memory_store, dict):
            for idx, item in enumerate(memory_store.get("history", [])[-4:]):
                if not isinstance(item, dict):
                    continue
                short.append(
                    {
                        "source": "store_history",
                        "signal_id": f"store-{idx}",
                        "summary": str(item.get("content", "")).strip()[:180],
                        "metadata": {"role": item.get("role")},
                    }
                )
        return short

    @staticmethod
    def _collect_long_term(
        *,
        query: str,
        memory_store: dict[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(memory_store, dict):
            return []
        long_term = memory_store.get("long_term", {})
        if not isinstance(long_term, dict):
            return []
        items: list[dict[str, Any]] = []
        for key, value in list(long_term.items())[:10]:
            summary = f"{key}: {str(value)[:160]}"
            items.append(
                {
                    "source": "long_term_store",
                    "signal_id": f"lt-{key}",
                    "summary": summary,
                    "metadata": {"key": key},
                }
            )
        return items

    def _collect_semantic(self, *, oil_request: OILRequest, query: str) -> list[dict[str, Any]]:
        semantic: list[dict[str, Any]] = []
        subjects: list[str] = []
        if oil_request.intent:
            subjects.append(str(oil_request.intent))
        topic = str((oil_request.entities or {}).get("topic", "")).strip()
        if topic:
            subjects.append(topic)
        first_token = str(query or "").strip().split(" ")[0] if str(query or "").strip() else ""
        if first_token:
            subjects.append(first_token.lower())
        for subject in subjects[:3]:
            try:
                facts = self.memory_facade.get_semantic_facts(subject, limit=3)
            except Exception:
                facts = []
            for fact in facts:
                semantic.append(
                    {
                        "source": "semantic_memory",
                        "signal_id": str(getattr(fact, "fact_id", "")),
                        "summary": (
                            f"{getattr(fact, 'subject', '')} "
                            f"{getattr(fact, 'predicate', '')} "
                            f"{getattr(fact, 'object_value', '')}"
                        ).strip()[:200],
                        "metadata": {"confidence": getattr(fact, "confidence", 0.0)},
                    }
                )
        return semantic

    def _collect_operational(self, *, session_id: str, run_id: str | None) -> list[dict[str, Any]]:
        operational: list[dict[str, Any]] = []
        try:
            decisions = self.decision_store.find_decisions(session_id=session_id, limit=5)
        except Exception:
            decisions = []
        for idx, item in enumerate(decisions):
            if not isinstance(item, dict):
                continue
            operational.append(
                {
                    "source": "decision_memory",
                    "signal_id": str(item.get("entry_id", f"decision-{idx}")),
                    "summary": (
                        f"{item.get('decision_type','')} {item.get('task_type','')} "
                        f"{item.get('reason','')}"
                    ).strip()[:200],
                    "metadata": {"reason_code": item.get("reason_code"), "task_type": item.get("task_type")},
                }
            )
        try:
            evidence = self.evidence_store.get_evidence(session_id=session_id, task_id=None, limit=5)
        except Exception:
            evidence = []
        for idx, item in enumerate(evidence):
            if not isinstance(item, dict):
                continue
            operational.append(
                {
                    "source": "evidence_memory",
                    "signal_id": str(item.get("entry_id", f"evidence-{idx}")),
                    "summary": f"evidence task_type={item.get('task_type','')} {item.get('evidence',{})}"[:200],
                    "metadata": {"task_type": item.get("task_type")},
                }
            )
        if self.run_registry is None:
            return operational
        try:
            summary = self.run_registry.get_resolution_summary()
            operational.append(
                {
                    "source": "governance_summary",
                    "signal_id": "resolution-summary",
                    "summary": f"resolution_counts={summary.get('resolution_counts', {})}",
                    "metadata": {"resolution_counts": summary.get("resolution_counts", {})},
                }
            )
        except Exception:
            pass
        try:
            recent = self.run_registry.recent_resolution_events(limit=5)
        except Exception:
            recent = []
        for idx, item in enumerate(recent):
            if not isinstance(item, dict):
                continue
            operational.append(
                {
                    "source": "resolution_event",
                    "signal_id": f"resolution-{idx}",
                    "summary": (
                        f"{item.get('status','')} {item.get('reason','')} "
                        f"{item.get('source','')}"
                    ).strip()[:200],
                    "metadata": {"status": item.get("status"), "reason": item.get("reason")},
                }
            )
        if run_id:
            try:
                record = self.run_registry.get(run_id)
            except Exception:
                record = None
            if record is not None:
                payload = record.as_dict()
                operational.append(
                    {
                        "source": "run_registry",
                        "signal_id": f"run-{run_id}",
                        "summary": (
                            f"run={payload.get('run_id')} status={payload.get('status')} "
                            f"last_action={payload.get('last_action')}"
                        )[:200],
                        "metadata": {
                            "status": payload.get("status"),
                            "progress_score": payload.get("progress_score"),
                        },
                    }
                )
        return operational

    @staticmethod
    def _to_candidates(
        *,
        short_term: list[dict[str, Any]],
        long_term: list[dict[str, Any]],
        semantic: list[dict[str, Any]],
        operational: list[dict[str, Any]],
    ) -> list[MemorySignal]:
        pool = short_term + long_term + semantic + operational
        candidates: list[MemorySignal] = []
        for item in pool:
            source = str(item.get("source", "memory")).strip() or "memory"
            signal_id = str(item.get("signal_id", "")).strip() or f"{source}-signal"
            summary = str(item.get("summary", "")).strip()
            if not summary:
                continue
            candidates.append(
                MemorySignal(
                    memory_type=source,
                    signal_id=signal_id,
                    summary=summary,
                    score=0.0,
                    metadata=dict(item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {}),
                )
            )
        return candidates

    @staticmethod
    def _rank(*, candidates: list[MemorySignal], query: str) -> list[MemorySignal]:
        lowered_query = str(query or "").lower()
        query_tokens = {token for token in lowered_query.split() if len(token) > 2}
        type_weight = {
            "semantic_memory": 0.25,
            "working_memory": 0.2,
            "transcript": 0.17,
            "store_history": 0.15,
            "resolution_event": 0.14,
            "governance_summary": 0.13,
            "run_registry": 0.13,
            "long_term_store": 0.12,
            "decision_memory": 0.16,
            "evidence_memory": 0.17,
        }
        scored: list[MemorySignal] = []
        for index, candidate in enumerate(candidates):
            text = candidate.summary.lower()
            overlap = sum(1 for token in query_tokens if token in text)
            overlap_score = min(0.45, overlap * 0.08)
            confidence_hint = 0.0
            if isinstance(candidate.metadata.get("confidence"), (int, float)):
                confidence_hint = min(0.25, max(0.0, float(candidate.metadata.get("confidence")) * 0.25))
            base = type_weight.get(candidate.memory_type, 0.1)
            recency_hint = max(0.0, 0.2 - index * 0.01)
            score = round(min(1.0, base + overlap_score + confidence_hint + recency_hint), 4)
            scored.append(
                MemorySignal(
                    memory_type=candidate.memory_type,
                    signal_id=candidate.signal_id,
                    summary=candidate.summary,
                    score=score,
                    metadata=dict(candidate.metadata),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored

    @staticmethod
    def _summary(*, selected: list[MemorySignal], total: int) -> str:
        if not selected:
            return "No relevant memory signals selected."
        counts: dict[str, int] = {}
        for item in selected:
            counts[item.memory_type] = counts.get(item.memory_type, 0) + 1
        source_summary = ", ".join(f"{key}:{value}" for key, value in sorted(counts.items()))
        return f"Selected {len(selected)} of {total} memory signals ({source_summary})."

from __future__ import annotations

import os
from collections import defaultdict
from uuid import uuid4

from brain.runtime.memory.episodic.models import Episode

from .models import SemanticFact, utc_now_iso


class FactConsolidator:
    def __init__(self) -> None:
        self.min_episodes = max(1, int(os.getenv("OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT", "5") or 5))

    def consolidate(self, *, episodes: list[Episode]) -> list[SemanticFact]:
        grouped: dict[tuple[str, str], list[Episode]] = defaultdict(list)
        for episode in episodes:
            grouped[(episode.event_type, episode.outcome)].append(episode)

        facts: list[SemanticFact] = []
        for (event_type, outcome), bucket in grouped.items():
            if len(bucket) < self.min_episodes:
                continue
            total_for_subject = len([episode for episode in episodes if episode.event_type == event_type]) or 1
            confidence = max(0.0, min(1.0, len(bucket) / total_for_subject))
            goal_types = sorted(
                {
                    str((episode.metadata or {}).get("goal_type", "")).strip()
                    for episode in bucket
                    if str((episode.metadata or {}).get("goal_type", "")).strip()
                }
            )
            now = utc_now_iso()
            facts.append(
                SemanticFact(
                    fact_id=f"semantic-fact-{uuid4()}",
                    subject=event_type,
                    predicate="tends_to_result_in",
                    object_value=outcome,
                    confidence=confidence,
                    source_episode_ids=[episode.episode_id for episode in bucket],
                    goal_types=goal_types,
                    created_at=now,
                    last_reinforced_at=now,
                    metadata={"sample_size": len(bucket)},
                )
            )
        return facts

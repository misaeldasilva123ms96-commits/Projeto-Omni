"""Deterministic local-only relevance search."""

from brain.runtime.external.discovery.models import CandidateSearchResult, DiscoveryCandidate


def search_candidates(
    candidates: tuple[DiscoveryCandidate, ...] | list[DiscoveryCandidate],
    query: str,
    *,
    category: str | None = None,
    limit: int = 20,
) -> tuple[CandidateSearchResult, ...]:
    needle = " ".join(str(query or "").split()).casefold()
    if query and not 2 <= len(needle) <= 100:
        raise ValueError("query must contain 2..100 characters")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    category_needle = str(category or "").strip().casefold()
    ranked: list[CandidateSearchResult] = []
    for candidate in candidates:
        if category_needle and category_needle not in str(candidate.category or "").casefold():
            continue
        fields = (
            candidate.name.casefold(),
            candidate.description.casefold(),
            str(candidate.category or "").casefold(),
            str(candidate.provider or "").casefold(),
        )
        if needle:
            score = 100 if fields[0] == needle else 50 if needle in fields[0] else 0
            score += 20 if needle in fields[2] else 0
            score += 10 if needle in fields[1] else 0
            score += 5 if needle in fields[3] else 0
            if not score:
                continue
        else:
            score = 0
        ranked.append(CandidateSearchResult(candidate, score))
    ranked.sort(
        key=lambda item: (
            -item.relevance_score,
            item.candidate.name.casefold(),
            item.candidate.candidate_id,
        )
    )
    return tuple(ranked[:limit])

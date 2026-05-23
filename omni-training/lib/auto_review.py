from __future__ import annotations

from collections import Counter
from typing import Any

from dataset_quality import duplicate_fingerprint, quality_assessment


def classify_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    duplicate_counts = Counter(duplicate_fingerprint(record) for record in records)
    classified: list[dict[str, Any]] = []
    for record in records:
        enriched = dict(record)
        assessment = quality_assessment(enriched)
        fingerprint = duplicate_fingerprint(enriched)
        if duplicate_counts[fingerprint] > 1 and "duplicate_approx" not in assessment["quality_flags"]:
            assessment["quality_flags"].append("duplicate_approx")
            if assessment["review_action"] == "keep":
                assessment["review_action"] = "review"
        enriched["quality_score"] = float(assessment["quality_score"])
        enriched["quality_flags"] = list(dict.fromkeys(assessment["quality_flags"]))
        enriched["review_action"] = str(assessment["review_action"])
        if enriched["review_action"] == "reject":
            enriched["review_status"] = "rejected"
        elif enriched["review_action"] == "review":
            enriched["review_status"] = "draft"
        else:
            enriched["review_status"] = str(enriched.get("review_status", "") or "reviewed")
        classified.append(enriched)
    return classified


def summarize_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(record.get("review_action", "review") or "review") for record in records)
    return {
        "total_records": len(records),
        "keep": counts.get("keep", 0),
        "review": counts.get("review", 0),
        "reject": counts.get("reject", 0),
    }

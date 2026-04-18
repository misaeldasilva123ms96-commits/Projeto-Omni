from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FeedbackSource = Literal["explicit", "implicit", "mixed", "none"]


@dataclass(slots=True)
class ExplicitFeedback:
    thumb: str | None = None  # "up" | "down" | None
    rating: float | None = None
    task_completed: bool | None = None
    user_correction: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "thumb": self.thumb,
            "rating": self.rating,
            "task_completed": self.task_completed,
            "user_correction": self.user_correction,
        }


@dataclass(slots=True)
class FeedbackBundle:
    explicit: ExplicitFeedback
    implicit_tags: list[str] = field(default_factory=list)
    feedback_class: str = "neutral"
    feedback_source: FeedbackSource = "none"

    def as_dict(self) -> dict[str, Any]:
        return {
            "explicit": self.explicit.as_dict(),
            "implicit_tags": list(self.implicit_tags),
            "feedback_class": self.feedback_class,
            "feedback_source": self.feedback_source,
        }


def combine_feedback(
    explicit: ExplicitFeedback | None,
    implicit_tags: list[str],
) -> FeedbackBundle:
    ex = explicit or ExplicitFeedback()
    tags = [str(t).strip() for t in implicit_tags if str(t).strip()]
    has_ex = bool(
        (ex.thumb in ("up", "down"))
        or ex.rating is not None
        or ex.task_completed is not None
        or (ex.user_correction and ex.user_correction.strip())
    )
    has_im = bool(tags)
    if has_ex and has_im:
        src: FeedbackSource = "mixed"
    elif has_ex:
        src = "explicit"
    elif has_im:
        src = "implicit"
    else:
        src = "none"

    fb_class = "neutral"
    if ex.thumb == "down" or "retry_or_correct" in tags or "redo_language" in tags:
        fb_class = "negative"
    elif ex.thumb == "up" or ex.task_completed is True or "productive_continuation" in tags:
        fb_class = "positive"

    return FeedbackBundle(explicit=ex, implicit_tags=tags, feedback_class=fb_class, feedback_source=src)

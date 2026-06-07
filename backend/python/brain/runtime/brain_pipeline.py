from __future__ import annotations

import time
import logging
from typing import Any

from brain.runtime.pipeline_stage import PipelineResult

logger = logging.getLogger(__name__)


class BrainPipeline:
    def __init__(self, stages: list[Any]) -> None:
        self._stages = list(stages)

    def add_stage(self, stage: Any) -> None:
        self._stages.append(stage)

    async def run(self, initial_context: dict[str, Any]) -> PipelineResult:
        context = dict(initial_context)
        start = time.monotonic()

        for idx, stage in enumerate(self._stages):
            stage_name = getattr(stage, "__class__", type(stage)).__name__
            stage_start = time.monotonic()

            try:
                if hasattr(stage, "run"):
                    result = await stage.run(context)
                elif callable(stage):
                    result = await stage(context)
                else:
                    continue

                if isinstance(result, dict):
                    context.update(result)
                elif isinstance(result, PipelineResult):
                    if not result.success:
                        return result
                    if result.data:
                        context.update(result.data)

            except Exception as exc:
                logger.exception("Pipeline stage %s failed: %s", stage_name, exc)
                return PipelineResult(
                    success=False,
                    data={"stage": stage_name, "error": str(exc)},
                    error=f"{stage_name} failed: {exc}",
                )

        elapsed = int((time.monotonic() - start) * 1000)
        context["_pipeline_duration_ms"] = elapsed
        return PipelineResult(success=True, data=context)

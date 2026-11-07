"""Composable six-stage scientific workflow.

The pipeline orchestrates domain-specific functions; it does not invent or
replace scientific equations. Each challenge supplies its own data source,
validation rules, cleaning, analysis, verification, and visualization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class PipelineError(RuntimeError):
    """A pipeline stage failed; stage identifies where processing stopped."""

    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(f"{stage}: {message}")


@dataclass(frozen=True)
class PipelineResult:
    """Output and auditable list of completed stages."""

    data: Any
    verification: Any
    visualization: Any
    completed_stages: tuple[str, ...]


def run_pipeline(
    acquire: Callable[[], Any],
    validate: Callable[[Any], Any],
    clean: Callable[[Any], Any],
    process: Callable[[Any], Any],
    verify: Callable[[Any], Any],
    visualize: Callable[[Any], Any],
) -> PipelineResult:
    """Run Acquire → Validate → Clean → Process → Verify → Visualize.

    Each function receives the previous stage's output. The verifier must
    return exactly True; False or an ambiguous result stops the pipeline.
    Exceptions are wrapped in PipelineError with the failing stage name.
    """
    stages: list[str] = []

    def execute(name: str, function: Callable[..., Any], value: Any = None,
                has_input: bool = True) -> Any:
        try:
            result = function(value) if has_input else function()
        except Exception as exc:
            raise PipelineError(name, str(exc)) from exc
        stages.append(name)
        return result

    acquired = execute("acquire", acquire, has_input=False)
    validated = execute("validate", validate, acquired)
    cleaned = execute("clean", clean, validated)
    processed = execute("process", process, cleaned)
    verification = execute("verify", verify, processed)
    if verification is not True:
        raise PipelineError("verify", "verification must return exactly True")
    visualization = execute("visualize", visualize, processed)

    return PipelineResult(
        data=processed,
        verification=verification,
        visualization=visualization,
        completed_stages=tuple(stages),
    )

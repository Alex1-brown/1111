"""Canonical workflow principle for the NASA Universal Science Core.

This is an architectural workflow, not a universal physical law or one
mathematical equation. Domain-specific calculations belong in dedicated
analysis modules and must preserve units, provenance, and uncertainty.
"""

UNIVERSAL_SCIENCE_PIPELINE = (
    "acquire",
    "validate",
    "clean",
    "process",
    "verify",
    "visualize",
)

PIPELINE_LABELS_RU = (
    "Получить данные",
    "Проверить данные",
    "Очистить данные",
    "Обработать данные",
    "Проверить результат",
    "Визуализировать результат",
)

PIPELINE_LABELS_EN = (
    "Acquire data",
    "Validate data",
    "Clean data",
    "Process data",
    "Verify results",
    "Visualize results",
)


def describe_pipeline(language: str = "en") -> tuple[str, ...]:
    """Return the canonical workflow labels in Russian or English."""
    return PIPELINE_LABELS_RU if language.lower().startswith("ru") else PIPELINE_LABELS_EN

"""Dependency-free SVG charts for reproducible scientific reports."""
from __future__ import annotations

from html import escape
from math import ceil, isfinite
from typing import Iterable


def render_line_chart(
    points: Iterable[tuple[str, float]],
    title: str,
    y_label: str,
    width: int = 1000,
    height: int = 600,
) -> str:
    """Render a labelled SVG line chart from ordered (x-label, y-value) pairs."""
    rows = [(str(label), float(value)) for label, value in points]
    if width < 400 or height < 300:
        raise ValueError("Chart dimensions are too small.")
    if any(not isfinite(value) for _, value in rows):
        raise ValueError("Chart values must be finite.")
    margin_left, margin_right, margin_top, margin_bottom = 100, 40, 75, 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    safe_title, safe_y = escape(title), escape(y_label)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2:.1f}" y="38" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">{safe_title}</text>',
    ]
    if not rows:
        parts.append(f'<text x="{width / 2:.1f}" y="{height / 2:.1f}" text-anchor="middle" font-family="Arial" font-size="18">No valid observations</text>')
        parts.append("</svg>")
        return "\n".join(parts)

    values = [value for _, value in rows]
    low, high = min(values), max(values)
    if low == high:
        padding = max(abs(low) * 0.05, 1.0)
        low, high = low - padding, high + padding
    else:
        padding = (high - low) * 0.08
        low, high = low - padding, high + padding

    def y_coord(value: float) -> float:
        return margin_top + (high - value) / (high - low) * plot_height

    for tick in range(6):
        value = low + (high - low) * tick / 5
        y = y_coord(value)
        parts.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width-margin_right}" y2="{y:.2f}" stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left-12}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="13">{value:.3g}</text>')

    if len(rows) == 1:
        x_positions = [margin_left + plot_width / 2]
    else:
        x_positions = [margin_left + i * plot_width / (len(rows) - 1) for i in range(len(rows))]
    coordinates = [(x, y_coord(value)) for x, value in zip(x_positions, values)]
    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    parts.append(f'<polyline points="{polyline}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    for x, y in coordinates:
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#1d4ed8"/>')

    label_step = max(1, ceil(len(rows) / 12))
    for index, (label, x) in enumerate(zip([row[0] for row in rows], x_positions)):
        if index % label_step == 0 or index == len(rows) - 1:
            parts.append(f'<text x="{x:.2f}" y="{height-margin_bottom+28}" text-anchor="middle" font-family="Arial" font-size="13">{escape(label)}</text>')

    parts.extend([
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height-margin_bottom}" stroke="#333333"/>',
        f'<line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-margin_right}" y2="{height-margin_bottom}" stroke="#333333"/>',
        f'<text x="{width/2:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="16">Year</text>',
        f'<text x="26" y="{height/2:.1f}" transform="rotate(-90 26 {height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="16">{safe_y}</text>',
        "</svg>",
    ])
    return "\n".join(parts)

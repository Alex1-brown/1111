"""Self-contained offline HTML report for Earth System Trend Detective."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Iterable


def _blend(base: tuple[int, int, int], strength: float) -> str:
    strength = max(0.0, min(1.0, strength))
    rgb = tuple(round(255 - (255 - channel) * strength) for channel in base)
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def _svg(path: str | Path | None) -> str:
    if not path:
        return "<p class='muted'>Chart unavailable.</p>"
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "<p class='muted'>Chart unavailable.</p>"
    if "<svg" not in content[:500]:
        return "<p class='muted'>Chart file is not a valid SVG.</p>"
    return content


def render_html_report(
    report: dict[str, Any],
    pixel_trends: Iterable[dict[str, Any]] = (),
    chart_paths: dict[str, str] | None = None,
) -> str:
    """Render an offline HTML report with a clickable pixel-trend grid."""
    chart_paths = chart_paths or {}
    ndvi = report.get("modis_ndvi", {})
    power = report.get("power_time_series_analysis", {})
    cross = report.get("cross_source_monthly_analysis", {})
    grid = ndvi.get("grid", {})
    nrows, ncols = int(grid.get("nrows", 0)), int(grid.get("ncols", 0))
    trends = list(pixel_trends)
    by_pixel = {(int(row["row"]), int(row["column"])): row for row in trends}
    slopes = [
        abs(float(row["sen_slope_ndvi_per_year"]))
        for row in trends if row.get("sen_slope_ndvi_per_year") is not None
    ]
    max_abs_slope = max(slopes, default=0.0) or 1.0

    cells = []
    for row in range(nrows):
        for column in range(ncols):
            trend = by_pixel.get((row, column))
            if not trend:
                cells.append(
                    f"<button class='pixel missing' type='button' "
                    f"aria-label='Pixel {row},{column}: no trend estimate' "
                    f"data-info='Pixel {row},{column}: no trend estimate'>·</button>"
                )
                continue
            slope = trend.get("sen_slope_ndvi_per_year")
            if slope is None:
                color = "#d1d5db"
            else:
                slope = float(slope)
                base = (37, 99, 235) if slope < 0 else (220, 105, 35)
                color = _blend(base, abs(slope) / max_abs_slope)
            q = trend.get("q_value_by")
            q_text = (
                "not estimated (not eligible for adjusted inference)"
                if q is None else f"{float(q):.4g}"
            )
            slope_text = "not available" if slope is None else f"{float(slope):+.5f} NDVI/year"
            ci_lower = trend.get("sen_slope_ci_95_lower_ndvi_per_year")
            ci_upper = trend.get("sen_slope_ci_95_upper_ndvi_per_year")
            ci_text = (
                f"[{float(ci_lower):+.5f}, {float(ci_upper):+.5f}] NDVI/year"
                if ci_lower is not None and ci_upper is not None else "not available"
            )
            ci_method = trend.get("sen_slope_ci_95_method") or "method unavailable"
            years = trend.get("years", "n/a")
            status = trend.get("serial_correlation_status", "not evaluated")
            if trend.get("serial_correlation_adjusted"):
                dependence_text = "Hamed-Rao variance correction applied"
            elif status == "constant_series_no_trend":
                dependence_text = "constant series; no trend inference needed"
            else:
                dependence_text = f"temporal correction not applied ({status})"
            iid_p = trend.get("p_value_iid")
            iid_text = (
                f" Unadjusted iid p-value {float(iid_p):.4g} is shown for reference only."
                if q is None and iid_p is not None else ""
            )
            info = (
                f"Pixel row {row}, column {column}; Sen slope {slope_text}; "
                f"nominal 95% CI {ci_text}; CI method: {ci_method}; BY q-value {q_text}; "
                f"annual observations {years}; {dependence_text}.{iid_text}"
            )
            cells.append(
                f"<button class='pixel' type='button' style='background:{color}' "
                f"aria-label='{html.escape(info, quote=True)}' "
                f"data-info='{html.escape(info, quote=True)}'>{row*ncols+column+1}</button>"
            )
    grid_html = (
        f"<div class='pixel-grid' style='grid-template-columns:repeat({ncols}, minmax(0,1fr))'>"
        + "".join(cells) + "</div>"
        if nrows and ncols else "<p class='muted'>Spatial trend grid unavailable.</p>"
    )

    def metric(value: Any, suffix: str = "") -> str:
        if value is None:
            return "n/a"
        if isinstance(value, float):
            return f"{value:.3f}{suffix}"
        return f"{html.escape(str(value))}{suffix}"

    temp_trend = power.get("descriptive_linear_trends", {}).get("annual_mean_temperature", {})
    precip_trend = power.get("descriptive_linear_trends", {}).get("annual_precipitation_total", {})
    paired_days = power.get("paired_valid_days", "n/a")
    common_months = cross.get("common_months", "n/a")
    trend_period = ndvi.get("trend_period", [])
    trend_period_text = f"{trend_period[0]}–{trend_period[1]}" if len(trend_period) == 2 else "n/a"
    pettitt = ndvi.get("annual_fixed_panel_change_detection", {}).get("pettitt", {})
    change_year = pettitt.get("change_point_year")
    if change_year is None:
        change_year = "not detected"

    charts = []
    for key, title in (
        ("annual_ndvi.svg", "Annual NDVI — fixed spatial panel"),
        ("annual_ndvi_coverage.svg", "Annual NDVI spatial coverage"),
        ("annual_temperature.svg", "Annual 2 m air temperature"),
        ("annual_precipitation.svg", "Annual precipitation"),
    ):
        if key in chart_paths:
            charts.append(
                f"<section class='chart'><h3>{html.escape(title)}</h3>{_svg(chart_paths[key])}</section>"
            )

    cross_table = "<p class='muted'>Cross-source monthly analysis unavailable.</p>"
    if cross:
        rows = []
        for group_name, group_key in (
            ("Monthly anomalies", "anomaly_correlations"),
            ("Detrended anomalies", "detrended_anomaly_correlations"),
        ):
            group = cross.get(group_key, {})
            if not isinstance(group, dict):
                continue
            for variable, label in (
                ("temperature", "NDVI vs temperature"),
                ("precipitation", "NDVI vs precipitation"),
            ):
                pearson_key = f"ndvi_vs_{variable}_pearson_r"
                spearman_key = f"ndvi_vs_{variable}_spearman_rho"
                rows.append(
                    f"<tr><td>{html.escape(group_name)}: {label}</td>"
                    f"<td>{metric(group.get(pearson_key))}</td>"
                    f"<td>{metric(group.get(spearman_key))}</td></tr>"
                )
        if rows:
            cross_table = (
                "<table><thead><tr><th>Comparison</th><th>Pearson r</th><th>Spearman ρ</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>"
            )

    safe_report = json.dumps(report, ensure_ascii=False, default=str).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Earth System Trend Detective — Analysis Report</title>
<style>
:root{{--ink:#172033;--muted:#667085;--line:#e5e7eb;--panel:#f8fafc;--blue:#2563eb;--orange:#dc6923}}
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f8;color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:28px 18px 60px}}header{{background:#10233f;color:white;padding:30px;border-radius:18px}}
h1{{margin:0 0 8px;font-size:clamp(26px,4vw,38px)}}header p{{color:#d6e2f2;margin:0}}
h2{{margin:30px 0 12px;font-size:22px}}h3{{margin:0 0 12px;font-size:16px}}
.panel,.metric,.chart{{background:white;border:1px solid var(--line);border-radius:14px;padding:18px;margin-top:14px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:18px}}
.metric strong{{display:block;font-size:24px;line-height:1.25}}.metric span{{color:var(--muted);font-size:13px}}
.grid-wrap{{display:grid;grid-template-columns:minmax(0,1fr) minmax(230px,0.55fr);gap:18px;align-items:start}}
.pixel-grid{{display:grid;gap:2px;max-width:660px;background:#e5e7eb;padding:3px;border-radius:8px}}
.pixel{{border:0;min-width:0;aspect-ratio:1;border-radius:2px;color:#111827;font-size:8px;cursor:pointer;padding:0}}
.pixel:hover,.pixel:focus{{outline:2px solid #111827;outline-offset:1px;z-index:2}}
.pixel.missing{{background:#e5e7eb;color:#9ca3af}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:13px;margin:10px 0}}
.swatch{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-2px}}
#pixel-detail{{min-height:130px;background:var(--panel);padding:14px;border-radius:10px;white-space:pre-wrap}}
.chart svg{{width:100%;height:auto;display:block}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}}th{{background:var(--panel)}}
.muted{{color:var(--muted)}}.caveat{{border-left:4px solid #d97706;padding:12px 16px;background:#fffbeb;border-radius:6px}}
footer{{margin-top:34px;color:var(--muted);font-size:13px}}
@media(max-width:760px){{.grid-wrap{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<header><h1>Earth System Trend Detective</h1>
<p>Reproducible analysis of NASA Earth-observation and climate data</p>
<p>Generated: {html.escape(str(report.get("generated_at_utc", "unknown")))}</p></header>
<div class="metrics">
<div class="metric"><strong>{metric(ndvi.get("composite_count"))}</strong><span>Monthly MODIS composites selected</span></div>
<div class="metric"><strong>{metric(ndvi.get("available_composite_count"))}</strong><span>Available 16-day MODIS composites</span></div>
<div class="metric"><strong>{metric(ndvi.get("fixed_panel_pixels"))}</strong><span>Pixels in fixed annual panel</span></div>
<div class="metric"><strong>{metric(paired_days)}</strong><span>Paired NASA POWER days</span></div>
<div class="metric"><strong>{metric(common_months)}</strong><span>Common monthly observations</span></div>
<div class="metric"><strong>{html.escape(trend_period_text)}</strong><span>MODIS core trend period</span></div>
<div class="metric"><strong>{html.escape(str(change_year))}</strong><span>Pettitt candidate change year</span></div>
</div>
<h2>Spatial NDVI trend map</h2>
<section class="panel">
<div class="legend"><span><i class="swatch" style="background:#2563eb"></i>NDVI decreasing</span>
<span><i class="swatch" style="background:#dc6923"></i>NDVI increasing</span>
<span><i class="swatch" style="background:#d1d5db"></i>No trend estimate</span></div>
<p class="muted">Cell colour encodes Sen slope direction and magnitude, not statistical significance. BY q-values are shown only for temporally eligible pixel series.</p>
<div class="grid-wrap"><div>{grid_html}</div><div><h3>Pixel details</h3><div id="pixel-detail">Select a grid cell to inspect its Sen slope, confidence interval, temporal-correction status and eligible BY q-value.</div>
<p class="muted">Grid rows and columns follow the MODIS COG subset window. This is a spatial sample grid, not a political or street map.</p></div></div>
</section>
<h2>Time-series visualizations</h2>
{''.join(charts)}
<h2>Cross-source monthly associations</h2>
<section class="panel">{cross_table}<p class="muted">Correlations are exploratory associations; they do not establish causation or validate one physical variable against another.</p></section>
<h2>Methods and quality controls</h2>
<section class="panel">
<ul>
<li>NASA POWER daily 2 m air temperature and corrected precipitation.</li>
<li>NASA MODIS/Terra MOD13Q1.061 250 m NDVI, one 16-day composite selected per calendar month.</li>
<li>Only pixel-reliability code 0 enters NDVI analysis; annual pixel medians require at least three valid composites.</li>
<li>Annual spatial summaries use a fixed pixel cohort present in every requested year; changing coverage is shown separately.</li>
<li>Per-pixel Sen slopes and intervals; Hamed–Rao modified Mann–Kendall variance correction is attempted only for at least ten equally spaced observations with estimable detrended-rank autocorrelation.</li>
<li>Benjamini–Yekutieli q-values are calculated only across temporally eligible pixel tests; ineligible pixels retain descriptive slopes and iid reference p-values but no adjusted p-value or q-value.</li>
<li>Pettitt single-change-point screening and robust median-absolute-deviation anomaly screening.</li>
</ul></section>
<h2>Interpretation limits</h2>
<section class="caveat">
Mann–Kendall uses the Hamed–Rao (1998) detrended-rank variance correction only when a series has at least ten equally spaced observations and an estimable rank autocorrelation function. Short, irregular or otherwise ineligible series receive no temporally adjusted p-value and are excluded from the spatial BY family; their iid p-values are reference-only. The correction is approximate and does not guarantee that all dependence is removed. Pettitt p-values remain unadjusted. Sen-slope intervals use the same modified variance only where the correction is applied; otherwise they are nominal iid intervals. NDVI measures vegetation greenness, not temperature or precipitation. POWER is gridded data, not a local weather-station record. Correlation does not prove causation. The spatial grid is a local sample, not a region-wide census.
</section>
<footer>Data sources: <a href="https://power.larc.nasa.gov/">NASA POWER</a>; <a href="https://doi.org/10.5067/MODIS/MOD13Q1.061">NASA LP DAAC MOD13Q1.061</a>; <a href="https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-13Q1-061">Microsoft Planetary Computer STAC collection</a>. Consult the repository README for citation, licensing notes and reproducibility instructions.</footer>
<script>
const reportData = {safe_report};
document.querySelectorAll(".pixel").forEach((cell) => {{
  cell.addEventListener("click", () => {{
    document.getElementById("pixel-detail").textContent = cell.dataset.info || "No details available.";
  }});
}});
</script>
</main></body></html>"""

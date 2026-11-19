"""Browser interface for the existing Earth System Trend Detective pipeline.

This service starts the repository's real science_core.cli in a worker process.
It is intended for a trusted, single-user demo; do not expose it publicly without
authentication, quotas and process isolation.
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from science_core.desktop import build_cli_command, validate_coordinates

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "web_artifacts"
ARTIFACTS.mkdir(exist_ok=True)
app = FastAPI(title="Earth System Trend Detective", version="0.1.0")

_lock = threading.Lock()
_job: dict[str, Any] = {
    "id": None, "status": "idle", "message": "Ready", "log": [],
    "return_code": None, "report": None, "process": None,
}


class RunRequest(BaseModel):
    latitude: float = Field(default=38.5598, ge=-90, le=90)
    longitude: float = Field(default=68.7870, ge=-180, le=180)


def _append(line: str) -> None:
    with _lock:
        _job["log"].append(line.rstrip()[:1200])
        _job["log"] = _job["log"][-500:]
        _job["message"] = line.rstrip()[:240]


def _worker(job_id: str, command: list[str], output: Path) -> None:
    try:
        _append("Starting the existing NASA data pipeline…")
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        with _lock:
            if _job["id"] != job_id:
                process.terminate()
                return
            _job["process"] = process
        assert process.stdout is not None
        for line in process.stdout:
            _append(line)
        code = process.wait()
        report = output / "report.html"
        with _lock:
            if _job["id"] == job_id:
                _job["return_code"] = code
                _job["status"] = "completed" if code == 0 and report.is_file() else "failed"
                _job["report"] = str(report) if code == 0 and report.is_file() else None
                _job["message"] = "Analysis complete" if _job["status"] == "completed" else f"Pipeline exited with code {code}"
                _job["process"] = None
    except Exception as exc:
        with _lock:
            if _job["id"] == job_id:
                _job["status"] = "failed"
                _job["message"] = str(exc)[:500]
                _job["process"] = None


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "earth-system-trend-detective"}


@app.post("/api/run")
def run_analysis(request: RunRequest) -> dict[str, Any]:
    try:
        lat, lon = validate_coordinates(request.latitude, request.longitude)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with _lock:
        if _job["status"] == "running":
            raise HTTPException(status_code=409, detail="An analysis is already running.")
        job_id = uuid.uuid4().hex
        output = ARTIFACTS / job_id
        output.mkdir(parents=True, exist_ok=False)
        command = build_cli_command(lat, lon, output)
        _job.update({
            "id": job_id, "status": "running", "message": "Starting…",
            "log": [], "return_code": None, "report": None, "process": None,
        })
    thread = threading.Thread(target=_worker, args=(job_id, command, output), daemon=True)
    thread.start()
    return {"id": job_id, "status": "running"}


@app.get("/api/status")
def status() -> dict[str, Any]:
    with _lock:
        return {
            "id": _job["id"], "status": _job["status"], "message": _job["message"],
            "log": list(_job["log"]), "return_code": _job["return_code"],
            "has_report": bool(_job["report"]),
        }


@app.post("/api/stop")
def stop() -> dict[str, str]:
    with _lock:
        process = _job.get("process")
        if _job["status"] != "running":
            raise HTTPException(status_code=409, detail="No running analysis.")
        if process is None:
            raise HTTPException(status_code=409, detail="The process is starting; try again shortly.")
        process.terminate()
        _job["status"] = "stopping"
        _job["message"] = "Stop requested"
    return {"status": "stopping"}


@app.get("/report")
def report() -> FileResponse:
    with _lock:
        path_value = _job.get("report")
    if not path_value:
        raise HTTPException(status_code=404, detail="No completed report is available.")
    path = Path(path_value).resolve()
    if not path.is_relative_to(ARTIFACTS.resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="text/html", filename="earth-system-report.html")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Earth System Trend Detective</title>
<style>
:root{color-scheme:dark;--bg:#081321;--panel:#102238;--line:#23415d;--text:#e8f1f8;--muted:#9bb0c4;--accent:#57d6b2;--blue:#78b7ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 20% 0%,#173554 0,transparent 42%),var(--bg);color:var(--text);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1050px;margin:auto;padding:28px 18px 60px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}
.brand{font-size:12px;letter-spacing:.16em;color:var(--accent);font-weight:700}.tag{border:1px solid var(--line);border-radius:30px;padding:6px 12px;color:var(--muted);font-size:12px}
h1{font-size:clamp(28px,5vw,48px);line-height:1.06;margin:24px 0 12px;max-width:760px}p{color:var(--muted)}
.layout{display:grid;grid-template-columns: minmax(0,1.1fr) minmax(270px,.9fr);gap:16px;margin-top:26px}
.card{background:linear-gradient(145deg,rgba(20,43,66,.96),rgba(12,29,47,.96));border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 14px 35px #0003}
h2{font-size:17px;margin:0 0 16px}.fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label{display:block;color:var(--muted);font-size:13px;margin-bottom:6px}input{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:#081827;color:var(--text);font-size:16px}
button{border:0;border-radius:10px;padding:12px 16px;font-weight:700;cursor:pointer;background:var(--accent);color:#06241d}
button.secondary{background:#1b3855;color:var(--text);border:1px solid var(--line)}button:disabled{opacity:.45;cursor:not-allowed}
.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}.status{display:flex;align-items:center;gap:9px;margin-top:17px;color:var(--muted);font-size:13px}
.dot{width:9px;height:9px;border-radius:50%;background:#71879a}.dot.running{background:#ffc66d;box-shadow:0 0 0 5px #ffc66d20}.dot.completed{background:var(--accent)}
.log{height:280px;overflow:auto;background:#06111d;border:1px solid var(--line);border-radius:10px;padding:12px;font:12px/1.55 ui-monospace,monospace;color:#b9d1e5;white-space:pre-wrap;overflow-wrap:anywhere}
.meta{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.metric{padding:12px;background:#0a1b2b;border-radius:10px}.metric b{display:block;font-size:18px}.metric span{color:var(--muted);font-size:12px}
.note{font-size:12px;border-left:2px solid var(--blue);padding-left:12px;margin-top:15px}
footer{margin-top:20px;font-size:12px;color:#7890a6}
@media(max-width:720px){.layout{grid-template-columns:1fr}.fields{grid-template-columns:1fr 1fr}.card{padding:16px}}
</style></head><body><main>
<div class="top"><div class="brand">EARTH OBSERVATION • SCIENCE WORKBENCH</div><div class="tag">LIVE DATA PIPELINE · NASA + MODIS</div></div>
<h1>Earth System<br>Trend Detective</h1>
<p>Run the project's existing Python analysis for a selected location. Follow the live process log and open the generated scientific report.</p>
<div class="layout">
<section class="card"><h2>Study area</h2>
<div class="fields"><div><label for="lat">Latitude (−90 to 90)</label><input id="lat" type="number" min="-90" max="90" step="any" value="38.5598"></div>
<div><label for="lon">Longitude (−180 to 180)</label><input id="lon" type="number" min="-180" max="180" step="any" value="68.7870"></div></div>
<div class="actions"><button id="run">Run NASA analysis</button><button class="secondary" id="dushanbe">Dushanbe</button><button class="secondary" id="stop" disabled>Stop</button></div>
<div class="status"><span id="dot" class="dot"></span><span id="state">Ready to start</span></div>
<div class="meta"><div class="metric"><b>2001–2025</b><span>MODIS NDVI period</span></div><div class="metric"><b>2021–2025</b><span>NASA POWER period</span></div><div class="metric"><b>~4 × 4 km</b><span>Local study window</span></div><div class="metric"><b>Quality screened</b><span>MODIS pixel reliability</span></div></div>
<p class="note">The run downloads actual source data. Internet access is required. A completed report can be opened separately; no sample results are substituted.</p>
</section>
<section class="card"><h2>Live execution log</h2><div id="log" class="log">Waiting for a run…</div>
<div class="actions"><button id="report" disabled>Open scientific report</button></div>
<p class="note">The report contains the pipeline's charts, data coverage, spatial NDVI results, and scientific limitations.</p></section>
</div>
<footer>Research tool, not a forecasting service. NDVI is a vegetation indicator; exploratory correlations do not establish causation. Public deployment requires authentication and resource controls.</footer>
</main><script>
const $=id=>document.getElementById(id);let timer=null,lastLog="";
function setState(s){$("state").textContent=s;$("dot").className="dot "+s}
function showLog(lines){const value=(lines||[]).join("\n");if(value!==lastLog){$("log").textContent=value||"No log output yet."; $("log").scrollTop=$("log").scrollHeight;lastLog=value}}
async function poll(){try{const r=await fetch("/api/status");const d=await r.json();setState(d.message||d.status);showLog(d.log);$("stop").disabled=d.status!=="running";$("report").disabled=!d.has_report;if(["completed","failed","idle"].includes(d.status)){clearInterval(timer);timer=null;$("run").disabled=false}}catch(e){setState("Connection error")}}
$("run").onclick=async()=>{const latitude=Number($("lat").value),longitude=Number($("lon").value);if(!Number.isFinite(latitude)||latitude < -90||latitude>90||!Number.isFinite(longitude)||longitude < -180||longitude>180){alert("Enter valid latitude and longitude.");return}
$("run").disabled=true;$("report").disabled=true;lastLog="";$("log").textContent="Submitting analysis…";try{const r=await fetch("/api/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({latitude,longitude})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not start");setState("Starting analysis");timer=setInterval(poll,1500);poll()}catch(e){setState(e.message);$("run").disabled=false}};
$("dushanbe").onclick=()=>{$("lat").value="38.5598";$("lon").value="68.7870"};
$("stop").onclick=async()=>{try{await fetch("/api/stop",{method:"POST"});poll()}catch(e){setState(e.message)}};
$("report").onclick=()=>window.open("/report","_blank");
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

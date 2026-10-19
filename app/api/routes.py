import os
import tempfile
import threading
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from app.core.database import init_db, get_telemetry_stats, log_visitor
from app.services.pipeline import (
    get_engine_state,
    stop_pipeline,
    run_pipeline_task,
    set_output_file_path,
    get_output_file_path
)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """Serves the dashboard UI component and logs visitor IP telemetry."""
    init_db()
    
    # Capture client IP safely
    client_ip = request.client.host if request.client else "127.0.0.1"
    log_visitor(client_ip)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(base_dir, "templates", "index.html")
    
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
            
    return HTMLResponse(content="<h3>Error: Dashboard template not found.</h3>", status_code=404)

@router.get("/api/telemetry")
def get_telemetry_data():
    """Returns database telemetry counters and visitor logs as JSON."""
    init_db()
    stats = get_telemetry_stats()
    return stats

@router.get("/api/telemetry-view", response_class=HTMLResponse)
def get_telemetry_html_component():
    """Serves the separate telemetry.html component view dynamically."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(base_dir, "templates", "telemetry.html")
    
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<p class='text-red-500'>Telemetry component template missing.</p>", status_code=404)


@router.get("/status")
def get_status():
    return get_engine_state()

@router.post("/start")
def start_engine():
    state = get_engine_state()
    if not state["running"]:
        with tempfile.NamedTemporaryFile(
            prefix="outreach_review_queue_", suffix=".csv", delete=False
        ) as output_file:
            output_csv_path = output_file.name
        
        set_output_file_path(output_csv_path)
        t = threading.Thread(target=run_pipeline_task, args=(output_csv_path,))
        t.daemon = True
        t.start()
    return {"status": "started"}

@router.post("/stop")
def stop_engine():
    stop_pipeline()
    return {"status": "stopping"}

@router.get("/download-csv")
def download_csv():
    file_path = get_output_file_path()
    if file_path and os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/csv", filename="outreach_review_queue.csv")
    return {"error": "CSV file not found yet."}
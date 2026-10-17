import os
import tempfile
import threading
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from app.services.pipeline import (
    get_engine_state,
    stop_pipeline,
    run_pipeline_task,
    set_output_file_path,
    get_output_file_path
)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Outreach Engine Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Plus Jakarta Sans', sans-serif; }
        </style>
    </head>
    <body class="bg-[#090A0F] text-slate-100 min-h-screen flex flex-col items-center justify-center p-6 selection:bg-blue-500 selection:text-white relative overflow-hidden">
        <div class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none"></div>
        <div class="absolute bottom-10 right-10 w-[300px] h-[300px] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none"></div>

        <div class="relative z-10 bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 rounded-3xl shadow-2xl p-8 max-w-lg w-full">
            <div class="flex items-center justify-between mb-8">
                <div>
                    <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-blue-500 inline-block shadow-[0_0_12px_rgba(59,130,246,0.6)]"></span>
                        Outreach Engine
                    </h1>
                    <p class="text-slate-400 text-xs mt-1 font-medium">Data Extraction & AI Pitch Generator</p>
                </div>
                <div id="statusBadge" class="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700/50 transition-all">
                    Idle
                </div>
            </div>

            <div class="mb-6">
                <button id="engineBtn" onclick="toggleEngine()" class="w-full py-4 px-6 rounded-2xl font-bold text-base transition-all duration-200 shadow-lg shadow-blue-600/20 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white cursor-pointer active:scale-[0.98]">
                    Start Engine
                </button>
            </div>

            <div class="bg-slate-950/60 border border-slate-800/60 rounded-2xl p-5 mb-6">
                <div class="flex justify-between items-center mb-3">
                    <span class="text-[11px] uppercase tracking-wider text-slate-400 font-bold">System Status</span>
                </div>
                <p id="statusText" class="text-sm text-slate-300 font-mono tracking-tight bg-slate-900/50 p-3 rounded-xl border border-slate-800/40">Ready to start extraction...</p>
                <div class="mt-4 w-full bg-slate-900 rounded-full h-2.5 overflow-hidden p-[1px] border border-slate-800/80">
                    <div id="progressBar" class="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full w-0 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.4)]"></div>
                </div>
            </div>

            <div id="downloadContainer" class="hidden">
                <a id="downloadCsvLink" href="/download-csv" class="flex items-center justify-center gap-2 w-full py-3.5 px-4 bg-emerald-600/90 hover:bg-emerald-500 text-white font-semibold rounded-2xl text-center transition-all shadow-lg shadow-emerald-600/20 active:scale-[0.98]">
                    <span>Download Extracted CSV</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                </a>
            </div>
        </div>

        <script>
            async function fetchStatus() {
                try {
                    const res = await fetch('/status');
                    const data = await res.json();
                    
                    const btn = document.getElementById('engineBtn');
                    const statusBadge = document.getElementById('statusBadge');
                    const statusText = document.getElementById('statusText');
                    const progressBar = document.getElementById('progressBar');
                    const downloadContainer = document.getElementById('downloadContainer');

                    statusText.innerText = data.status;
                    
                    if (data.total > 0) {
                        const percent = (data.progress / data.total) * 100;
                        progressBar.style.width = percent + '%';
                    }

                    if (data.running) {
                        btn.innerText = "Stop Engine";
                        btn.className = "w-full py-4 px-6 rounded-2xl font-bold text-base transition-all duration-200 shadow-lg shadow-red-600/20 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white cursor-pointer active:scale-[0.98]";
                        statusBadge.innerText = "Running";
                        statusBadge.className = "px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse";
                        downloadContainer.classList.add('hidden');
                    } else {
                        btn.innerText = "Start Engine";
                        btn.className = "w-full py-4 px-6 rounded-2xl font-bold text-base transition-all duration-200 shadow-lg shadow-blue-600/20 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white cursor-pointer active:scale-[0.98]";
                        if (data.progress > 0 || data.status.includes("completed") || data.status.includes("stopped")) {
                            statusBadge.innerText = "Ready";
                            statusBadge.className = "px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
                            downloadContainer.classList.remove('hidden');
                        } else {
                            statusBadge.innerText = "Idle";
                            statusBadge.className = "px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700/50";
                        }
                    }
                } catch (e) {
                    console.error(e);
                }
            }

            async function toggleEngine() {
                const btn = document.getElementById('engineBtn');
                const isRunning = btn.innerText === "Stop Engine";
                const endpoint = isRunning ? '/stop' : '/start';
                await fetch(endpoint, { method: 'POST' });
                fetchStatus();
            }

            document.getElementById('downloadCsvLink').addEventListener('click', async (event) => {
                if (!window.showSaveFilePicker) return;
                event.preventDefault();
                const downloadUrl = event.currentTarget.href;

                try {
                    const fileHandle = await window.showSaveFilePicker({
                        suggestedName: 'outreach_review_queue.csv',
                        types: [{ description: 'CSV file', accept: { 'text/csv': ['.csv'] } }]
                    });
                    const response = await fetch(downloadUrl);
                    if (!response.ok) throw new Error(`CSV download failed: ${response.status}`);
                    const writable = await fileHandle.createWritable();
                    await writable.write(await response.blob());
                    await writable.close();
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        console.error(error);
                        window.location.href = downloadUrl;
                    }
                }
            });

            setInterval(fetchStatus, 1000);
        </script>
    </body>
    </html>
    """)

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
        t = threading.Thread(target=run_pipeline_task, args=("leads.csv", output_csv_path))
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
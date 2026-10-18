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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Outreach Engine Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Plus Jakarta Sans', sans-serif; }
        </style>
    </head>
    <body class="bg-[#F8FAFC] text-slate-800 min-h-screen flex font-sans antialiased">

        <!-- Left Navigation Sidebar -->
        <aside class="w-20 lg:w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-4 shrink-0">
            <div>
                <!-- Brand Logo / Name -->
                <div class="flex items-center gap-3 px-2 py-3 mb-6">
                    <div class="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
                        O
                    </div>
                    <span class="hidden lg:inline text-lg font-bold text-slate-900 tracking-tight">Outreach Engine</span>
                </div>

                <!-- Nav Links -->
                <nav class="space-y-1">
                    <a href="#" class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-900 bg-slate-100/80 transition-colors">
                        <svg class="w-5 h-5 text-slate-700" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                        <span class="hidden lg:inline">Home</span>
                    </a>
                    <a href="#" class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                        <span class="hidden lg:inline">Leads Pipeline</span>
                    </a>
                    <a href="#" class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                        <span class="hidden lg:inline">Generated Queue</span>
                    </a>
                </nav>
            </div>

            <!-- Profile Badge -->
            <div class="pt-4 border-t border-slate-100 flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-200 border border-slate-300 overflow-hidden flex items-center justify-center font-bold text-slate-600 text-xs">
                    N
                </div>
                <div class="hidden lg:block overflow-hidden">
                    <p class="text-xs font-semibold text-slate-900 truncate">Nosarummen</p>
                    <p class="text-[10px] text-slate-400 truncate">Engineer Workspace</p>
                </div>
            </div>
        </aside>

        <!-- Main Content Workspace -->
        <main class="flex-1 flex flex-col min-w-0 overflow-y-auto">
            
            <!-- Top Header Stepper Bar -->
            <header class="bg-white border-b border-slate-200 px-8 py-3.5 flex items-center justify-between gap-4">
                <div class="flex items-center gap-6 text-xs font-medium text-slate-500 overflow-x-auto">
                    <div class="flex items-center gap-2 text-slate-900 font-semibold shrink-0">
                        <span class="w-4 h-4 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">✓</span>
                        Setup Leads
                    </div>
                    <span class="text-slate-300">•</span>
                    <div class="flex items-center gap-2 text-slate-900 font-semibold shrink-0">
                        <span class="w-4 h-4 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">✓</span>
                        Gemini Model Ready
                    </div>
                    <span class="text-slate-300">•</span>
                    <div class="flex items-center gap-2 text-blue-600 font-semibold shrink-0">
                        <span class="w-4 h-4 rounded-full border-2 border-blue-600 flex items-center justify-center text-[10px]">3</span>
                        Generate Pitches
                    </div>
                    <span class="text-slate-300">•</span>
                    <div class="flex items-center gap-2 text-slate-400 shrink-0">
                        <span class="w-4 h-4 rounded-full border border-slate-300 flex items-center justify-center text-[10px]">4</span>
                        Export Queue
                    </div>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
                        System Online
                    </span>
                </div>
            </header>

            <!-- Dashboard Body -->
            <div class="p-8 max-w-6xl w-full mx-auto space-y-6">
                
                <!-- Greeting Header -->
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Welcome back, Nosarummen</h1>
                        <p class="text-sm text-slate-500 mt-0.5">Extract B2B lead datasets and generate AI cold outreach pitches at scale.</p>
                    </div>
                </div>

                <!-- Hero Section: Grid with Action Box + Royal Blue Stat Card -->
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    
                    <!-- Main Engine Controller Banner (2 cols) -->
                    <div class="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between relative overflow-hidden">
                        <div class="flex items-start justify-between">
                            <div class="max-w-md">
                                <span id="statusBadge" class="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 mb-3 border border-slate-200">
                                    Idle
                                </span>
                                <h2 class="text-lg font-bold text-slate-900">Lead Processing & AI Generation</h2>
                                <p class="text-xs text-slate-500 mt-1">Reads leads from leads.csv and drafts direct, value-focused messages using Gemini 3.8 Flash.</p>
                            </div>
                        </div>

                        <!-- Progress Bar & Status Display -->
                        <div class="mt-6">
                            <p id="statusText" class="text-xs font-mono text-slate-600 mb-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">Ready to start extraction...</p>
                            <div class="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                                <div id="progressBar" class="bg-blue-600 h-2.5 rounded-full w-0 transition-all duration-300"></div>
                            </div>
                        </div>

                        <!-- Action Button Bar -->
                        <div class="mt-6 flex items-center gap-3">
                            <button id="engineBtn" onclick="toggleEngine()" class="px-6 py-3 rounded-xl font-semibold text-sm bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-sm cursor-pointer flex items-center gap-2">
                                <span>Start Engine</span>
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                            </button>

                            <div id="downloadContainer" class="hidden">
                                <a id="downloadCsvLink" href="/download-csv" class="px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition-all shadow-sm flex items-center gap-2">
                                    <span>Download CSV</span>
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                                </a>
                            </div>
                        </div>
                    </div>

                    <!-- Royal Blue Banner Card (Terac style) -->
                    <div class="bg-blue-600 rounded-2xl p-6 text-white flex flex-col justify-between shadow-md relative overflow-hidden">
                        <div class="absolute -right-6 -bottom-6 w-32 h-32 bg-white/10 rounded-full blur-xl pointer-events-none"></div>
                        
                        <div>
                            <span class="text-[11px] font-bold tracking-wider uppercase opacity-80">Extraction Metrics</span>
                            <h3 id="processedCount" class="text-3xl font-extrabold mt-1">0 Leads</h3>
                            <p class="text-xs text-blue-100 mt-2 leading-relaxed">Generated messages are cached and formatted for instant CSV export.</p>
                        </div>

                        <div class="pt-6 border-t border-white/15 flex items-center gap-2 text-xs font-medium text-blue-100">
                            <svg class="w-4 h-4 text-emerald-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            <span>Gemini 3.8 Flash Active</span>
                        </div>
                    </div>
                </div>

                <!-- Lower Section: Pipeline Tasks / Activity View -->
                <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                    <div class="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
                        <h3 class="font-bold text-slate-900 text-sm">Active Review Queue</h3>
                        <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
                            Waiting on review
                        </span>
                    </div>

                    <div class="flex items-center gap-4 py-3 px-4 rounded-xl bg-slate-50 border border-slate-200/60">
                        <div class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center font-semibold text-slate-600 text-xs shrink-0">
                            CSV
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-semibold text-slate-900 truncate">leads.csv Pipeline Execution</p>
                            <p class="text-xs text-slate-400 mt-0.5">Target: React & Next.js Founders / Engineering Leads</p>
                        </div>
                        <span id="queueStatusPill" class="text-xs font-semibold text-slate-500 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
                            Idle
                        </span>
                    </div>
                </div>

            </div>
        </main>

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
                    const processedCount = document.getElementById('processedCount');
                    const queueStatusPill = document.getElementById('queueStatusPill');

                    statusText.innerText = data.status;
                    processedCount.innerText = `${data.progress} / ${data.total || 0} Leads`;
                    
                    if (data.total > 0) {
                        const percent = (data.progress / data.total) * 100;
                        progressBar.style.width = percent + '%';
                    }

                    if (data.running) {
                        btn.innerHTML = `<span>Stop Engine</span>`;
                        btn.className = "px-6 py-3 rounded-xl font-semibold text-sm bg-rose-600 hover:bg-rose-700 text-white transition-all shadow-sm cursor-pointer";
                        statusBadge.innerText = "Running";
                        statusBadge.className = "inline-block px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse";
                        queueStatusPill.innerText = "Processing...";
                        downloadContainer.classList.add('hidden');
                    } else {
                        btn.innerHTML = `<span>Start Engine</span><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>`;
                        btn.className = "px-6 py-3 rounded-xl font-semibold text-sm bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-sm cursor-pointer flex items-center gap-2";
                        if (data.progress > 0 || data.status.includes("completed") || data.status.includes("stopped")) {
                            statusBadge.innerText = "Ready";
                            statusBadge.className = "inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200";
                            queueStatusPill.innerText = "Completed";
                            downloadContainer.classList.remove('hidden');
                        } else {
                            statusBadge.innerText = "Idle";
                            statusBadge.className = "inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200";
                            queueStatusPill.innerText = "Idle";
                        }
                    }
                } catch (e) {
                    console.error(e);
                }
            }

            async function toggleEngine() {
                const btn = document.getElementById('engineBtn');
                const isRunning = btn.innerText.includes("Stop");
                const endpoint = isRunning ? '/stop' : '/start';
                await fetch(endpoint, { method: 'POST' });
                fetchStatus();
            }

            document.getElementById('downloadCsvLink')?.addEventListener('click', async (event) => {
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
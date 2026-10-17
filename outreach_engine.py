import os
import tempfile
import threading
import time
import webbrowser
from typing import Optional
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Outreach Engine Dashboard")

# Initialize Gemini Client if API key is present
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Engine State Management
engine_state = {
    "running": False,
    "status": "Idle - Ready to extract",
    "progress": 0,
    "total": 0
}

output_file_path: Optional[str] = None
stop_event = threading.Event()

def run_pipeline_task(input_csv_path: str, output_csv_path: str):
    """Background task to extract leads, generate AI pitches, and save to CSV."""
    global engine_state
    engine_state["running"] = True
    engine_state["status"] = "Processing leads..."
    stop_event.clear()

    if not os.path.exists(input_csv_path):
        engine_state["status"] = f"Error: Input file '{input_csv_path}' not found."
        engine_state["running"] = False
        return

    try:
        df = pd.read_csv(input_csv_path)
        engine_state["total"] = len(df)
        engine_state["progress"] = 0
        review_records = []

        for index, row in df.iterrows():
            # Check if stop button was clicked
            if stop_event.is_set():
                engine_state["status"] = "Engine stopped by user. Saving available data..."
                break

            name = row.get("Name", "Founder")
            company = row.get("Company", "Your Company")
            email = row.get("Email", "")
            profile_url = row.get("ProfileURL", "#")
            focus = row.get("Focus", "React and Next.js development")
            channel = row.get("Channel", "LinkedIn")

            # Generate AI-personalized pitch using Gemini
            pitch = ""
            if client:
                try:
                    prompt = (
                        f"Write a short, professional cold outreach message (under 120 words)"
                        f" to {name} at {company}, who focuses on {focus}. Pitch Nosa, an"
                        f" experienced React/Next.js frontend engineer looking for contract"
                        f" overflow work. Keep it direct and value-focused."
                    )
                    response = client.models.generate_content(
                        model="gemini-3.8-flash", contents=prompt
                    )
                    pitch = response.text
                except Exception as e:
                    pitch = f"[AI Error: {e}]"

            review_records.append({
                "Name": name,
                "Company": company,
                "Email": email,
                "Channel": channel,
                "ProfileURL": profile_url,
                "GeneratedMessage": pitch,
            })

            engine_state["progress"] = index + 1
            engine_state["status"] = f"Processed {index + 1} of {len(df)} leads..."
            time.sleep(0.4) # Simulate smooth streaming progress

        # Export available records to CSV
        output_df = pd.DataFrame(review_records)
        output_df.to_csv(output_csv_path, index=False)
        
        if stop_event.is_set():
            engine_state["status"] = "Stopped gracefully. Partial CSV ready for download!"
        else:
            engine_state["status"] = "Extraction completed successfully!"
            
    except Exception as e:
        engine_state["status"] = f"Error: {e}"
    finally:
        engine_state["running"] = False


@app.get("/", response_class=HTMLResponse)
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
        <!-- Background Ambient Glow Effects -->
        <div class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none"></div>
        <div class="absolute bottom-10 right-10 w-[300px] h-[300px] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none"></div>

        <div class="relative z-10 bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 rounded-3xl shadow-2xl p-8 max-w-lg w-full">
            
            <!-- Header Section -->
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
            <!-- Center Action Button -->
            <div class="mb-6">
                <button id="engineBtn" onclick="toggleEngine()" class="w-full py-4 px-6 rounded-2xl font-bold text-base transition-all duration-200 shadow-lg shadow-blue-600/20 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white cursor-pointer active:scale-[0.98]">
                    Start Engine
                </button>
            </div>

            <!-- Status & Progress Box -->
            <div class="bg-slate-950/60 border border-slate-800/60 rounded-2xl p-5 mb-6">
                <div class="flex justify-between items-center mb-3">
                    <span class="text-[11px] uppercase tracking-wider text-slate-400 font-bold">System Status</span>
                </div>
                <p id="statusText" class="text-sm text-slate-300 font-mono tracking-tight bg-slate-900/50 p-3 rounded-xl border border-slate-800/40">Ready to start extraction...</p>
                <div class="mt-4 w-full bg-slate-900 rounded-full h-2.5 overflow-hidden p-[1px] border border-slate-800/80">
                    <div id="progressBar" class="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full w-0 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.4)]"></div>
                </div>
            </div>

            <!-- Download CSV Section -->
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

@app.get("/status")
def get_status():
    return engine_state

@app.post("/start")
def start_engine():
    global output_file_path
    if not engine_state["running"]:
        with tempfile.NamedTemporaryFile(
            prefix="outreach_review_queue_", suffix=".csv", delete=False
        ) as output_file:
            output_csv_path = output_file.name
        output_file_path = output_csv_path
        t = threading.Thread(target=run_pipeline_task, args=("leads.csv", output_csv_path))
        t.daemon = True
        t.start()
    return {"status": "started"}

@app.post("/stop")
def stop_engine():
    if engine_state["running"]:
        stop_event.set()
    return {"status": "stopping"}

@app.get("/download-csv")
def download_csv():
    if output_file_path and os.path.exists(output_file_path):
        return FileResponse(output_file_path, media_type="text/csv", filename="outreach_review_queue.csv")
    return {"error": "CSV file not found yet."}


if __name__ == "__main__":
    import uvicorn

    def open_browser():
        time.sleep(2.0)  # Give uvicorn a brief second to spin up
        webbrowser.open("http://127.0.0.1:8000")

    # Automatically open local browser tab
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI server locally (ready for future cloud deployment via port binding)
    uvicorn.run("outreach_engine:app", host="127.0.0.1", port=8000, reload=True)
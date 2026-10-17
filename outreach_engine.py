import os
import threading
import time
import webbrowser
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
    "total": 0,
    "output_file": "outreach_review_queue.csv"
}

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
    </head>
    <body class="bg-gray-950 text-white font-sans min-h-screen flex flex-col items-center justify-center p-6">
        <div class="bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl p-8 max-w-md w-full text-center">
            <h1 class="text-3xl font-bold mb-1 tracking-tight text-blue-400">Outreach Engine</h1>
            <p class="text-gray-400 mb-8 text-sm">Data Extraction & AI Pitch Generator</p>
            
            <!-- Center Action Button -->
            <div class="my-6">
                <button id="engineBtn" onclick="toggleEngine()" class="w-full py-4 px-6 rounded-xl font-bold text-lg transition-all shadow-lg bg-blue-600 hover:bg-blue-500 text-white cursor-pointer">
                    Start Engine
                </button>
            </div>

            <!-- Status & Progress Box -->
            <div class="bg-gray-950 border border-gray-800 rounded-xl p-4 mb-6 text-left">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs uppercase tracking-wider text-gray-500 font-semibold">Engine Status</span>
                    <span id="statusBadge" class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300">Idle</span>
                </div>
                <p id="statusText" class="text-sm text-gray-300 font-mono">Ready to start extraction...</p>
                <div class="mt-3 w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                    <div id="progressBar" class="bg-blue-500 h-2 w-0 transition-all duration-300"></div>
                </div>
            </div>

            <!-- Download CSV Section -->
            <div id="downloadContainer" class="hidden">
                <a href="/download-csv" class="inline-block w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-center transition-all shadow-md">
                    Download Extracted CSV 📥
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
                        btn.className = "w-full py-4 px-6 rounded-xl font-bold text-lg transition-all shadow-lg bg-red-600 hover:bg-red-500 text-white cursor-pointer";
                        statusBadge.innerText = "Running";
                        statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse";
                        downloadContainer.classList.add('hidden');
                    } else {
                        btn.innerText = "Start Engine";
                        btn.className = "w-full py-4 px-6 rounded-xl font-bold text-lg transition-all shadow-lg bg-blue-600 hover:bg-blue-500 text-white cursor-pointer";
                        if (data.progress > 0 || data.status.includes("completed") || data.status.includes("stopped")) {
                            statusBadge.innerText = "Ready";
                            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
                            downloadContainer.classList.remove('hidden');
                        } else {
                            statusBadge.innerText = "Idle";
                            statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300";
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
    if not engine_state["running"]:
        t = threading.Thread(target=run_pipeline_task, args=("leads.csv", "outreach_review_queue.csv"))
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
    if os.path.exists("outreach_review_queue.csv"):
        return FileResponse("outreach_review_queue.csv", media_type="text/csv", filename="outreach_review_queue.csv")
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
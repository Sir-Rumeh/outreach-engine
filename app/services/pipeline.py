import os
import time
import threading
import pandas as pd
from typing import Optional
from app.core.config import client
from app.core.database import init_db, increment_counter

# Engine State Management
engine_state = {
    "running": False,
    "status": "Idle - Ready to extract",
    "progress": 0,
    "total": 0
}

output_file_path: Optional[str] = None
stop_event = threading.Event()

def get_engine_state() -> dict:
    return engine_state

def set_output_file_path(path: str):
    global output_file_path
    output_file_path = path

def get_output_file_path() -> Optional[str]:
    return output_file_path

def stop_pipeline():
    if engine_state["running"]:
        stop_event.set()

def run_pipeline_task(input_csv_path: str, output_csv_path: str):
    """Background task that reads real leads from CSV using enumerate, calls Gemini API,
    and records anonymous telemetry usage counters in SQLite.
    """
    global engine_state
    engine_state["running"] = True
    engine_state["status"] = "Initializing database and reading lead dataset..."
    stop_event.clear()

    # Initialize SQLite Telemetry DB
    init_db()

    if not os.path.exists(input_csv_path) or os.path.getsize(input_csv_path) == 0:
        engine_state["status"] = f"Error: Input file '{input_csv_path}' not found or empty."
        engine_state["running"] = False
        return

    try:
        df = pd.read_csv(input_csv_path)
        if df.empty:
            engine_state["status"] = "Error: Input CSV contains no rows."
            engine_state["running"] = False
            return

        engine_state["total"] = len(df)
        engine_state["progress"] = 0
        review_records = []

        # Increment global run telemetry counter
        increment_counter("total_runs", 1)

        for current_step, (_, row) in enumerate(df.iterrows(), start=1):
            if stop_event.is_set():
                engine_state["status"] = "Engine stopped by user. Saving available data..."
                break

            name = row.get("Name", "Founder")
            company = row.get("Company", "Your Company")
            email = row.get("Email", "")
            profile_url = row.get("ProfileURL", "#")
            focus = row.get("Focus", "React and Next.js development")
            channel = row.get("Channel", "LinkedIn")
            source_post = row.get("SourcePost", "Looking for engineering support.")

            # Generate AI-personalized pitch using Gemini
            pitch = ""
            if client:
                try:
                    prompt = (
                        f"Analyze this public post from {name} at {company}: '{source_post}' "
                        f"(Focus: {focus}). Write a short, professional cold outreach message "
                        f"(under 120 words) pitching Nosa, an experienced React/Next.js and "
                        f"Python/FastAPI engineer looking for contract overflow work. Keep it direct and value-focused."
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

            # Increment throughput/lead telemetry counter in SQLite
            increment_counter("total_leads_processed", 1)

            engine_state["progress"] = current_step
            engine_state["status"] = f"Processed {current_step} of {len(df)} leads..."
            time.sleep(0.4)

        # Export available records to CSV
        output_df = pd.DataFrame(review_records)
        output_df.to_csv(output_csv_path, index=False)
        
        if stop_event.is_set():
            engine_state["status"] = "Stopped gracefully. Partial CSV ready for download!"
        else:
            engine_state["status"] = f"Extraction completed successfully! Processed {len(review_records)} leads."
            
    except Exception as e:
        engine_state["status"] = f"Error: {e}"
    finally:
        engine_state["running"] = False
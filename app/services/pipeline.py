import os
import time
import threading
from typing import Optional
import pandas as pd
from app.core.config import client
from app.models.schemas import LeadItem

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

        # for index, row in df.iterrows():
        for current_step, (_, row) in enumerate(df.iterrows(), start=1):
            if stop_event.is_set():
                engine_state["status"] = "Engine stopped by user. Saving available data..."
                break

            # Validate input fields using Pydantic model defaults
            lead_data = LeadItem(
                Name=str(row.get("Name", "Founder")),
                Company=str(row.get("Company", "Your Company")),
                Email=str(row.get("Email", "")),
                Channel=str(row.get("Channel", "LinkedIn")),
                ProfileURL=str(row.get("ProfileURL", "#")),
                Focus=str(row.get("Focus", "React and Next.js development"))
            )

            # Generate AI-personalized pitch using Gemini
            pitch = ""
            if client:
                try:
                    prompt = (
                        f"Write a short, professional cold outreach message (under 120 words)"
                        f" to {lead_data.Name} at {lead_data.Company}, who focuses on {lead_data.Focus}."
                        f" Pitch Nosa, an experienced React/Next.js frontend engineer looking for"
                        f" contract overflow work. Keep it direct and value-focused."
                    )
                    response = client.models.generate_content(
                        model="gemini-3.8-flash", contents=prompt
                    )
                    pitch = response.text
                except Exception as e:
                    pitch = f"[AI Error: {e}]"

            review_records.append({
                "Name": lead_data.Name,
                "Company": lead_data.Company,
                "Email": lead_data.Email,
                "Channel": lead_data.Channel,
                "ProfileURL": lead_data.ProfileURL,
                "GeneratedMessage": pitch,
            })
            

            engine_state["progress"] = current_step
            engine_state["status"] = f"Processed {current_step} of {len(df)} leads..."
            time.sleep(0.4)

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
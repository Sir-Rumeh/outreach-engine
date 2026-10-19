import os
import time
import threading
import json
import pandas as pd
from typing import Optional
from google.genai import types
from app.core.config import client
from app.core.database import init_db, increment_counter

# Engine State Management
engine_state = {
    "running": False,
    "status": "Idle - Ready to extract",
    "progress": 0,
    "total": 0,
    "percentage": 0
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

def fetch_live_founders_from_web() -> pd.DataFrame:
    """Uses Gemini with live Google Search Grounding to find real tech founders 
    who posted within the last 24 hours looking for React, Next.js, or FastAPI support.
    Throws an error if live data cannot be retrieved rather than using fake data.
    """
    if not client:
        raise RuntimeError("Gemini API client is not initialized. Check your GEMINI_API_KEY.")

    try:
        # Prompt engineered to instruct Gemini to search the live web via Google Search Grounding
        prompt = (
            "Search the live web (X/Twitter, LinkedIn, Wellfound, and tech startup communities) for real tech founders "
            "or engineering leads who have posted publicly within the last 24 hours looking for React, Next.js, TypeScript, "
            "or FastAPI freelance/contract engineering help. "
            "Extract at least 5 real, active founders. "
            "Return ONLY a valid JSON array with no markdown code blocks or backticks, where each object has these exact keys: "
            "Name, Company, Email (or handle if email is private), Channel, ProfileURL, Focus, SourcePost. "
            "Ensure SourcePost quotes or summarizes their actual recent post."
        )

        # Enable Google Search Grounding tool so Gemini queries the live web in real-time
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.1
            )
        )
        
        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise ValueError("Gemini returned an empty response during live web search.")

        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        leads_data = json.loads(text)
        if isinstance(leads_data, list) and len(leads_data) > 0:
            return pd.DataFrame(leads_data)
        else:
            raise ValueError("Parsed JSON did not contain a valid list of leads.")

    except Exception as e:
        print(f"CRITICAL: Live founder search failed: {e}")
        raise e

def run_pipeline_task(output_csv_path: str):
    global engine_state
    engine_state["running"] = True
    engine_state["status"] = "Crawling live web via Google Search (Past 24 Hours)..."
    engine_state["progress"] = 0
    engine_state["total"] = 0
    engine_state["percentage"] = 10
    stop_event.clear()

    init_db()

    try:
        # Fetch strictly live data from the web (no fake fallbacks)
        df = fetch_live_founders_from_web()
        if df.empty:
            raise ValueError("No live leads returned from search query.")

        total_leads = len(df)
        engine_state["total"] = total_leads
        review_records = []

        increment_counter("total_runs", 1)

        for current_step, (_, row) in enumerate(df.iterrows(), start=1):
            if stop_event.is_set():
                engine_state["status"] = "Engine stopped by user. Saving available data..."
                break

            name = str(row.get("Name", "Founder"))
            company = str(row.get("Company", "Startup"))
            email = str(row.get("Email", "Not Public"))
            profile_url = str(row.get("ProfileURL", "#"))
            focus = str(row.get("Focus", "React/Next.js"))
            channel = str(row.get("Channel", "X/Twitter"))
            source_post = str(row.get("SourcePost", "Looking for engineering support."))

            # Draft personalized outreach pitch for this specific real founder
            pitch = ""
            if client:
                try:
                    pitch_prompt = (
                        f"Analyze this real public post from {name} at {company} ({channel}): '{source_post}' "
                        f"(Focus: {focus}). Write a short, professional cold outreach message (under 120 words) "
                        f"pitching Nosa, an experienced React/Next.js and Python/FastAPI engineer looking for contract overflow work. "
                        f"Reference their specific post bottleneck directly. Keep it concise, high-value, and conversion-focused."
                    )
                    pitch_response = client.models.generate_content(
                        model="gemini-3.8-flash", contents=pitch_prompt
                    )
                    pitch = getattr(pitch_response, "text", "") or "[Pitch generation unavailable]"
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

            increment_counter("total_leads_processed", 1)

            calculated_pct = int((current_step / total_leads) * 100)
            engine_state["progress"] = current_step
            engine_state["percentage"] = calculated_pct
            engine_state["status"] = f"Processed {current_step} of {total_leads} live leads ({calculated_pct}%)..."
            time.sleep(0.4)

        output_df = pd.DataFrame(review_records)
        output_df.to_csv(output_csv_path, index=False)
        
        if stop_event.is_set():
            engine_state["status"] = "Stopped gracefully. Partial CSV ready for download!"
        else:
            engine_state["percentage"] = 100
            engine_state["status"] = f"Live extraction completed successfully! Processed {len(review_records)} real founders."
            
    except Exception as e:
        engine_state["status"] = f"Error: {str(e)}"
        engine_state["percentage"] = 0
    finally:
        engine_state["running"] = False
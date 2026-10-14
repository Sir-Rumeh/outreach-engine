import os
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# Initialize Gemini Client using environment API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Configuration Constants
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def run_outreach_pipeline(input_csv_path: str, output_csv_path: str):
  """Reads leads, sends emails automatically where available, and generates

  a review queue CSV with clickable social profile links for LinkedIn/X.
  """
  if not os.path.exists(input_csv_path):
    print(f"[Error] Input file '{input_csv_path}' not found.")
    return

  df = pd.read_csv(input_csv_path)
  review_records = []

  print(f"[Info] Processing {len(df)} leads...")

  for index, row in df.iterrows():
    name = row.get("Name", "Founder")
    company = row.get("Company", "Your Company")
    email = row.get("Email", "")
    profile_url = row.get("ProfileURL", "#")
    focus = row.get("Focus", "React and Next.js development")
    channel = row.get("Channel", "LinkedIn")

    # Generate AI-personalized pitch using Gemini
    prompt = (
        f"Write a short, professional cold outreach message (under 120 words)"
        f" to {name} at {company}, who focuses on {focus}. Pitch Nosa, an"
        f" experienced React/Next.js frontend engineer looking for contract"
        f" overflow work. Keep it direct and value-focused."
    )

    try:
      response = client.models.generate_content(
          model="gemini-3.8-flash", contents=prompt
      )
      pitch = response.text
    except Exception as e:
      print(f"[AI Error] Failed to generate pitch for {name}: {e}")
      continue

    # 1. Automated Email Dispatch (if email exists and is valid)
    if pd.notna(email) and "@" in str(email):
      try:
        msg = MIMEMultipart()
        msg["Subject"] = f"Quick React / Next.js contract bandwidth for {company}"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        msg.attach(MIMEText(pitch, "plain"))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
          server.login(SENDER_EMAIL, SENDER_PASSWORD)
          server.sendmail(msg["From"], msg["To"], msg.as_string())
        print(f"[Email Sent] Successfully delivered pitch to {name} ({email})")
      except Exception as mail_error:
        print(f"[SMTP Error] Could not send email to {name}: {mail_error}")

    # 2. Add to Review Queue for LinkedIn / X Manual Dispatch
    review_records.append({
        "Name": name,
        "Company": company,
        "Channel": channel,
        "ProfileURL": profile_url,
        "GeneratedMessage": pitch,
    })

  # Export review queue to CSV containing clickable profile links
  output_df = pd.DataFrame(review_records)
  output_df.to_csv(output_csv_path, index=False)
  print(
      f"\n[Success] Review queue exported successfully to '{output_csv_path}'."
  )
  print(
      "Open the CSV in Excel, Google Sheets, or your browser to click profile"
      " links and send messages!"
  )


if __name__ == "__main__":
  # Ensure environment variables are set before running:
  # export GEMINI_API_KEY="your-gemini-key"
  # export SENDER_EMAIL="your-email@gmail.com"
  # export SENDER_APP_PASSWORD="your-email-app-password"

  run_outreach_pipeline("leads.csv", "outreach_review_queue.csv")
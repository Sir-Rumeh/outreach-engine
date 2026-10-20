import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "outreach.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Key-value counters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                key TEXT PRIMARY KEY,
                value INTEGER
            )
        """)
        # Visitor IP telemetry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Error log audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_message TEXT,
                error_context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def log_visitor(ip_address: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO visitors (ip_address) VALUES (?)", (ip_address,))
        conn.commit()

def increment_counter(key: str, amount: int = 1):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM counters WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO counters (key, value) VALUES (?, ?)", (key, amount))
        else:
            cursor.execute("UPDATE counters SET value = value + ? WHERE key = ?", (amount, key))
        conn.commit()

def log_error(error_message: str, error_context: str = "Pipeline"):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO error_logs (error_message, error_context) VALUES (?, ?)",
            (error_message, error_context)
        )
        conn.commit()

def get_error_logs():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM error_logs ORDER BY id DESC LIMIT 50")
        return [dict(row) for row in cursor.fetchall()]

def get_telemetry_stats():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM counters")
        counters = {row["key"]: row["value"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(DISTINCT ip_address) as unique_visitors FROM visitors")
        unique_visitors = cursor.fetchone()["unique_visitors"]
        
        cursor.execute("SELECT ip_address as ip, timestamp FROM visitors ORDER BY id DESC LIMIT 20")
        recent_visitors = [dict(row) for row in cursor.fetchall()]
        
        return {
            "unique_visitors": unique_visitors,
            "counters": counters,
            "recent_visitors": recent_visitors
        }
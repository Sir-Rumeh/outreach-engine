import sqlite3
import os

DB_PATH = "outreach.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    # Pipeline execution log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            leads_processed INTEGER,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def increment_counter(key: str, amount: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM counters WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO counters (key, value) VALUES (?, ?)", (key, amount))
    else:
        cursor.execute("UPDATE counters SET value = value + ? WHERE key = ?", (amount, key))
    conn.commit()
    conn.close()

def log_visitor(ip: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO visitors (ip_address) VALUES (?)", (ip,))
    conn.commit()
    conn.close()

def get_telemetry_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get counters
    cursor.execute("SELECT key, value FROM counters")
    counters = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get total unique IPs and visitor logs
    cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM visitors")
    unique_visitors = cursor.fetchone()[0] or 0

    cursor.execute("SELECT ip_address, timestamp FROM visitors ORDER BY timestamp DESC LIMIT 10")
    recent_visitors = [{"ip": row[0], "timestamp": row[1]} for row in cursor.fetchall()]

    conn.close()
    
    return {
        "counters": counters,
        "unique_visitors": unique_visitors,
        "recent_visitors": recent_visitors
    }
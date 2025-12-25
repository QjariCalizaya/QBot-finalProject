import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH","bot.db")

def _connect():
    conn = sqlite3.connect(DB_PATH, )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA jounal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    schema= """
    CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT NOT NULL,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    UNIQUE(date, hour),
    UNIQUE(user_id, status)
    );

    CREATE TABLE IF NOT EXISTS user_state (
    user_id INTEGER PRIMARY KEY,
    state TEXT,
    data TEXT
    );
    """
    with _connect() as conn:
        conn.execute(schema)


def has_active_appointment(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM appointments WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        return cur.fetchone() is not None
    
def get_taken_hours(date: str):
    with _connect() as conn:
        cur = conn.execute(
            "SELECT hour FROM appointments WHERE date = ?",
            (date,)
        )
        return [row[0] for row in cur.fetchall()]

def create_appointment(data: dict) -> bool:
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO appointments
                (user_id, name, phone, address, date, hour, type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data["user_id"],
                data["name"],
                data["phone"],
                data["address"],
                data["date"],
                data["hour"],
                data["type"]
            ))
        return True
    except sqlite3.IntegrityError:
        return False
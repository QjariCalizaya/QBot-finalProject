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
    """
    with _connect() as conn:
        conn.execute(schema)



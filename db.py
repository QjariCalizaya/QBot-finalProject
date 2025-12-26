import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()


DB = os.getenv("DB_PATH")


def _connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,

            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,

            date TEXT NOT NULL,        
            hour INTEGER NOT NULL,     

            type TEXT NOT NULL,  
            status TEXT NOT NULL DEFAULT 'active',

            UNIQUE(date, hour),
            UNIQUE(user_id, status)
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT
        )
        """)



def has_active_appointment(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM appointments WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        return cur.fetchone() is not None



def save_user_state(user_id, state, data):
    with _connect() as conn:
        conn.execute("""
            INSERT INTO user_state (user_id, state, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET state = ?, data = ?
        """, (user_id, state, json.dumps(data), state, json.dumps(data)))



def load_user_state(user_id):
    with _connect() as conn:
        cur = conn.execute(
            "SELECT state, data FROM user_state WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if row:
            return row[0], json.loads(row[1])
        return None, {}

def get_taken_hours(date: str, exclude_user_id: int | None = None) -> list[int]:
    with _connect() as conn:
        if exclude_user_id:
            cur = conn.execute(
                """
                SELECT hour FROM appointments
                WHERE date = ? AND status = 'active' AND user_id != ?
                """,
                (date, exclude_user_id),
            )
        else:
            cur = conn.execute(
                """
                SELECT hour FROM appointments
                WHERE date = ? AND status = 'active'
                """,
                (date,),
            )
        return [row["hour"] for row in cur.fetchall()]


def create_appointment(data: dict) -> bool:
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO appointments (
                    user_id,
                    name,
                    phone,
                    address,
                    date,
                    hour,
                    type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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


def update_appointment(user_id: int, data: dict) -> bool:
    try:
        with _connect() as conn:
            conn.execute("""
                UPDATE appointments
                SET
                    name = ?,
                    phone = ?,
                    address = ?,
                    date = ?,
                    hour = ?,
                    type = ?
                WHERE user_id = ? AND status = 'active'
            """, (
                data["name"],
                data["phone"],
                data["address"],
                data["date"],
                data["hour"],
                data["type"],
                user_id
            ))
        return True
    except sqlite3.IntegrityError:
        return False

def get_active_appointment(user_id: int) -> dict | None:
    with _connect() as conn:
        cur = conn.execute("""
            SELECT
                name, phone, address, date, hour, type
            FROM appointments
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

def cancel_appointment(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE appointments
            SET status = 'cancelled'
            WHERE user_id = ? AND status = 'active'
            """,
            (user_id,)
        )
        return cur.rowcount > 0

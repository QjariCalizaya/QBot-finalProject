import os
import sqlite3
import json
from typing import Any, Dict, Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()

def _get_db_path() -> str:
    return os.getenv("DB_PATH") or "bot.sqlite3"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    #conn.execute("PRAGMA journal_mode = WAL")
    #conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
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
            status TEXT NOT NULL CHECK(status IN ('active','canceled')) DEFAULT 'active'
        )
        """)

        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_active_user
        ON appointments(user_id)
        WHERE status = 'active'
        """)

        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_active_slot
        ON appointments(date, hour)
        WHERE status = 'active'
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT
        )
        """)

        conn.commit()
    finally:
        conn.close()


def create_appointment(data: Dict[str, Any]) -> bool:
    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO appointments (
                user_id, name, phone, address, date, hour, type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            data["user_id"],
            data["name"],
            data["phone"],
            data["address"],
            data["date"],
            data["hour"],
            data["type"],
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_appointment(user_id: int, data: Dict[str, Any]) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("""
            UPDATE appointments
            SET name=?, phone=?, address=?, date=?, hour=?, type=?
            WHERE user_id=? AND status='active'
        """, (
            data["name"],
            data["phone"],
            data["address"],
            data["date"],
            data["hour"],
            data["type"],
            user_id,
        ))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def cancel_appointment(user_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("""
            UPDATE appointments
            SET status='canceled'
            WHERE user_id=? AND status='active'
        """, (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def has_active_appointment(user_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT 1 FROM appointments WHERE user_id=? AND status='active'",
            (user_id,)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def get_active_appointment(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute("""
            SELECT user_id, name, phone, address, date, hour, type
            FROM appointments
            WHERE user_id=? AND status='active'
        """, (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_taken_hours(date: str, exclude_user: Optional[int] = None) -> List[int]:
    conn = _connect()
    try:
        if exclude_user is None:
            cur = conn.execute(
                "SELECT hour FROM appointments WHERE date=? AND status='active'",
                (date,)
            )
        else:
            cur = conn.execute(
                "SELECT hour FROM appointments WHERE date=? AND status='active' AND user_id<>?",
                (date, exclude_user)
            )
        return [r["hour"] for r in cur.fetchall()]
    finally:
        conn.close()


def save_user_state(user_id: int, state: Optional[str], data: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        if state is None:
            conn.execute("DELETE FROM user_state WHERE user_id=?", (user_id,))
        else:
            conn.execute("""
                INSERT INTO user_state (user_id, state, data)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET state=excluded.state, data=excluded.data
            """, (user_id, state, json.dumps(data)))
        conn.commit()
    finally:
        conn.close()


def load_user_state(user_id: int) -> Tuple[Optional[str], Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT state, data FROM user_state WHERE user_id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None, {}
        return row["state"], json.loads(row["data"] or "{}")
    finally:
        conn.close()

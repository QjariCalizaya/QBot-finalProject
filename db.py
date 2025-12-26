import os
import sqlite3
import json
from dotenv import load_dotenv
from typing import Any, Dict, Optional, Tuple, List

load_dotenv()

DB = os.getenv("DB_PATH") or "bot.sqlite3"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            date TEXT NOT NULL,              -- ISO: YYYY-MM-DD
            hour INTEGER NOT NULL,           -- 9..17
            type TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active','canceled')) DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """)

 
        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_appointments_active_user
        ON appointments(user_id)
        WHERE status = 'active'
        """)


        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_appointments_active_slot
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


def save_user_state(user_id: int, state: Optional[str], data: Dict[str, Any]) -> None:
    with _connect() as conn:
        if state is None:
            conn.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
            return

        payload = json.dumps(data, ensure_ascii=False)
        conn.execute("""
            INSERT INTO user_state (user_id, state, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state = excluded.state,
                data  = excluded.data
        """, (user_id, state, payload))


def load_user_state(user_id: int) -> Tuple[Optional[str], Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT state, data FROM user_state WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None, {}
        state = row["state"]
        data_raw = row["data"] or "{}"
        try:
            data = json.loads(data_raw)
        except json.JSONDecodeError:
            data = {}
        return state, data


def has_active_appointment(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM appointments WHERE user_id = ? AND status = 'active' LIMIT 1",
            (user_id,)
        )
        return cur.fetchone() is not None


def get_active_appointment(user_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute("""
            SELECT user_id, name, phone, address, date, hour, type, status
            FROM appointments
            WHERE user_id = ? AND status = 'active'
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)


def get_taken_hours(date: str, exclude_user: Optional[int] = None) -> List[int]:
    with _connect() as conn:
        if exclude_user is None:
            cur = conn.execute(
                "SELECT hour FROM appointments WHERE date = ? AND status = 'active'",
                (date,)
            )
        else:
            cur = conn.execute(
                "SELECT hour FROM appointments WHERE date = ? AND status = 'active' AND user_id <> ?",
                (date, exclude_user)
            )
        return [int(r["hour"]) for r in cur.fetchall()]


def create_appointment(data: Dict[str, Any]) -> bool:
    """
    Devuelve True si inserta OK.
    Devuelve False si hay conflicto (slot tomado o ya tiene cita activa).
    """
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO appointments (
                    user_id, name, phone, address, date, hour, type, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                int(data["user_id"]),
                str(data["name"]),
                str(data["phone"]),
                str(data["address"]),
                str(data["date"]),
                int(data["hour"]),
                str(data["type"]),
            ))
        return True
    except sqlite3.IntegrityError:
        return False


def update_appointment(user_id: int, data: Dict[str, Any]) -> bool:
    """
    Actualiza la cita activa del usuario.
    Devuelve False si el nuevo slot choca con otro (o si no existe activa).
    """
    try:
        with _connect() as conn:
            cur = conn.execute("""
                UPDATE appointments
                SET name = ?,
                    phone = ?,
                    address = ?,
                    date = ?,
                    hour = ?,
                    type = ?
                WHERE user_id = ? AND status = 'active'
            """, (
                str(data["name"]),
                str(data["phone"]),
                str(data["address"]),
                str(data["date"]),
                int(data["hour"]),
                str(data["type"]),
                int(user_id),
            ))
            if cur.rowcount == 0:
                return False
        return True
    except sqlite3.IntegrityError:
        return False


def cancel_appointment(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE appointments
            SET status = 'canceled'
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        return cur.rowcount > 0

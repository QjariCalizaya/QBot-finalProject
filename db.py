import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()


DB = os.getenv("DB_PATH")


def get_connection():
    return sqlite3.connect(DB)


def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT
        )
        """)


# ✅ ¿El usuario tiene una cita activa?
def has_active_appointment(user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM appointments WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        return cur.fetchone() is not None


# 💾 Guardar estado del usuario
def save_user_state(user_id, state, data):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_state (user_id, state, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET state = ?, data = ?
        """, (user_id, state, json.dumps(data), state, json.dumps(data)))


# 📥 Cargar estado del usuario
def load_user_state(user_id):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT state, data FROM user_state WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if row:
            return row[0], json.loads(row[1])
        return None, {}

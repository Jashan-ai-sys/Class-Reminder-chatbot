import os
import sqlite3
from typing import Optional, Tuple

DB = os.getenv("DATABASE_URL", "bot.db")


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password_enc BLOB NOT NULL,
        cookie TEXT,
        cookie_expiry INTEGER
      )
    """)
    c.execute("""
      CREATE TABLE IF NOT EXISTS reminders (
        chat_id INTEGER,
        meeting_id TEXT,
        job_name TEXT,
        PRIMARY KEY(chat_id, meeting_id)
      )
    """)
    conn.commit()
    conn.close()


def save_user(chat_id: int, username: str, password_enc: bytes):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("REPLACE INTO users (chat_id, username, password_enc) VALUES (?, ?, ?)",
              (chat_id, username, password_enc))
    conn.commit()
    conn.close()


def get_user(chat_id: int) -> Optional[Tuple[str, bytes, Optional[str], Optional[int]]]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username, password_enc, cookie, cookie_expiry FROM users WHERE chat_id=?",
              (chat_id,))
    row = c.fetchone()
    conn.close()
    return row


def delete_user(chat_id: int):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()


def add_reminder_record(chat_id: int, meeting_id: str, job_name: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("REPLACE INTO reminders (chat_id, meeting_id, job_name) VALUES (?, ?, ?)",
              (chat_id, meeting_id, job_name))
    conn.commit()
    conn.close()


def get_reminder_records(chat_id: int):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT meeting_id, job_name FROM reminders WHERE chat_id=?", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def delete_reminder_record(chat_id: int, meeting_id: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE chat_id=? AND meeting_id=?", (chat_id, meeting_id))
    conn.commit()
    conn.close()

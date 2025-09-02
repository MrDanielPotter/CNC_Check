
import sqlite3, json, time, os
from typing import Any, Dict, Optional, List, Tuple

DB_NAME = "app.db"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_no TEXT NOT NULL,
  operator_name TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  completed_at INTEGER,
  status TEXT NOT NULL DEFAULT 'active' -- active|completed|abandoned
);
CREATE TABLE IF NOT EXISTS steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  block_index INTEGER NOT NULL,
  item_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  hint TEXT,
  critical INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending', -- pending|in_progress|done|failed
  started_at INTEGER,
  completed_at INTEGER,
  duration_sec INTEGER,
  note TEXT,
  override_by_master INTEGER NOT NULL DEFAULT 0,
  override_master_name TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_steps_unique ON steps(session_id, block_index, item_index);

CREATE TABLE IF NOT EXISTS step_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id INTEGER NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
  changed_at INTEGER NOT NULL,
  old_status TEXT,
  new_status TEXT,
  note TEXT
);
CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id INTEGER NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  added_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  level TEXT NOT NULL,     -- INFO|WARN|ERROR|AUDIT
  action TEXT NOT NULL,    -- e.g. 'pin_change','critical_override','email_send','pdf_generate'
  details TEXT             -- JSON string with details
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""

class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.executescript(SCHEMA)
        self.conn.commit()
        if self.get_setting("report_seq") is None:
            self.set_setting("report_seq", "0")

    def get_setting(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self.conn.commit()

    def bump_report_seq(self) -> int:
        seq = int(self.get_setting("report_seq") or "0") + 1
        self.set_setting("report_seq", str(seq))
        return seq

    def create_session(self, order_no: str, operator_name: str) -> int:
        ts = int(time.time())
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sessions(order_no, operator_name, started_at) VALUES(?,?,?)",
                    (order_no, operator_name, ts))
        self.conn.commit()
        return cur.lastrowid

    def get_active_session(self) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE status='active' ORDER BY id DESC LIMIT 1")
        return cur.fetchone()

    def mark_session_completed(self, session_id: int):
        ts = int(time.time())
        cur = self.conn.cursor()
        cur.execute("UPDATE sessions SET status='completed', completed_at=? WHERE id=?", (ts, session_id))
        self.conn.commit()

    def ensure_steps_for_session(self, session_id: int, checklist: Dict[str, Any]):
        cur = self.conn.cursor()
        for bi, block in enumerate(checklist["blocks"]):
            for ii, item in enumerate(block["items"]):
                cur.execute("""
                    INSERT OR IGNORE INTO steps(session_id, block_index, item_index, text, hint, critical)
                    VALUES(?,?,?,?,?,?)
                """, (session_id, bi, ii, item["text"], item.get("hint"), 1 if item.get("critical") else 0))
        self.conn.commit()

    def get_steps(self, session_id: int) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM steps WHERE session_id=? ORDER BY block_index, item_index", (session_id,))
        return cur.fetchall()

    def update_step_status(self, step_id: int, new_status: str, note: Optional[str] = None):
        cur = self.conn.cursor()
        cur.execute("SELECT status, started_at FROM steps WHERE id=?", (step_id,))
        row = cur.fetchone()
        old_status = row["status"] if row else None
        now = int(time.time())
        started_at = row["started_at"]

        # if moving from pending to in_progress, set started_at
        if new_status == "in_progress" and not started_at:
            cur.execute("UPDATE steps SET status=?, started_at=? WHERE id=?", (new_status, now, step_id))
        elif new_status in ("done", "failed"):
            # set completed_at and duration
            cur.execute("SELECT started_at FROM steps WHERE id=?", (step_id,))
            srow = cur.fetchone()
            s_at = srow["started_at"] if srow else None
            if not s_at:
                s_at = now
                cur.execute("UPDATE steps SET started_at=? WHERE id=?", (s_at, step_id))
            duration = max(0, now - s_at)
            cur.execute("UPDATE steps SET status=?, completed_at=?, duration_sec=?, note=? WHERE id=?",
                        (new_status, now, duration, note, step_id))
        else:
            cur.execute("UPDATE steps SET status=?, note=? WHERE id=?", (new_status, note, step_id))

        # version trail
        cur.execute("INSERT INTO step_versions(step_id, changed_at, old_status, new_status, note) VALUES(?,?,?,?,?)",
                    (step_id, now, old_status, new_status, note))
        self.conn.commit()

    def set_step_master_override(self, step_id: int, master_name: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE steps SET override_by_master=1, override_master_name=? WHERE id=?", (master_name, step_id))
        self.conn.commit()

    def add_photo(self, step_id: int, file_path: str):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO photos(step_id, file_path, added_at) VALUES(?,?,?)",
                    (step_id, file_path, int(time.time())))
        self.conn.commit()

    def get_photos_for_step(self, step_id: int) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM photos WHERE step_id=? ORDER BY id", (step_id,))
        return cur.fetchall()

    def log(self, level: str, action: str, details: Dict[str, Any]):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO logs(ts, level, action, details) VALUES(?,?,?,?)",
                    (int(time.time()), level, action, json.dumps(details, ensure_ascii=False)))
        self.conn.commit()

    def add_report(self, session_id: int, seq: int, file_path: str):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO reports(session_id, seq, file_path, created_at) VALUES(?,?,?,?)",
                    (session_id, seq, file_path, int(time.time())))
        self.conn.commit()

    def list_reports(self, order_no_like: Optional[str] = None) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        if order_no_like:
            cur.execute("""
              SELECT r.*, s.order_no FROM reports r
              JOIN sessions s ON s.id=r.session_id
              WHERE s.order_no LIKE ? ORDER BY r.id DESC
            """, (f"%{order_no_like}%",))
        else:
            cur.execute("""
              SELECT r.*, s.order_no FROM reports r
              JOIN sessions s ON s.id=r.session_id
              ORDER BY r.id DESC
            """)
        return cur.fetchall()

"""Local SQLite task metadata. Run state, cookies, logs and screenshots also stay on disk."""
import json
from pathlib import Path
import sqlite3
import time


class SessionStore:
    def __init__(self, path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, goal TEXT NOT NULL, skill TEXT, provider TEXT NOT NULL,
                mode TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL,
                started REAL, finished REAL, error TEXT, trigger_id TEXT UNIQUE)''')

    def connect(self):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;return db

    def create(self, run_id, goal, skill=None, provider='claude', mode='agent', trigger_id=None):
        with self.connect() as db:
            db.execute('INSERT INTO sessions(id,goal,skill,provider,mode,status,created,trigger_id) VALUES (?,?,?,?,?,?,?,?)',
                       (run_id,goal,skill,provider,mode,'queued',time.time(),trigger_id))
        return self.get(run_id)

    def get(self, run_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM sessions WHERE id=?',(run_id,)).fetchone()
        if row is None: raise KeyError(run_id)
        return dict(row)

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM sessions ORDER BY created DESC LIMIT 500')]

    def by_trigger(self, trigger_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM sessions WHERE trigger_id=?',(trigger_id,)).fetchone()
        return dict(row) if row else None

    def update(self, run_id, **fields):
        if not fields or not set(fields)<= {'status','started','finished','error','skill'}:
            raise ValueError('Invalid session update')
        with self.connect() as db:
            db.execute('UPDATE sessions SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),run_id))

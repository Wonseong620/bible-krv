"""Daily successful-generation quota. No conversations or user identifiers stored."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from . import trends
except ImportError:
    import trends

TIMEZONE = ZoneInfo('Asia/Seoul')
LIMIT = 100


class QuotaExceeded(Exception):
    pass


class Quota:
    def __init__(self, path, clock=None):
        self.path = str(path)
        self.clock = clock or (lambda: datetime.now(TIMEZONE))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            trends.initialize(conn)
            conn.execute('CREATE TABLE IF NOT EXISTS daily_responses (day TEXT PRIMARY KEY, completed INTEGER NOT NULL CHECK(completed BETWEEN 0 AND 100))')

    def day(self):
        return self.clock().astimezone(TIMEZONE).date()

    def status(self):
        day = self.day()
        with sqlite3.connect(self.path, timeout=1) as conn:
            row = conn.execute('SELECT completed FROM daily_responses WHERE day=?', (day.isoformat(),)).fetchone()
        completed = row[0] if row else 0
        return {'limit': LIMIT, 'completed': completed, 'remaining': LIMIT-completed,
                'timezone': 'Asia/Seoul', 'resets_at': datetime.combine(day+timedelta(days=1), datetime.min.time(), TIMEZONE).isoformat()}

    def trends(self):
        with sqlite3.connect(self.path, timeout=1) as conn:
            return trends.read(conn, self.day().isoformat())

    def run(self, generate, labels=None):
        # Hold a single writer transaction until generation completes. WAL readers
        # (health/status) remain available. Failure or process exit rolls back.
        conn = sqlite3.connect(self.path, timeout=1)
        try:
            conn.execute('BEGIN IMMEDIATE')
            day = self.day().isoformat()
            row = conn.execute('SELECT completed FROM daily_responses WHERE day=?', (day,)).fetchone()
            if row and row[0] >= LIMIT: raise QuotaExceeded()
            result = generate()
            # Count against the day the response completes, including midnight rollover.
            day = self.day().isoformat()
            conn.execute('INSERT OR IGNORE INTO daily_responses(day, completed) VALUES (?,0)', (day,))
            updated = conn.execute('UPDATE daily_responses SET completed=completed+1 WHERE day=? AND completed<?', (day,LIMIT))
            if updated.rowcount != 1: raise QuotaExceeded()
            if labels:
                trends.record(conn, day, labels)
            conn.commit()
            return result
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

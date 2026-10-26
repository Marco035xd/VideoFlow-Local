"""A temporary archive of queue records. Media files are never moved or deleted."""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager

RETENTION_SECONDS = 30 * 24 * 60 * 60


class RemovedDownloads:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.private = {}
        with self.connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS removed_downloads (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                removed_at REAL NOT NULL, expires_at REAL NOT NULL)''')
            self.purge(con)

    @contextmanager
    def connect(self):
        with self.lock:
            con = sqlite3.connect(self.path, timeout=20)
            con.row_factory = sqlite3.Row
            try:
                with con:
                    yield con
            finally:
                con.close()

    def purge(self, con):
        cutoff = time.time()
        con.execute('DELETE FROM removed_downloads WHERE expires_at <= ?', (cutoff,))
        self.private = {key: value for key, value in self.private.items() if value['expires_at'] > cutoff}

    def put(self, payload):
        timestamp = time.time()
        record = dict(payload=payload, removed_at=timestamp, expires_at=timestamp + RETENTION_SECONDS)
        with self.connect() as con:
            self.purge(con)
            if payload.get('advanced', {}).get('incognito'):
                self.private[payload['id']] = record
            else:
                con.execute('INSERT OR REPLACE INTO removed_downloads VALUES (?, ?, ?, ?)',
                            (payload['id'], json.dumps(payload, ensure_ascii=False), timestamp, record['expires_at']))

    def list(self):
        with self.connect() as con:
            self.purge(con)
            records = [dict(payload=json.loads(row['payload']), removed_at=row['removed_at'],
                            expires_at=row['expires_at']) for row in con.execute('SELECT * FROM removed_downloads')]
            records.extend(self.private.values())
            return sorted(records, key=lambda item: item['removed_at'], reverse=True)

    def get(self, identifier):
        return next((record for record in self.list() if record['payload']['id'] == identifier), None)

    def delete(self, identifier):
        with self.connect() as con:
            self.purge(con)
            removed = self.private.pop(identifier, None)
            count = con.execute('DELETE FROM removed_downloads WHERE id = ?', (identifier,)).rowcount
            if not removed and not count:
                raise KeyError('Registro temporal no encontrado o vencido.')

"""A temporary archive of queue records. Media files are never moved or deleted."""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager

RETENTION_OPTIONS = (7, 15, 30)
DEFAULT_RETENTION_DAYS = 30


def normalize_retention_days(value):
    return value if type(value) is int and value in RETENTION_OPTIONS else DEFAULT_RETENTION_DAYS


class RemovedDownloads:
    def __init__(self, path, retention_days=DEFAULT_RETENTION_DAYS):
        self.path = path
        self.lock = threading.RLock()
        self.private = {}
        self.retention_days = normalize_retention_days(retention_days)
        with self.connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS removed_downloads (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                removed_at REAL NOT NULL, expires_at REAL NOT NULL)''')
        self.set_retention(self.retention_days)

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

    def set_retention(self, days):
        if type(days) is not int or days not in RETENTION_OPTIONS:
            raise ValueError('Selecciona 7, 15 o 30 días de conservación.')
        with self.connect() as con:
            # Expired records must not return when the retention period increases.
            self.purge(con)
            seconds = days * 24 * 60 * 60
            con.execute('UPDATE removed_downloads SET expires_at = removed_at + ?', (seconds,))
            for record in self.private.values():
                record['expires_at'] = record['removed_at'] + seconds
            self.purge(con)
            self.retention_days = days

    def put(self, payload):
        with self.connect() as con:
            timestamp = time.time()
            record = dict(payload=payload, removed_at=timestamp,
                          expires_at=timestamp + self.retention_days * 24 * 60 * 60)
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

    def delete_many(self, identifiers):
        """Remove available records in one transaction and return their identifiers."""
        requested = set(identifiers)
        with self.lock:
            with self.connect() as con:
                self.purge(con)
                stored = {row['id'] for row in con.execute('SELECT id FROM removed_downloads')}
                found = requested & (stored | set(self.private))
                con.executemany('DELETE FROM removed_downloads WHERE id = ?',
                                ((identifier,) for identifier in found & stored))
            for identifier in found:
                self.private.pop(identifier, None)
            return found

"""Local SQLite database: users, settings, backup and restore."""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("aimlab.db")
SCHEMA_VERSION = 1


class DatabaseError(Exception):
    pass


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = self._open(self.path)
        self._migrate()

    @staticmethod
    def _open(path):
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _migrate(self):
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(
                    key TEXT PRIMARY KEY, value TEXT NOT NULL);
                PRAGMA user_version=1;
                """
            )
            log.info("Database created/migrated to version 1")
        elif version > SCHEMA_VERSION:
            raise DatabaseError("Database was created by a newer version of AIMLAB PRO.")

    def close(self):
        self._conn.close()

    # ---- users
    def create_user(self, name: str) -> int:
        name = (name or "").strip()
        if not name:
            raise ValueError("empty")
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO users(name, created_at) VALUES(?, ?)",
                    (name, datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError as e:
            raise ValueError("duplicate") from e
        return cur.lastrowid

    def list_users(self):
        return [dict(r) for r in self._conn.execute("SELECT * FROM users ORDER BY id")]

    def get_user(self, user_id):
        r = self._conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(r) if r else None

    def ensure_default_user(self, name="Player") -> int:
        users = self.list_users()
        return users[0]["id"] if users else self.create_user(name)

    # ---- settings
    def get_setting(self, key, default=None):
        r = self._conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key, value):
        with self._conn:
            self._conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    # ---- backup / restore
    def backup(self, dest):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(str(dest))
        try:
            self._conn.backup(target)
        finally:
            target.close()
        log.info("Backup written to %s", dest)

    def restore(self, src):
        src = Path(src)
        if not src.is_file():
            raise DatabaseError("Backup file not found.")
        probe = None
        try:
            probe = sqlite3.connect(str(src))
            ok = probe.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            tables = {r[0] for r in probe.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            ver = probe.execute("PRAGMA user_version").fetchone()[0]
            if not ok or not {"users", "settings"} <= tables or ver > SCHEMA_VERSION:
                raise DatabaseError("This is not a valid AIMLAB PRO backup.")
            safety = self.path.with_suffix(".before-restore.bak")
            self.backup(safety)
            probe.backup(self._conn)
        except sqlite3.DatabaseError as e:
            raise DatabaseError("This is not a valid AIMLAB PRO backup.") from e
        finally:
            if probe:
                probe.close()
        self._migrate()
        log.info("Database restored from %s", src)

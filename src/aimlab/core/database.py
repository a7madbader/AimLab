"""Local SQLite database: users, settings, backup and restore."""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("aimlab.db")
SCHEMA_VERSION = 2

MIGRATIONS = {
    1: """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """,
    2: """
        CREATE TABLE IF NOT EXISTS mouse_profiles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL COLLATE NOCASE,
            dpi REAL NOT NULL,
            polling_hz REAL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, name));
        CREATE TABLE IF NOT EXISTS calibration_results(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mouse_profile_id INTEGER REFERENCES mouse_profiles(id) ON DELETE SET NULL,
            kind TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL);
    """,
}


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
        if version > SCHEMA_VERSION:
            raise DatabaseError("Database was created by a newer version of AIMLAB PRO.")
        for v in range(version + 1, SCHEMA_VERSION + 1):
            self._conn.executescript(MIGRATIONS[v] + f"PRAGMA user_version={v};")
            log.info("Database migrated to version %d", v)

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

    # ---- mouse profiles
    @staticmethod
    def _check_profile_values(name, dpi, polling_hz):
        name = (name or "").strip()
        if not name:
            raise ValueError("empty")
        try:
            dpi = float(dpi)
        except (TypeError, ValueError):
            raise ValueError("dpi")
        if not 50 <= dpi <= 100000:
            raise ValueError("dpi")
        if polling_hz is not None:
            polling_hz = float(polling_hz)
            if not 1 <= polling_hz <= 100000:
                raise ValueError("polling")
        return name, dpi, polling_hz

    def create_mouse_profile(self, user_id, name, dpi, polling_hz=None, notes=""):
        name, dpi, polling_hz = self._check_profile_values(name, dpi, polling_hz)
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO mouse_profiles(user_id,name,dpi,polling_hz,notes,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (user_id, name, dpi, polling_hz, notes, datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError as e:
            raise ValueError("duplicate") from e
        return cur.lastrowid

    def list_mouse_profiles(self, user_id):
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM mouse_profiles WHERE user_id=? ORDER BY id", (user_id,))]

    def get_mouse_profile(self, profile_id):
        r = self._conn.execute("SELECT * FROM mouse_profiles WHERE id=?", (profile_id,)).fetchone()
        return dict(r) if r else None

    def update_mouse_profile(self, profile_id, **fields):
        current = self.get_mouse_profile(profile_id)
        if not current:
            raise ValueError("unknown profile")
        allowed = {"name", "dpi", "polling_hz", "notes"}
        if not set(fields) <= allowed:
            raise ValueError("bad field")
        merged = {**current, **fields}
        name, dpi, hz = self._check_profile_values(merged["name"], merged["dpi"], merged["polling_hz"])
        try:
            with self._conn:
                self._conn.execute(
                    "UPDATE mouse_profiles SET name=?, dpi=?, polling_hz=?, notes=? WHERE id=?",
                    (name, dpi, hz, merged["notes"], profile_id))
        except sqlite3.IntegrityError as e:
            raise ValueError("duplicate") from e

    def delete_mouse_profile(self, profile_id):
        with self._conn:
            self._conn.execute("DELETE FROM mouse_profiles WHERE id=?", (profile_id,))

    # ---- calibration results
    def add_calibration_result(self, user_id, kind, data: dict, mouse_profile_id=None):
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO calibration_results(user_id,mouse_profile_id,kind,data,created_at)"
                " VALUES(?,?,?,?,?)",
                (user_id, mouse_profile_id, kind, json.dumps(data, ensure_ascii=False),
                 datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid

    def list_calibration_results(self, user_id, kind=None, limit=50):
        sql = "SELECT * FROM calibration_results WHERE user_id=?"
        args = [user_id]
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        out = []
        for r in self._conn.execute(sql, args):
            d = dict(r)
            d["data"] = json.loads(d["data"])
            out.append(d)
        return out

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

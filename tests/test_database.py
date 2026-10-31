import tempfile
import unittest
from pathlib import Path

from aimlab.core.database import Database, DatabaseError
from aimlab.core.settings import Settings


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = Database(self.dir / "t.db")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_users_create_unique_and_empty(self):
        uid = self.db.create_user("Ali")
        self.assertEqual(self.db.get_user(uid)["name"], "Ali")
        with self.assertRaises(ValueError):
            self.db.create_user("ali")      # case-insensitive duplicate
        with self.assertRaises(ValueError):
            self.db.create_user("   ")

    def test_arabic_user_names(self):
        uid = self.db.create_user("محمد")
        self.assertEqual(self.db.get_user(uid)["name"], "محمد")

    def test_settings_persist_after_reopen(self):
        s = Settings(self.db)
        s.language = "ar"
        uid = self.db.create_user("Sara")
        s.active_user_id = uid
        self.db.close()
        db2 = Database(self.dir / "t.db")
        s2 = Settings(db2)
        self.assertEqual(s2.language, "ar")
        self.assertEqual(s2.active_user_id, uid)
        db2.close()
        self.db = Database(self.dir / "t.db")   # for tearDown

    def test_defaults_and_validation(self):
        s = Settings(self.db)
        self.assertEqual(s.language, "en")
        with self.assertRaises(ValueError):
            s.language = "fr"
        self.assertEqual(self.db.get_user(s.active_user_id)["name"], "Player")

    def test_backup_and_restore(self):
        s = Settings(self.db)
        s.language = "ar"
        self.db.create_user("Keep")
        self.db.backup(self.dir / "bk" / "backup.db")
        s.language = "en"
        self.db.create_user("Temp")
        self.db.restore(self.dir / "bk" / "backup.db")
        names = [u["name"] for u in self.db.list_users()]
        self.assertIn("Keep", names)
        self.assertNotIn("Temp", names)
        self.assertEqual(Settings(self.db).language, "ar")

    def test_restore_rejects_garbage(self):
        bad = self.dir / "bad.db"
        bad.write_bytes(b"this is not a database")
        with self.assertRaises(DatabaseError):
            self.db.restore(bad)
        with self.assertRaises(DatabaseError):
            self.db.restore(self.dir / "missing.db")
        self.assertEqual(Settings(self.db).language, "en")   # untouched


if __name__ == "__main__":
    unittest.main()


class MouseProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = Database(self.dir / "t.db")
        self.settings = Settings(self.db)
        self.uid = self.settings.active_user_id

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_v1_database_upgrades_without_losing_data(self):
        import sqlite3
        old = self.dir / "old.db"
        c = sqlite3.connect(old)
        c.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE, created_at TEXT NOT NULL);
            CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO users(name, created_at) VALUES('Old User','2026-01-01');
            INSERT INTO settings VALUES('language','ar'); PRAGMA user_version=1;""")
        c.commit(); c.close()
        db = Database(old)
        try:
            self.assertEqual(db.list_users()[0]["name"], "Old User")
            self.assertEqual(Settings(db).language, "ar")
            pid = db.create_mouse_profile(1, "G Pro", 800)
            self.assertEqual(db.get_mouse_profile(pid)["dpi"], 800)
        finally:
            db.close()

    def test_profile_crud_and_validation(self):
        pid = self.db.create_mouse_profile(self.uid, "Razer", 1600, 1000, "notes")
        self.assertEqual(self.db.list_mouse_profiles(self.uid)[0]["name"], "Razer")
        self.db.update_mouse_profile(pid, dpi=800.5, polling_hz=500)
        p = self.db.get_mouse_profile(pid)
        self.assertEqual((p["dpi"], p["polling_hz"]), (800.5, 500))
        for bad in (("", 800), ("X", 0), ("X", -1), ("X", 999999), ("X", "abc")):
            with self.assertRaises(ValueError):
                self.db.create_mouse_profile(self.uid, *bad)
        with self.assertRaises(ValueError):
            self.db.create_mouse_profile(self.uid, "razer", 800)   # duplicate, case-insensitive
        self.db.delete_mouse_profile(pid)
        self.assertEqual(self.db.list_mouse_profiles(self.uid), [])

    def test_active_profile_per_user(self):
        a = self.db.create_mouse_profile(self.uid, "A", 800)
        self.assertIsNone(self.settings.active_mouse_profile_id)
        self.settings.active_mouse_profile_id = a
        self.assertEqual(self.settings.active_mouse_profile_id, a)
        other = self.db.create_user("Other")
        b = self.db.create_mouse_profile(other, "B", 400)
        with self.assertRaises(ValueError):
            self.settings.active_mouse_profile_id = b        # belongs to another user
        self.db.delete_mouse_profile(a)
        self.assertIsNone(self.settings.active_mouse_profile_id)

    def test_calibration_results_roundtrip_arabic(self):
        self.db.add_calibration_result(self.uid, "polling", {"hz": 998.4, "note": "جيد"})
        self.db.add_calibration_result(self.uid, "dpi", {"dpi": 812})
        rows = self.db.list_calibration_results(self.uid, "polling")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["data"]["note"], "جيد")
        self.assertEqual(len(self.db.list_calibration_results(self.uid)), 2)

    def test_restore_older_backup_gets_upgraded(self):
        import sqlite3
        old = self.dir / "v1.db"
        c = sqlite3.connect(old)
        c.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE, created_at TEXT NOT NULL);
            CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO users(name, created_at) VALUES('Backup User','2026-01-01'); PRAGMA user_version=1;""")
        c.commit(); c.close()
        self.db.restore(old)
        self.assertEqual(self.db.list_users()[0]["name"], "Backup User")
        self.db.create_mouse_profile(self.db.list_users()[0]["id"], "Works", 800)

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

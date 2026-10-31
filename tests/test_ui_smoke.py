"""Starts the real window headlessly. Skipped automatically where PySide6 isn't installed
(it isn't in the Linux dev sandbox; it runs on the Windows build server)."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class UiSmoke(unittest.TestCase):
    def test_window_navigation_and_language_switch(self):
        # ignore_cleanup_errors: Windows may hold the db file for a moment after close.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            os.environ["AIMLAB_DATA_DIR"] = d
            from aimlab.main import build_context, run_selftest
            from aimlab.ui.theme import stylesheet
            app = QApplication.instance() or QApplication([])
            app.setStyleSheet(stylesheet())
            ctx = build_context()
            try:
                self.assertEqual(run_selftest(app, ctx), 0)
                self.assertEqual(ctx.settings.language, "en")
            finally:
                ctx.db.close()   # Windows cannot delete a file that is still open


if __name__ == "__main__":
    unittest.main()

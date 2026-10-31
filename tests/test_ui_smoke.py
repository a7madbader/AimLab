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


class FakeCapture:
    """Stands in for the real mouse: hands out a prepared list of samples."""
    available = True

    def __init__(self):
        self.queue = []
        self.started = 0

    def start(self):
        self.started += 1

    def stop(self):
        pass

    def drain(self):
        out, self.queue = self.queue, []
        return out


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class CalibrationPageSmoke(unittest.TestCase):
    def test_full_calibration_workflow_with_fake_mouse(self):
        from tests.synth import steady_stream, swipe
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            os.environ["AIMLAB_DATA_DIR"] = d
            from aimlab.main import build_context
            from aimlab.ui.calibration_page import CalibrationPage
            from aimlab.ui.main_window import MainWindow
            from aimlab.ui.theme import stylesheet
            app = QApplication.instance() or QApplication([])
            app.setStyleSheet(stylesheet())
            ctx = build_context()
            try:
                win = MainWindow(ctx)
                page = win.pages[2]
                self.assertIsInstance(page, CalibrationPage)
                fake = FakeCapture()
                page.capture = fake
                uid = ctx.settings.active_user_id

                # profile -> becomes active, dashboard shows it
                page.pr_name.setText("Test Mouse")
                page.pr_dpi.setValue(800)
                page._profile_add()
                self.assertIsNotNone(ctx.settings.active_mouse_profile_id)
                self.assertIn("Test Mouse", win.pages[0].cards["calibration"].value.text())

                # polling through the public apply method
                r = page.apply_polling(steady_stream(1000, 5))
                self.assertTrue(r.ok)
                self.assertIn("1000", page.poll_result.text())
                page._save_hz()
                self.assertEqual(ctx.db.list_mouse_profiles(uid)[0]["polling_hz"], 1000)

                # DPI through the real start -> Space path using the fake mouse
                page.dpi_dist.setValue(20)
                fake.queue = swipe(round(800 * 20 / 2.54), 1.0)
                page._dpi_start()
                self.assertEqual(page._mode, "dpi")
                page._on_space()
                self.assertIsNone(page._mode)
                self.assertIn("800", page.dpi_result.text())

                # acceleration: three swipes
                for counts, dur in ((6300, 1.5), (6310, 0.6), (6290, 0.2)):
                    fake.queue = swipe(counts, dur)
                    page._accel_start()
                    page._on_space()
                self.assertTrue(page.acc_result.text())

                # smoothness
                fake.queue = swipe(6000, 1.0)
                page._smooth_start()
                page._on_space()
                self.assertIn("%", page.sm_result.text())

                # everything was stored
                kinds = {r["kind"] for r in ctx.db.list_calibration_results(uid)}
                self.assertEqual(kinds, {"polling", "dpi", "acceleration", "smoothness"})

                # calculator
                page.c_dpi.setValue(800)
                page.c_sens.setValue(1.0)
                self.assertIn("51.9", page.c_cm.text())

                # Arabic: whole window re-translates, tabs and explanation included
                ctx.settings.language = "ar"
                ctx.tr.set_language("ar")
                win.apply_language()
                self.assertEqual(page.tabs.tabText(1), ctx.tr.t("calib.tab.polling"))
                self.assertIn(ctx.tr.t("calib.polling.what"), page.explain["polling"].text.text())
            finally:
                ctx.db.close()


if __name__ == "__main__":
    unittest.main()

import logging
import sys

from . import __version__
from .core import paths
from .core.context import AppContext
from .core.database import Database
from .core.logging_setup import setup_logging
from .core.settings import Settings
from .localization.i18n import Translator


def build_context() -> AppContext:
    db = Database(paths.db_path())
    settings = Settings(db)
    settings.active_user_id  # makes sure a default profile exists
    return AppContext(db, settings, Translator(settings.language))


def run_selftest(app, ctx) -> int:
    """Used by the automated Windows build to prove the real .exe starts and works."""
    from .ui.main_window import NAV, MainWindow
    log = logging.getLogger("aimlab")
    win = MainWindow(ctx)
    win.show()
    app.processEvents()
    assert win.nav.count() == len(NAV) == 10, "navigation must have 10 pages"
    for i in range(win.nav.count()):
        win.nav.setCurrentRow(i)
        app.processEvents()
    for lang in ("ar", "en"):
        ctx.settings.language = lang
        ctx.tr.set_language(lang)
        win.apply_language()
        app.processEvents()
    # Informational only (never fails the self-test): can raw mouse capture start in this build?
    try:
        from .mouse.capture import create_capture
        cap = create_capture()
        cap.start()
        cap.stop()
        log.info("SELFTEST raw input capture: start/stop OK (available=%s)", cap.available)
    except Exception as e:
        log.warning("SELFTEST raw input capture not available here: %s", e)
    log.info("SELFTEST PASSED (v%s)", __version__)
    win.close()
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    log = setup_logging()
    log.info("Starting AIMLAB PRO v%s", __version__)
    from PySide6.QtWidgets import QApplication
    from .ui.main_window import MainWindow
    from .ui.theme import stylesheet
    app = QApplication(argv)
    app.setApplicationName("AIMLAB PRO")
    app.setStyleSheet(stylesheet())
    ctx = build_context()
    if "--selftest" in argv:
        try:
            return run_selftest(app, ctx)
        except Exception:
            log.exception("SELFTEST FAILED")
            return 1
    win = MainWindow(ctx)
    win.show()
    return app.exec()

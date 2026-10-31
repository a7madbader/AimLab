import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget,
                               QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from .. import __version__
from ..core import paths
from ..core.context import AppContext
from .calibration_page import CalibrationPage
from .pages import BasePage, DashboardPage, SettingsPage
from .theme import stylesheet

log = logging.getLogger("aimlab.ui")

# (key, phase in which the real page is built; None = already implemented)
NAV = [("dashboard", None), ("sensitivity", 3), ("calibration", None), ("analysis", 4),
       ("ai", 5), ("training", 7), ("games", 6), ("history", 8), ("reports", 8),
       ("settings", None)]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)
        icon = paths.asset_path("aimlab.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(250)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 12)
        self.brand = QLabel("AIMLAB PRO")
        self.brand.setObjectName("Brand")
        self.tagline = QLabel()
        self.tagline.setObjectName("Tagline")
        self.tagline.setWordWrap(True)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.version = QLabel(f"v{__version__}")
        self.version.setObjectName("Tagline")
        for w in (self.brand, self.tagline, self.nav):
            sl.addWidget(w)
        sl.addWidget(self.version)

        self.stack = QStackedWidget()
        self.pages: list[BasePage] = []
        for key, phase in NAV:
            if key == "dashboard":
                page = DashboardPage(ctx, key)
            elif key == "calibration":
                page = CalibrationPage(ctx, self.apply_language)
            elif key == "settings":
                page = SettingsPage(ctx, self.apply_language)
            else:
                page = BasePage(ctx, key, planned_phase=phase)
            self.pages.append(page)
            self.stack.addWidget(page)
            self.nav.addItem("")
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        root.addWidget(side)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.apply_language()
        self.nav.setCurrentRow(0)

    def apply_language(self):
        """Re-translate everything and flip layout direction for Arabic."""
        tr = self.ctx.tr
        QApplication.setLayoutDirection(Qt.RightToLeft if tr.is_rtl else Qt.LeftToRight)
        self.setWindowTitle(tr.t("app.title"))
        self.tagline.setText(tr.t("app.tagline"))
        for i, (key, _) in enumerate(NAV):
            self.nav.item(i).setText(tr.t(f"nav.{key}"))
        for page in self.pages:
            page.retranslate()
        log.info("Language applied: %s", tr.lang)

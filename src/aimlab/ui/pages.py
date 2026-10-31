"""Page widgets. Every page has retranslate() so the language can change instantly."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget)

from ..core.context import AppContext


class BasePage(QWidget):
    add_stretch = True

    def __init__(self, ctx: AppContext, key: str, planned_phase=None):
        super().__init__()
        self.ctx, self.key, self.planned_phase = ctx, key, planned_phase
        self.setObjectName("Content")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(32, 28, 32, 28)
        self.layout_.setSpacing(14)
        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        self.desc = QLabel()
        self.desc.setObjectName("PageDesc")
        self.desc.setWordWrap(True)
        self.layout_.addWidget(self.title)
        self.layout_.addWidget(self.desc)
        self.planned = None
        if planned_phase is not None:
            self.planned = QLabel()
            self.planned.setObjectName("Planned")
            self.planned.setWordWrap(True)
            self.layout_.addWidget(self.planned)
        self.build()
        if self.add_stretch:
            self.layout_.addStretch(1)

    def build(self):
        """Subclasses add their own widgets here."""

    def retranslate(self):
        t = self.ctx.tr.t
        self.title.setText(t(f"nav.{self.key}"))
        self.desc.setText(t(f"pages.{self.key}.desc"))
        if self.planned is not None:
            self.planned.setText(t("common.coming_in_phase", phase=self.planned_phase))


class Card(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        self.title = QLabel()
        self.title.setObjectName("CardTitle")
        self.value = QLabel()
        self.value.setObjectName("CardValue")
        self.value.setWordWrap(True)
        lay.addWidget(self.title)
        lay.addWidget(self.value)


class DashboardPage(BasePage):
    def build(self):
        grid = QGridLayout()
        grid.setSpacing(14)
        self.cards = {k: Card() for k in ("profile", "database", "calibration", "tests", "phase")}
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 2, i % 2)
        self.layout_.addLayout(grid)

    def retranslate(self):
        super().retranslate()
        t = self.ctx.tr.t
        user = self.ctx.db.get_user(self.ctx.settings.active_user_id)
        name = user["name"] if user else "-"
        self.title.setText(t("dashboard.welcome", name=name))
        mp_id = self.ctx.settings.active_mouse_profile_id
        mp = self.ctx.db.get_mouse_profile(mp_id) if mp_id else None
        calib = (t("dashboard.calibration_value", name=mp["name"], dpi=f"{mp['dpi']:g}")
                 if mp else t("dashboard.not_calibrated"))
        values = {"profile": name, "database": t("dashboard.database_ok"),
                  "calibration": calib, "tests": "0",
                  "phase": t("dashboard.phase_value")}
        for k, card in self.cards.items():
            card.title.setText(t(f"dashboard.{k}"))
            card.value.setText(values[k])


class SettingsPage(BasePage):
    def __init__(self, ctx, on_language_changed):
        super().__init__(ctx, "settings")
        self._on_language_changed = on_language_changed

    def build(self):
        self.lang_label = QLabel()
        self.lang_label.setObjectName("Section")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("", "en")
        self.lang_combo.addItem("", "ar")
        self.lang_hint = QLabel()
        self.lang_hint.setObjectName("PageDesc")
        self.lang_combo.setCurrentIndex(0 if self.ctx.settings.language == "en" else 1)
        self.lang_combo.currentIndexChanged.connect(self._language_picked)

        self.prof_label = QLabel()
        self.prof_label.setObjectName("Section")
        self.prof_list = QListWidget()
        self.prof_list.setMaximumHeight(160)
        row = QHBoxLayout()
        self.prof_edit = QLineEdit()
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self._add_profile)
        self.prof_edit.returnPressed.connect(self._add_profile)
        row.addWidget(self.prof_edit, 1)
        row.addWidget(self.add_btn)
        self.use_btn = QPushButton()
        self.use_btn.clicked.connect(self._use_profile)
        self.status = QLabel()
        self.status.setObjectName("Status")

        for w in (self.lang_label, self.lang_combo, self.lang_hint, self.prof_label,
                  self.prof_list):
            self.layout_.addWidget(w)
        self.layout_.addLayout(row)
        self.layout_.addWidget(self.use_btn, 0, Qt.AlignLeft)
        self.layout_.addWidget(self.status)

    def _language_picked(self, index):
        lang = self.lang_combo.itemData(index)
        if lang and lang != self.ctx.settings.language:
            self.ctx.settings.language = lang
            self.ctx.tr.set_language(lang)
            self._on_language_changed()

    def _refresh_profiles(self):
        t = self.ctx.tr.t
        active = self.ctx.settings.active_user_id
        self.prof_list.clear()
        for u in self.ctx.db.list_users():
            label = u["name"] + (f"  {t('settings.active_marker')}" if u["id"] == active else "")
            self.prof_list.addItem(label)
        # keep user ids in order for lookup
        self._ids = [u["id"] for u in self.ctx.db.list_users()]

    def _add_profile(self):
        t = self.ctx.tr.t
        name = self.prof_edit.text().strip()
        try:
            self.ctx.db.create_user(name)
        except ValueError as e:
            self.status.setText(t("settings.err_empty" if str(e) == "empty"
                                  else "settings.err_duplicate"))
            return
        self.prof_edit.clear()
        self.status.setText(t("settings.added", name=name))
        self._refresh_profiles()

    def _use_profile(self):
        row = self.prof_list.currentRow()
        if row < 0 or row >= len(self._ids):
            return
        self.ctx.settings.active_user_id = self._ids[row]
        self._on_language_changed()  # refreshes every page (dashboard shows the profile)
        user = self.ctx.db.get_user(self._ids[row])
        self.status.setText(self.ctx.tr.t("settings.switched", name=user["name"]))

    def retranslate(self):
        super().retranslate()
        t = self.ctx.tr.t
        self.lang_combo.blockSignals(True)
        self.lang_combo.setItemText(0, t("settings.english"))
        self.lang_combo.setItemText(1, t("settings.arabic"))
        self.lang_combo.setCurrentIndex(0 if self.ctx.settings.language == "en" else 1)
        self.lang_combo.blockSignals(False)
        self.lang_label.setText(t("settings.language_label"))
        self.lang_hint.setText(t("settings.language_hint"))
        self.prof_label.setText(t("settings.profiles"))
        self.prof_edit.setPlaceholderText(t("settings.new_profile"))
        self.add_btn.setText(t("settings.add_profile"))
        self.use_btn.setText(t("settings.use_profile"))
        self._refresh_profiles()

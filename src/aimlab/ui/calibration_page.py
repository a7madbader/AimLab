"""Mouse Calibration page (Phase 2).

Design: button handlers only start/stop recording. All result handling lives in the
apply_*() methods, which take a list of Samples, so they can be driven by tests.
"""
import html
import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QPushButton, QScrollArea,
                               QTabWidget, QVBoxLayout, QWidget)

from ..mouse import calculations as calc
from ..mouse.analysis import (analyze_acceleration, analyze_dpi, analyze_movement,
                              analyze_polling, swipe_from_samples)
from ..mouse.capture import create_capture
from ..mouse.pointer_settings import get_pointer_settings
from .pages import BasePage

log = logging.getLogger("aimlab.ui.calibration")

POLL_SECONDS = 5
SECTIONS = ("what", "why", "measures", "how", "results", "improve", "limits")
SWIPE_LABELS = ("slow", "medium", "fast")
GAMES = ("cs2", "valorant", "apex", "overwatch2", "cod")


def _label(object_name=None, wrap=True):
    lab = QLabel()
    lab.setWordWrap(wrap)
    if object_name:
        lab.setObjectName(object_name)
    return lab


def _spin(lo, hi, value, decimals=1, step=1.0):
    sp = QDoubleSpinBox()
    sp.setRange(lo, hi)
    sp.setDecimals(decimals)
    sp.setSingleStep(step)
    sp.setValue(value)
    return sp


class ExplainBox(QFrame):
    """The what / why / measures / how / results / improve / limits explanation of a tool."""

    def __init__(self, ctx, tool):
        super().__init__()
        self.ctx, self.tool = ctx, tool
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.RichText)
        lay.addWidget(self.text)

    def retranslate(self):
        t = self.ctx.tr.t
        parts = [f"<b>{html.escape(t('calib.explain_title'))}</b>"]
        for s in SECTIONS:
            parts.append(f"<p><b>{html.escape(t('calib.h.' + s))}:</b> "
                         f"{html.escape(t(f'calib.{self.tool}.{s}'))}</p>")
        self.text.setText("".join(parts))


class CalibrationPage(BasePage):
    add_stretch = False

    def __init__(self, ctx, on_profiles_changed=None, capture=None):
        super().__init__(ctx, "calibration")
        self._on_profiles_changed = on_profiles_changed or (lambda: None)
        self.capture = capture or create_capture()
        self._mode = None
        self._swipes = []
        self._last_hz = None
        self._last_dpi = None
        self._profile_ids = []
        self._poll_left = 0
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        # Space ends a recording. Active only while focus is inside this page.
        sc = QShortcut(QKeySequence(Qt.Key_Space), self)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(self._on_space)

    # ------------------------------------------------------------------ building
    def build(self):
        self.tabs = QTabWidget()
        self.explain = {}
        builders = [("settings", self._build_settings), ("polling", self._build_polling),
                    ("dpi", self._build_dpi), ("accel", self._build_accel),
                    ("smooth", self._build_smooth), ("calc", self._build_calc),
                    ("profiles", self._build_profiles)]
        self._tab_keys = [k for k, _ in builders]
        for key, fn in builders:
            body = QWidget()
            lay = QVBoxLayout(body)
            lay.setSpacing(10)
            fn(lay)
            if key != "profiles":
                self.explain[key] = ExplainBox(self.ctx, key)
                lay.addWidget(self.explain[key])
            lay.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(body)
            self.tabs.addTab(scroll, key)
        self.layout_.addWidget(self.tabs, 1)

    def _build_settings(self, lay):
        self.ps_status = _label("Status")
        self.ps_speed = _label()
        self.ps_speed_note = _label("PageDesc")
        self.ps_btn = QPushButton()
        self.ps_btn.clicked.connect(self.refresh_pointer_settings)
        for w in (self.ps_status, self.ps_speed, self.ps_speed_note):
            lay.addWidget(w)
        lay.addWidget(self.ps_btn, 0, Qt.AlignLeft)

    def _build_polling(self, lay):
        self.poll_info = _label("PageDesc")
        self.poll_btn = QPushButton()
        self.poll_btn.clicked.connect(self._polling_start)
        self.poll_result = _label("Section")
        self.poll_detail = _label("PageDesc")
        self.poll_save = QPushButton()
        self.poll_save.clicked.connect(self._save_hz)
        self.poll_save.setEnabled(False)
        self.poll_msg = _label("Status")
        for w in (self.poll_info,):
            lay.addWidget(w)
        lay.addWidget(self.poll_btn, 0, Qt.AlignLeft)
        for w in (self.poll_result, self.poll_detail):
            lay.addWidget(w)
        lay.addWidget(self.poll_save, 0, Qt.AlignLeft)
        lay.addWidget(self.poll_msg)

    def _build_dpi(self, lay):
        form = QFormLayout()
        self.dpi_dist_label = QLabel()
        self.dpi_dist = _spin(1, 200, 20.0)
        form.addRow(self.dpi_dist_label, self.dpi_dist)
        self.dpi_info = _label("PageDesc")
        self.dpi_btn = QPushButton()
        self.dpi_btn.clicked.connect(self._dpi_start)
        self.dpi_result = _label("Section")
        self.dpi_save = QPushButton()
        self.dpi_save.clicked.connect(self._save_dpi)
        self.dpi_save.setEnabled(False)
        self.dpi_msg = _label("Status")
        lay.addLayout(form)
        lay.addWidget(self.dpi_info)
        lay.addWidget(self.dpi_btn, 0, Qt.AlignLeft)
        lay.addWidget(self.dpi_result)
        lay.addWidget(self.dpi_save, 0, Qt.AlignLeft)
        lay.addWidget(self.dpi_msg)

    def _build_accel(self, lay):
        form = QFormLayout()
        self.acc_dist_label = QLabel()
        self.acc_dist = _spin(1, 200, 20.0)
        form.addRow(self.acc_dist_label, self.acc_dist)
        self.acc_info = _label("PageDesc")
        row = QHBoxLayout()
        self.acc_btn = QPushButton()
        self.acc_btn.clicked.connect(self._accel_start)
        self.acc_reset = QPushButton()
        self.acc_reset.clicked.connect(self._accel_reset)
        row.addWidget(self.acc_btn)
        row.addWidget(self.acc_reset)
        row.addStretch(1)
        self.acc_log = _label()
        self.acc_result = _label("Section")
        lay.addLayout(form)
        lay.addWidget(self.acc_info)
        lay.addLayout(row)
        lay.addWidget(self.acc_log)
        lay.addWidget(self.acc_result)

    def _build_smooth(self, lay):
        self.sm_info = _label("PageDesc")
        self.sm_btn = QPushButton()
        self.sm_btn.clicked.connect(self._smooth_start)
        self.sm_result = _label("Section")
        self.sm_label = _label("Status")
        lay.addWidget(self.sm_info)
        lay.addWidget(self.sm_btn, 0, Qt.AlignLeft)
        lay.addWidget(self.sm_result)
        lay.addWidget(self.sm_label)

    def _build_calc(self, lay):
        form = QFormLayout()
        self.c_dpi = _spin(50, 100000, 800, 0, 50)
        self.c_sens = _spin(0.0001, 1000, 1.0, 4, 0.05)
        self.c_game = QComboBox()
        for g in GAMES:
            self.c_game.addItem("", g)
        self.c_game.addItem("", "custom")
        self.c_yaw = _spin(0.00001, 10, calc.GAME_YAW["cs2"], 5, 0.001)
        self.c_pad = _spin(5, 200, 45, 1, 5)
        self.c_target = _spin(1, 500, 40, 1, 1)
        self.c_labels = {}
        for key, widget in (("calc_dpi", self.c_dpi), ("calc_sens", self.c_sens),
                            ("calc_game", self.c_game), ("calc_yaw", self.c_yaw),
                            ("calc_pad", self.c_pad), ("calc_target", self.c_target)):
            self.c_labels[key] = QLabel()
            form.addRow(self.c_labels[key], widget)
        self.c_edpi = _label("Section")
        self.c_cm = _label("Section")
        self.c_padres = _label()
        self.c_needed = _label()
        lay.addLayout(form)
        for w in (self.c_edpi, self.c_cm, self.c_padres, self.c_needed):
            lay.addWidget(w)
        for sp in (self.c_dpi, self.c_sens, self.c_yaw, self.c_pad, self.c_target):
            sp.valueChanged.connect(self._recalc)
        self.c_game.currentIndexChanged.connect(self._game_changed)

    def _build_profiles(self, lay):
        self.pr_list = QListWidget()
        self.pr_list.setMaximumHeight(170)
        form = QFormLayout()
        self.pr_name = QLineEdit()
        self.pr_dpi = _spin(50, 100000, 800, 0, 50)
        self.pr_hz = QLineEdit()
        self.pr_labels = {}
        for key, widget in (("prof_name", self.pr_name), ("prof_dpi", self.pr_dpi),
                            ("prof_hz", self.pr_hz)):
            self.pr_labels[key] = QLabel()
            form.addRow(self.pr_labels[key], widget)
        row = QHBoxLayout()
        self.pr_add = QPushButton()
        self.pr_add.clicked.connect(self._profile_add)
        self.pr_use = QPushButton()
        self.pr_use.clicked.connect(self._profile_use)
        self.pr_del = QPushButton()
        self.pr_del.clicked.connect(self._profile_delete)
        for b in (self.pr_add, self.pr_use, self.pr_del):
            row.addWidget(b)
        row.addStretch(1)
        self.pr_msg = _label("Status")
        lay.addWidget(self.pr_list)
        lay.addLayout(form)
        lay.addLayout(row)
        lay.addWidget(self.pr_msg)

    # ------------------------------------------------------------------ translation
    def retranslate(self):
        super().retranslate()
        t = self.ctx.tr.t
        for i, key in enumerate(self._tab_keys):
            self.tabs.setTabText(i, t(f"calib.tab.{key}"))
        for box in self.explain.values():
            box.retranslate()
        self.ps_btn.setText(t("calib.recheck"))
        if not self._mode:
            self.poll_info.setText(t("calib.poll_idle", sec=POLL_SECONDS))
            self.dpi_info.setText(t("calib.dpi_idle"))
            self.sm_info.setText(t("calib.sm_idle"))
        self.poll_btn.setText(t("calib.start"))
        self.poll_save.setText(t("calib.save_hz"))
        self.dpi_dist_label.setText(t("calib.dpi_distance"))
        self.dpi_btn.setText(t("calib.start"))
        self.dpi_save.setText(t("calib.save_dpi"))
        self.acc_dist_label.setText(t("calib.acc_distance"))
        self.acc_reset.setText(t("calib.reset"))
        self.sm_btn.setText(t("calib.record"))
        self._accel_refresh()
        for k, lab in self.c_labels.items():
            lab.setText(t(f"calib.{k}"))
        for i in range(self.c_game.count()):
            self.c_game.setItemText(i, t(f"calib.game_{self.c_game.itemData(i)}"))
        for k, lab in self.pr_labels.items():
            lab.setText(t(f"calib.{k}"))
        self.pr_add.setText(t("calib.prof_add"))
        self.pr_use.setText(t("calib.prof_use"))
        self.pr_del.setText(t("calib.prof_delete"))
        self.refresh_pointer_settings()
        self._refresh_profiles()
        self._recalc()

    # ------------------------------------------------------------------ recording engine
    def _begin(self, mode, msg_label):
        if self._mode:
            return False
        try:
            self.capture.start()
        except Exception as e:                      # CaptureError, OSError, ...
            log.warning("Capture start failed: %s", e)
            msg_label.setText(self.ctx.tr.t("calib.capture_error", error=str(e)))
            return False
        self._mode = mode
        self.setFocus()
        return True

    def _end(self):
        self._timer.stop()
        samples = self.capture.drain()
        self.capture.stop()
        self._mode = None
        return samples

    def _on_space(self):
        if self._mode == "dpi":
            self.apply_dpi(self._end())
        elif self._mode == "accel":
            self.apply_accel_swipe(self._end())
        elif self._mode == "smooth":
            self.apply_smooth(self._end())

    def _tick(self):
        if self._mode == "polling":
            self._poll_left -= 0.25
            if self._poll_left <= 0:
                self.apply_polling(self._end())
            else:
                self.poll_info.setText(self.ctx.tr.t("calib.poll_running", left=f"{self._poll_left:.0f}"))

    def _save_result(self, kind, data):
        uid = self.ctx.settings.active_user_id
        self.ctx.db.add_calibration_result(uid, kind, data, self.ctx.settings.active_mouse_profile_id)

    # ------------------------------------------------------------------ pointer settings
    def refresh_pointer_settings(self):
        t = self.ctx.tr.t
        ps = get_pointer_settings()
        if ps is None:
            self.ps_status.setText(t("calib.windows_only"))
            self.ps_speed.setText(t("calib.pointer_unavailable"))
            self.ps_speed_note.setText("")
            return
        self.ps_status.setText(t("calib.pointer_on" if ps.enhance_precision else "calib.pointer_off"))
        self.ps_speed.setText(t("calib.pointer_speed", speed=ps.speed))
        self.ps_speed_note.setText(t("calib.speed_ok" if ps.speed == 10 else "calib.speed_warn"))

    # ------------------------------------------------------------------ polling
    def _polling_start(self):
        if not self._begin("polling", self.poll_msg):
            return
        self.poll_msg.setText("")
        self._poll_left = float(POLL_SECONDS)
        self.poll_info.setText(self.ctx.tr.t("calib.poll_running", left=POLL_SECONDS))
        self._timer.start()

    def apply_polling(self, samples):
        t = self.ctx.tr.t
        r = analyze_polling(samples)
        self.poll_info.setText(t("calib.poll_idle", sec=POLL_SECONDS))
        if not r.ok:
            self.poll_result.setText("")
            self.poll_detail.setText(t("calib.poll_insufficient", n=r.n_intervals))
            self.poll_save.setEnabled(False)
            return r
        self._last_hz = r.hz
        self.poll_result.setText(t("calib.poll_result", hz=f"{r.hz:.0f}", common=r.nearest_common_hz))
        self.poll_detail.setText(t("calib.poll_detail", median=f"{r.median_ms:.2f}", p95=f"{r.p95_ms:.2f}",
                                   jitter=f"{r.jitter_ms:.2f}", n=r.n_intervals))
        self.poll_save.setEnabled(True)
        self._save_result("polling", {"hz": round(r.hz, 1), "nearest_common_hz": r.nearest_common_hz,
                                      "median_ms": round(r.median_ms, 3), "jitter_ms": round(r.jitter_ms, 3),
                                      "intervals": r.n_intervals})
        self.poll_msg.setText(t("calib.saved_history"))
        return r

    def _save_hz(self):
        self._save_to_profile(self.poll_msg, polling_hz=round(self._last_hz))

    # ------------------------------------------------------------------ DPI
    def _dpi_start(self):
        if not self._begin("dpi", self.dpi_msg):
            return
        self.dpi_msg.setText("")
        self.dpi_info.setText(self.ctx.tr.t("calib.dpi_running", cm=f"{self.dpi_dist.value():g}"))

    def apply_dpi(self, samples):
        t = self.ctx.tr.t
        self.dpi_info.setText(t("calib.dpi_idle"))
        r = analyze_dpi(samples, self.dpi_dist.value())
        if not r.ok:
            self.dpi_result.setText(t("calib.dpi_too_few"))
            self.dpi_save.setEnabled(False)
            return r
        self._last_dpi = r.dpi
        self.dpi_result.setText(t("calib.dpi_result", dpi=f"{r.dpi:.0f}", common=r.nearest_common,
                                  counts=f"{r.counts:.0f}"))
        self.dpi_save.setEnabled(True)
        self._save_result("dpi", {"dpi": round(r.dpi, 1), "counts": round(r.counts),
                                  "distance_cm": r.distance_cm, "nearest_common": r.nearest_common})
        self.dpi_msg.setText(t("calib.saved_history"))
        return r

    def _save_dpi(self):
        self._save_to_profile(self.dpi_msg, dpi=round(self._last_dpi, 1))

    def _save_to_profile(self, msg_label, **fields):
        t = self.ctx.tr.t
        pid = self.ctx.settings.active_mouse_profile_id
        if not pid:
            msg_label.setText(t("calib.need_profile"))
            return
        self.ctx.db.update_mouse_profile(pid, **fields)
        msg_label.setText(t("calib.saved_profile"))
        self._refresh_profiles()
        self._on_profiles_changed()

    # ------------------------------------------------------------------ acceleration
    def _accel_label(self, i):
        return self.ctx.tr.t(f"calib.acc_{SWIPE_LABELS[i]}")

    def _accel_refresh(self):
        t = self.ctx.tr.t
        self.acc_info.setText(t("calib.acc_prompt", n=len(self._swipes) + 1,
                                label=self._accel_label(min(len(self._swipes), 2))))
        self.acc_btn.setText(t("calib.record"))

    def _accel_start(self):
        if len(self._swipes) >= 3:
            self._accel_reset()
        n = len(self._swipes)
        if not self._begin("accel", self.acc_result):
            return
        self.acc_result.setText("")
        self.acc_info.setText(self.ctx.tr.t("calib.acc_running", n=n + 1,
                                            cm=f"{self.acc_dist.value():g}", label=self._accel_label(n)))

    def _accel_reset(self):
        self._swipes = []
        self.acc_log.setText("")
        self.acc_result.setText("")
        self._accel_refresh()

    def apply_accel_swipe(self, samples):
        t = self.ctx.tr.t
        n = len(self._swipes)
        sw = swipe_from_samples(SWIPE_LABELS[min(n, 2)], samples)
        if sw.counts < 50 or sw.duration_s <= 0:
            self.acc_result.setText(t("calib.acc_too_few"))
            self._accel_refresh()
            return None
        self._swipes.append(sw)
        prev = self.acc_log.text()
        line = t("calib.acc_progress", n=n + 1, counts=f"{sw.counts:.0f}", dur=f"{sw.duration_s:.2f}")
        self.acc_log.setText((prev + "\n" if prev else "") + line)
        result = None
        if len(self._swipes) >= 3:
            result = analyze_acceleration(self._swipes)
            key = f"calib.acc_{result.status}"
            self.acc_result.setText(t(key, pct=f"{result.deviation_pct:+.1f}", ratio=f"{result.speed_ratio:.1f}"))
            self._save_result("acceleration", {
                "status": result.status, "deviation_pct": round(result.deviation_pct, 2),
                "speed_ratio": round(result.speed_ratio, 2), "distance_cm": self.acc_dist.value(),
                "swipes": [{"label": s.label, "counts": round(s.counts), "duration_s": round(s.duration_s, 3)}
                           for s in self._swipes]})
        self._accel_refresh()
        return result

    # ------------------------------------------------------------------ smoothness
    def _smooth_start(self):
        if not self._begin("smooth", self.sm_label):
            return
        self.sm_label.setText("")
        self.sm_info.setText(self.ctx.tr.t("calib.sm_running"))

    def apply_smooth(self, samples):
        t = self.ctx.tr.t
        self.sm_info.setText(t("calib.sm_idle"))
        m = analyze_movement(samples)
        if not m.ok:
            self.sm_result.setText(t("calib.sm_insufficient"))
            self.sm_label.setText("")
            return m
        self.sm_result.setText(t("calib.sm_result", length=f"{m.path_length:.0f}",
                                 straight=f"{m.straightness_pct:.1f}", wobble=f"{m.wobble_pct:.1f}",
                                 cv=f"{m.speed_cv_pct:.0f}", dur=f"{m.duration_s:.2f}"))
        key = "sm_very_steady" if m.wobble_pct < 1.5 else "sm_steady" if m.wobble_pct < 4 else "sm_uneven"
        self.sm_label.setText(t(f"calib.{key}"))
        self._save_result("smoothness", {"path_length": round(m.path_length), "straightness_pct": round(m.straightness_pct, 2),
                                         "wobble_pct": round(m.wobble_pct, 2), "speed_cv_pct": round(m.speed_cv_pct, 1),
                                         "duration_s": round(m.duration_s, 3)})
        return m

    # ------------------------------------------------------------------ calculator
    def _game_changed(self):
        game = self.c_game.currentData()
        custom = game == "custom"
        self.c_yaw.setEnabled(custom)
        if not custom:
            self.c_yaw.blockSignals(True)
            self.c_yaw.setValue(calc.GAME_YAW[game])
            self.c_yaw.blockSignals(False)
        self._recalc()

    def _recalc(self):
        t = self.ctx.tr.t
        dpi, sens, yaw = self.c_dpi.value(), self.c_sens.value(), self.c_yaw.value()
        cm = calc.cm_per_360(dpi, sens, yaw)
        self.c_edpi.setText(t("calib.calc_edpi", edpi=f"{calc.edpi(dpi, sens):g}"))
        self.c_cm.setText(t("calib.calc_cm", cm=f"{cm:.2f}", inch=f"{cm / calc.CM_PER_INCH:.2f}"))
        self.c_padres.setText(t("calib.calc_padres", width=f"{self.c_pad.value():g}",
                                deg=f"{calc.degrees_on_pad(self.c_pad.value(), cm):.0f}"))
        self.c_needed.setText(t("calib.calc_needed", cm=f"{self.c_target.value():g}",
                                sens=f"{calc.sensitivity_for_cm360(dpi, self.c_target.value(), yaw):.4f}"))

    # ------------------------------------------------------------------ mouse profiles
    def _refresh_profiles(self):
        t = self.ctx.tr.t
        uid = self.ctx.settings.active_user_id
        active = self.ctx.settings.active_mouse_profile_id
        profiles = self.ctx.db.list_mouse_profiles(uid)
        self._profile_ids = [p["id"] for p in profiles]
        self.pr_list.clear()
        for p in profiles:
            hz = f" - {p['polling_hz']:g} Hz" if p["polling_hz"] else ""
            text = t("calib.prof_item", name=p["name"], dpi=f"{p['dpi']:g}", hz=hz)
            if p["id"] == active:
                text += f"  {t('calib.prof_active')}"
            self.pr_list.addItem(text)

    def _profile_add(self):
        t = self.ctx.tr.t
        hz_text = self.pr_hz.text().strip()
        try:
            hz = float(hz_text) if hz_text else None
            uid = self.ctx.settings.active_user_id
            pid = self.ctx.db.create_mouse_profile(uid, self.pr_name.text(), self.pr_dpi.value(), hz)
        except ValueError as e:
            key = {"empty": "err_empty", "duplicate": "err_duplicate", "dpi": "err_dpi"}.get(str(e), "err_polling")
            self.pr_msg.setText(t(f"calib.{key}"))
            return
        name = self.pr_name.text().strip()
        self.ctx.settings.active_mouse_profile_id = pid
        self.pr_name.clear()
        self.pr_hz.clear()
        self.c_dpi.setValue(self.ctx.db.get_mouse_profile(pid)["dpi"])
        self.pr_msg.setText(t("calib.prof_added", name=name))
        self._refresh_profiles()
        self._on_profiles_changed()

    def _selected_profile(self):
        row = self.pr_list.currentRow()
        return self._profile_ids[row] if 0 <= row < len(self._profile_ids) else None

    def _profile_use(self):
        pid = self._selected_profile()
        if pid is None:
            return
        self.ctx.settings.active_mouse_profile_id = pid
        prof = self.ctx.db.get_mouse_profile(pid)
        self.c_dpi.setValue(prof["dpi"])
        self.pr_msg.setText(self.ctx.tr.t("calib.prof_switched", name=prof["name"]))
        self._refresh_profiles()
        self._on_profiles_changed()

    def _profile_delete(self):
        pid = self._selected_profile()
        if pid is None:
            return
        self.ctx.db.delete_mouse_profile(pid)
        self.pr_msg.setText(self.ctx.tr.t("calib.prof_deleted"))
        self._refresh_profiles()
        self._on_profiles_changed()

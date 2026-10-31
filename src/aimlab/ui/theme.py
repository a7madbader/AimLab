"""Dark gaming theme (Qt style sheet)."""

ACCENT = "#00e5a8"
BG = "#0d1117"
PANEL = "#141a23"
PANEL_2 = "#1b2330"
TEXT = "#e6edf3"
MUTED = "#8b98a9"


def stylesheet() -> str:
    return f"""
    * {{ font-family: "Segoe UI", "Tahoma", sans-serif; font-size: 14px; color: {TEXT}; }}
    QMainWindow, QWidget#Content {{ background: {BG}; }}
    QFrame#Sidebar {{ background: {PANEL}; border: none; }}
    QLabel#Brand {{ font-size: 22px; font-weight: 700; color: {ACCENT}; padding: 18px 16px 2px 16px; }}
    QLabel#Tagline {{ color: {MUTED}; font-size: 11px; padding: 0 16px 14px 16px; }}
    QListWidget#Nav {{ background: transparent; border: none; outline: none; }}
    QListWidget#Nav::item {{ padding: 12px 16px; margin: 2px 8px; border-radius: 8px; }}
    QListWidget#Nav::item:hover {{ background: {PANEL_2}; }}
    QListWidget#Nav::item:selected {{ background: {ACCENT}; color: #04120d; font-weight: 600; }}
    QLabel#PageTitle {{ font-size: 26px; font-weight: 700; }}
    QLabel#PageDesc {{ color: {MUTED}; font-size: 14px; }}
    QLabel#Planned {{ color: {ACCENT}; background: {PANEL}; border: 1px dashed {ACCENT};
                      border-radius: 10px; padding: 18px; }}
    QFrame#Card {{ background: {PANEL}; border-radius: 12px; }}
    QLabel#CardTitle {{ color: {MUTED}; font-size: 12px; }}
    QLabel#CardValue {{ font-size: 18px; font-weight: 600; }}
    QLabel#Section {{ font-size: 16px; font-weight: 600; padding-top: 8px; }}
    QLabel#Status {{ color: {ACCENT}; }}
    QComboBox, QLineEdit, QListWidget {{ background: {PANEL}; border: 1px solid {PANEL_2};
                                         border-radius: 8px; padding: 8px; }}
    QPushButton {{ background: {ACCENT}; color: #04120d; border: none; border-radius: 8px;
                   padding: 9px 18px; font-weight: 600; }}
    QPushButton:hover {{ background: #33f0bf; }}
    """

"""Where the application keeps its files. Override with AIMLAB_DATA_DIR (used by tests)."""
import os
import sys
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("AIMLAB_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "AimLabPro"
    else:
        base = Path.home() / ".aimlabpro"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "aimlab.db"


def log_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def asset_path(name: str) -> Path:
    """Locate a bundled asset both in source checkouts and in the PyInstaller build."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "assets" / name
    return Path(__file__).resolve().parents[3] / "assets" / name

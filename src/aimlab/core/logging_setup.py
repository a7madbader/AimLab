import logging
import sys
from logging.handlers import RotatingFileHandler

from . import paths

_configured = False


def setup_logging(level=logging.INFO) -> logging.Logger:
    """Log to a rotating file and install a hook so crashes are recorded."""
    global _configured
    root = logging.getLogger("aimlab")
    if _configured:
        return root
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = RotatingFileHandler(paths.log_dir() / "aimlab.log", maxBytes=1_000_000,
                             backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    def _hook(exc_type, exc, tb):
        root.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook
    _configured = True
    return root

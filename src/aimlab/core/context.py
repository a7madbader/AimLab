from dataclasses import dataclass

from .database import Database
from .settings import Settings
from ..localization.i18n import Translator


@dataclass
class AppContext:
    db: Database
    settings: Settings
    tr: Translator

"""Tiny JSON-based translator with English fallback and RTL awareness."""
import json
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent / "locales"
RTL_LANGUAGES = {"ar"}


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def load_locale(lang: str) -> dict:
    with open(LOCALE_DIR / f"{lang}.json", encoding="utf-8") as f:
        return _flatten(json.load(f))


class Translator:
    def __init__(self, lang="en"):
        self._fallback = load_locale("en")
        self.lang = "en"
        self._strings = self._fallback
        self.set_language(lang)

    def set_language(self, lang: str):
        self._strings = load_locale(lang)
        self.lang = lang

    @property
    def is_rtl(self) -> bool:
        return self.lang in RTL_LANGUAGES

    def t(self, key: str, **kwargs) -> str:
        text = self._strings.get(key) or self._fallback.get(key) or key
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError):
            return text

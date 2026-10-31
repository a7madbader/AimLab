import re
import unittest

from aimlab.localization.i18n import Translator, load_locale

PH = re.compile(r"\{(\w+)\}")


class I18nTests(unittest.TestCase):
    def test_same_keys_in_both_languages(self):
        en, ar = load_locale("en"), load_locale("ar")
        self.assertEqual(set(en), set(ar), "English and Arabic keys differ")

    def test_no_empty_strings_and_placeholders_match(self):
        en, ar = load_locale("en"), load_locale("ar")
        for k in en:
            self.assertTrue(en[k].strip(), f"empty en: {k}")
            self.assertTrue(ar[k].strip(), f"empty ar: {k}")
            self.assertEqual(set(PH.findall(en[k])), set(PH.findall(ar[k])), f"placeholders: {k}")

    def test_all_ten_nav_pages_have_title_and_description(self):
        en = load_locale("en")
        pages = [k.split(".")[1] for k in en if k.startswith("nav.")]
        self.assertEqual(len(pages), 10)
        for p in pages:
            self.assertIn(f"pages.{p}.desc", en)

    def test_switching_and_rtl(self):
        tr = Translator("en")
        self.assertFalse(tr.is_rtl)
        self.assertEqual(tr.t("nav.settings"), "Settings")
        tr.set_language("ar")
        self.assertTrue(tr.is_rtl)
        self.assertEqual(tr.t("nav.settings"), "الإعدادات")

    def test_formatting_and_fallback(self):
        tr = Translator("ar")
        self.assertIn("أحمد", tr.t("dashboard.welcome", name="أحمد"))
        self.assertEqual(tr.t("missing.key"), "missing.key")


if __name__ == "__main__":
    unittest.main()


class CalibrationTextTests(unittest.TestCase):
    def test_every_tool_has_all_educational_sections_in_both_languages(self):
        sections = ("what", "why", "measures", "how", "results", "improve", "limits")
        for lang in ("en", "ar"):
            strings = load_locale(lang)
            for tool in ("settings", "polling", "dpi", "accel", "smooth", "calc"):
                for s in sections:
                    self.assertTrue(strings.get(f"calib.{tool}.{s}", "").strip(), f"{lang} calib.{tool}.{s}")
            for s in sections:
                self.assertIn(f"calib.h.{s}", strings)

    def test_arabic_text_is_actually_arabic(self):
        ar = load_locale("ar")
        for key in ("calib.polling.what", "calib.dpi.how", "calib.accel.limits", "nav.calibration"):
            self.assertTrue(any("\u0600" <= ch <= "\u06FF" for ch in ar[key]), key)

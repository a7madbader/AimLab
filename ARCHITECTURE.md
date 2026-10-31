# Architecture
src/aimlab/
- core/            paths, logging, SQLite database (users, settings, backup/restore), settings, AppContext
- localization/    JSON locale files (en, ar), Translator (fallback to English, RTL flag)
- ui/              Qt only: theme, pages, main window. No business logic here.
- mouse/           (Phase 2) Raw Input capture, DPI, polling rate, acceleration
- testing_engine/  (Phase 3) aim tests
- analytics/       (Phase 4) statistics
- ai/              (Phase 5) recommendation engine
- games/           (Phase 6) game conversion
- reports/         (Phase 8) PDF/CSV
packaging/         PyInstaller spec, Inno Setup script
tests/             unittest suites (pure logic runs anywhere; UI smoke test needs PySide6)

Design rules: logic modules must not import Qt, so they can be tested without a display.
All user-visible text goes through Translator keys (en.json and ar.json must stay in sync; a test enforces it).
Data lives in %APPDATA%\AimLabPro (database, logs).

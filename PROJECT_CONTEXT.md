# Project context
- Goal: professional Windows desktop app "AIMLAB PRO" (see original master prompt for the full feature list, 9 phases).
- Owner is not a programmer: never require terminal use; deliver installer + source.
- Stack: Python 3.12, PySide6 (Qt 6) UI, SQLite, PyInstaller + Inno Setup; Raw Input via ctypes (Phase 2).
- Dev sandbox is Linux with no network and no Windows: Windows builds happen on GitHub Actions (windows-latest).
- Rules: phased development; never claim a feature works unless tested; label results as "tested here" or "tested by CI/Windows".
- Continue the existing project; do not recreate it.

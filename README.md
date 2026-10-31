# AIMLAB PRO
Mouse sensitivity analysis, aim performance evaluation and calibration for FPS gamers. Windows desktop app (Python + PySide6).

**Status:** Phase 1 (Foundation) written. See DEVELOPMENT_STATUS.md for what is verified.

## For the end user
See HOW_TO_GET_THE_WINDOWS_APP.md.

## For developers
    pip install -r requirements-build.txt
    python -m unittest discover -s tests -t .      # run tests
    python -m aimlab                               # run from source (needs PySide6)
    pyinstaller packaging/AimLabPro.spec           # build exe (on Windows)

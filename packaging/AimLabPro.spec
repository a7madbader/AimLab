# PyInstaller recipe: builds dist/AimLabPro/AimLabPro.exe (windowed, no console)
import os
root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(root, "run_aimlab.py")],
    pathex=[os.path.join(root, "src")],
    datas=[
        (os.path.join(root, "src", "aimlab", "localization", "locales"),
         os.path.join("aimlab", "localization", "locales")),
        (os.path.join(root, "assets"), "assets"),
    ],
    hiddenimports=[],
    excludes=["tkinter", "unittest.mock"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AimLabPro",
          console=False, icon=os.path.join(root, "assets", "aimlab.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="AimLabPro")

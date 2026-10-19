# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the portable PhonePad.exe.

Bundles:
  * the FastAPI/uvicorn server (backend package)
  * the built React app (backend/static)
  * vgamepad plus its ViGEmClient DLLs and the ViGEmBus installer MSI
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

vg_datas, vg_binaries, vg_hidden = collect_all("vgamepad")

hiddenimports = list(vg_hidden)
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("websockets")

datas = vg_datas + [("backend/static", "backend/static")]


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=vg_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PhonePad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/PhonePad.ico",
)

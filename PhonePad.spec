# -*- mode: python ; coding: utf-8 -*-
"""Windowed, self-contained PhonePad desktop application."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
package_data = []
package_binaries = []
hidden_imports = []
for package in ("webview", "fastapi", "uvicorn", "websockets", "qrcode"):
    data, binaries, hidden = collect_all(package)
    package_data += data
    package_binaries += binaries
    hidden_imports += hidden

frontend = root / "frontend"
a = Analysis(
    [str(root / "app.py")],
    pathex=[str(root)],
    binaries=package_binaries,
    datas=package_data + [(str(frontend), "frontend")],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["unittest"],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

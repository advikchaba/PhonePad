# -*- mode: python ; coding: utf-8 -*-
"""Windowed, self-contained PhonePad desktop UI prototype."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

webview_datas, webview_binaries, webview_hidden = collect_all("webview")
root = Path(SPECPATH)
frontend = root / "frontend"

a = Analysis(
    [str(root / "app.py")],
    pathex=[str(root)],
    binaries=webview_binaries,
    datas=webview_datas + [(str(frontend), "frontend")],
    hiddenimports=webview_hidden,
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

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata
import platform

datas = copy_metadata("readchar")
if platform.system() == "Windows":
    name = "BHYG-Windows"
elif platform.system() == "Linux":
    name = "BHYG-Linux"
elif platform.system() == "macOS":
    print(platform.machine())
    if "64" in platform.machine():
        name = "BHYG-macOS-Intel"
    elif "ARM" in platform.machine():
        name = "BHYG-macOS-Apple_Silicon"
    else:
        name = "BHYG-macOS"
else:
    name = "BHYG"

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

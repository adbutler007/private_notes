# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Collect dependencies for critical packages
datas = []
binaries = []
hiddenimports = [
    "audio_summary_app.engine.server",
    "audio_summary_app.engine",
    "uvicorn",
    "fastapi",
    "mlx",
    "mlx_whisper",
    "numpy",
]

# Collect all package metadata/data
for pkg in ['uvicorn', 'fastapi', 'mlx_whisper', 'parakeet_mlx']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['src/audio_summary_app/engine/server.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='audio-summary-engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='audio-summary-engine',
)


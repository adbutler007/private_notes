# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('qt.conf', '.'), ('download_parakeet.py', '.')]
binaries = []
hiddenimports = ['audio_summary_app', 'audio_summary_app.gui', 'audio_summary_app.gui.app', 'audio_summary_app.gui.meeting_browser', 'audio_summary_app.gui.settings_window', 'audio_summary_app.gui.first_run_wizard', 'audio_summary_app.gui.recording_controller', 'mlx', 'mlx_whisper', 'parakeet_mlx', 'scipy', 'scipy.signal']
datas += copy_metadata('PyQt6')
tmp_ret = collect_all('mlx_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('parakeet_mlx')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('mlx')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['launch_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_qt6.py'],
    excludes=['matplotlib', 'IPython', 'jupyter', 'torch', 'tensorflow'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Audio Summary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Audio Summary',
)
app = BUNDLE(
    coll,
    name='Audio Summary.app',
    icon='assets/icon.icns',
    bundle_identifier='com.audiosummary.app',
)

"""
setup.py for py2app bundling
Creates a standalone .app for macOS
"""

from setuptools import setup

APP = ['src/audio_summary_app/gui/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',  # We'll create this
    'plist': {
        'CFBundleName': 'Private Notes',
        'CFBundleDisplayName': 'Private Notes',
        'CFBundleIdentifier': 'com.privatenotes.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSMinimumSystemVersion': '11.0',  # macOS Big Sur
        'LSUIElement': True,  # This makes it a menu bar app (no dock icon)
        'NSMicrophoneUsageDescription': 'Private Notes needs microphone access to record and transcribe meetings.',
        'NSAppleEventsUsageDescription': 'Private Notes may interact with other apps.',
    },
    'packages': [
        'audio_summary_app',
        'PyQt6',
        'numpy',
        'sounddevice',
        'mlx_whisper',
        'ollama',
        'pydantic',
        'psutil',
    ],
    'includes': [
        'audio_summary_app.gui',
        'audio_summary_app.gui.app',
        'audio_summary_app.gui.meeting_browser',
        'audio_summary_app.gui.settings_window',
        'audio_summary_app.gui.first_run_wizard',
        'audio_summary_app.gui.recording_controller',
    ],
    'excludes': [
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
    ],
}

setup(
    name='PrivateNotes',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

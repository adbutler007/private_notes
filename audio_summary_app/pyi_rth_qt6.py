"""
PyInstaller runtime hook for Qt6
Sets Qt library paths to fix bundle resolution issues
"""
import sys
import os
from pathlib import Path

# Get the bundle directory
if getattr(sys, 'frozen', False):
    bundle_dir = Path(sys._MEIPASS)

    # Set Qt plugin path
    os.environ['QT_PLUGIN_PATH'] = str(bundle_dir / 'PyQt6' / 'Qt6' / 'plugins')

    # Set Qt library path
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(bundle_dir / 'PyQt6' / 'Qt6' / 'plugins' / 'platforms')

    # Disable Qt library path resolution
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

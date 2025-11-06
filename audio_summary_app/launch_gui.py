#!/usr/bin/env python3
"""
Launcher script for Private Notes GUI
This is the entry point for the py2app bundle
"""

import sys
import os
import multiprocessing
from pathlib import Path

# Add the src directory to the path so we can import audio_summary_app
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    # Enable multiprocessing support for frozen apps
    multiprocessing.freeze_support()

    # Check if this is a multiprocessing worker process
    # PyInstaller workers will have special command line arguments
    is_worker = any('multiprocessing' in arg.lower() for arg in sys.argv)

    # Only run GUI if not a worker process
    if not is_worker:
        # Now import and run the GUI
        from audio_summary_app.gui.app import AudioSummaryApp

        app = AudioSummaryApp()
        sys.exit(app.run())

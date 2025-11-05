#!/usr/bin/env python3
"""
Launcher script for Private Notes GUI
This is the entry point for the py2app bundle
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import audio_summary_app
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Now import and run the GUI
from audio_summary_app.gui.app import AudioSummaryApp

if __name__ == "__main__":
    app = AudioSummaryApp()
    sys.exit(app.run())

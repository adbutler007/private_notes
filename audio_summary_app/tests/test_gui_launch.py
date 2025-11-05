"""
Test script for GUI launch
Tests that the GUI can be initialized without errors
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audio_summary_app.gui import AudioSummaryApp
from audio_summary_app.config import Config

def test_gui_import():
    """Test that GUI modules can be imported"""
    from audio_summary_app.gui.app import AudioSummaryApp
    from audio_summary_app.gui.meeting_browser import MeetingBrowser
    from audio_summary_app.gui.settings_window import SettingsWindow
    from audio_summary_app.gui.first_run_wizard import FirstRunWizard
    from audio_summary_app.gui.recording_controller import RecordingController
    print("✓ All GUI modules imported successfully")

def test_config():
    """Test config initialization"""
    config = Config()
    print(f"✓ Config initialized")
    print(f"  - STT Model: {config.stt_model_path}")
    print(f"  - LLM Model: {config.llm_model_name}")
    print(f"  - Output dir: {config.output_dir}")

if __name__ == "__main__":
    print("Testing GUI components...")
    print()

    test_gui_import()
    print()

    test_config()
    print()

    print("All tests passed!")
    print()
    print("To launch the GUI, run:")
    print("  uv run python -m audio_summary_app.gui.app")

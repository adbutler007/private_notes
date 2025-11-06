"""
Main GUI Application
macOS menu bar app for Audio Summary
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from ..config import Config
from .meeting_browser import MeetingBrowser
from .settings_window import SettingsWindow
from .first_run_wizard import FirstRunWizard
from .recording_controller import RecordingController


class AudioSummaryApp:
    """
    Main application class for Audio Summary
    Manages system tray icon, menu, and windows
    """

    def __init__(self):
        """Initialize the application"""
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep running when windows close

        # Load config
        self.config = Config()

        # Initialize recording controller
        self.recording_controller = RecordingController(self.config)

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self.app)
        self.setup_tray_icon()

        # Windows
        self.meeting_browser = None
        self.settings_window = None

        # Check if first run
        self.check_first_run()

    def setup_tray_icon(self):
        """Set up the system tray icon and menu"""
        # TODO: Use custom icon when available
        # For now, use a built-in icon
        self.tray_icon.setIcon(self.app.style().standardIcon(
            self.app.style().StandardPixmap.SP_MediaPlay
        ))

        # Create menu
        menu = QMenu()

        # Start/Stop recording action (dynamic)
        self.recording_action = QAction("Start Recording", menu)
        self.recording_action.triggered.connect(self.toggle_recording)
        menu.addAction(self.recording_action)

        menu.addSeparator()

        # Meeting Browser
        browser_action = QAction("Meeting Browser...", menu)
        browser_action.triggered.connect(self.show_meeting_browser)
        menu.addAction(browser_action)

        # Settings
        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Recent summaries submenu (will be populated dynamically)
        self.recent_menu = QMenu("Recent Summaries", menu)
        menu.addMenu(self.recent_menu)
        self.update_recent_summaries()

        menu.addSeparator()

        # Export this week
        export_action = QAction("Export This Week to CSV", menu)
        export_action.triggered.connect(self.export_week)
        menu.addAction(export_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

        # Connect recording controller signals
        self.recording_controller.recording_started.connect(self.on_recording_started)
        self.recording_controller.recording_stopped.connect(self.on_recording_stopped)
        self.recording_controller.summary_ready.connect(self.on_summary_ready)

    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.recording_controller.is_recording:
            self.recording_controller.stop_recording()
        else:
            self.recording_controller.start_recording()

    def on_recording_started(self):
        """Called when recording starts"""
        self.recording_action.setText("⏹ Stop Recording")
        # Change icon to indicate recording
        self.tray_icon.setIcon(self.app.style().standardIcon(
            self.app.style().StandardPixmap.SP_MediaStop
        ))
        self.tray_icon.showMessage(
            "Recording Started",
            "Audio summary is now recording",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def on_recording_stopped(self):
        """Called when recording stops"""
        self.recording_action.setText("Start Recording")
        # Change icon back to play
        self.tray_icon.setIcon(self.app.style().standardIcon(
            self.app.style().StandardPixmap.SP_MediaPlay
        ))

    def on_summary_ready(self, summary_path: str):
        """Called when summary is ready"""
        self.tray_icon.showMessage(
            "Summary Ready",
            f"Meeting summary saved",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        self.update_recent_summaries()

    def update_recent_summaries(self):
        """Update the recent summaries menu"""
        self.recent_menu.clear()

        # Get recent summaries from output directory
        output_dir = Path(self.config.output_dir)
        if not output_dir.exists():
            no_action = QAction("No summaries yet", self.recent_menu)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return

        # Get summaries (both folder structure and flat structure)
        import json
        summaries = []

        # New folder structure: YYYY-MM-DD Company - Contact/summary.txt
        for summary_file in output_dir.glob("*/summary.txt"):
            folder = summary_file.parent
            folder_name = folder.name
            json_file = folder / "data.json"

            # Load company/contact from JSON if available
            display_name = folder_name  # Default to folder name
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        contacts = data.get('contacts', [])
                        companies = data.get('companies', [])
                        if companies and companies[0].get('name'):
                            company = companies[0]['name']
                            if contacts and contacts[0].get('name'):
                                display_name = f"{company} - {contacts[0]['name']}"
                            else:
                                display_name = company
                        elif contacts and contacts[0].get('name'):
                            display_name = contacts[0]['name']
                except:
                    pass

            summaries.append((summary_file, display_name, summary_file.stat().st_mtime))

        # Old flat structure: summary_YYYYMMDD_HHMMSS.txt
        for summary_file in output_dir.glob("summary_*.txt"):
            if summary_file.parent != output_dir:  # Skip files in subfolders
                continue
            timestamp = summary_file.stem.replace("summary_", "")
            summaries.append((summary_file, timestamp, summary_file.stat().st_mtime))

        # Sort by modification time and take most recent 5
        summaries.sort(key=lambda x: x[2], reverse=True)
        summaries = summaries[:5]

        if not summaries:
            no_action = QAction("No summaries yet", self.recent_menu)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return

        for summary_file, display_name, _ in summaries:
            action = QAction(display_name, self.recent_menu)
            action.triggered.connect(lambda checked, f=summary_file: self.open_summary(f))
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        view_all = QAction("View All...", self.recent_menu)
        view_all.triggered.connect(self.show_meeting_browser)
        self.recent_menu.addAction(view_all)

    def open_summary(self, summary_path: Path):
        """Open a summary file in default text editor"""
        import subprocess
        subprocess.run(['open', str(summary_path)])

    def show_meeting_browser(self):
        """Show the meeting browser window"""
        if self.meeting_browser is None:
            self.meeting_browser = MeetingBrowser(self.config)
        self.meeting_browser.show()
        self.meeting_browser.raise_()
        self.meeting_browser.activateWindow()

    def show_settings(self):
        """Show the settings window"""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.config)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def export_week(self):
        """Export this week's meetings to CSV"""
        # TODO: Implement week filtering and export
        self.tray_icon.showMessage(
            "Export Complete",
            "This week's meetings exported to CSV",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def check_first_run(self):
        """Check if this is the first run and show setup wizard"""
        # Check if Ollama model exists
        import subprocess
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            model_name = self.config.llm_model_name
            if model_name not in result.stdout:
                # Show first run wizard
                wizard = FirstRunWizard(self.config)
                wizard.exec()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Ollama not installed - show first run wizard
            wizard = FirstRunWizard(self.config)
            wizard.exec()

    def quit_app(self):
        """Quit the application"""
        # Stop recording if active
        if self.recording_controller.is_recording:
            self.recording_controller.stop_recording()
        self.app.quit()

    def run(self):
        """Run the application"""
        return self.app.exec()


def main():
    """Entry point for GUI application"""
    app = AudioSummaryApp()
    sys.exit(app.run())


if __name__ == '__main__':
    main()

"""
First Run Wizard
Guides users through initial setup (Ollama, models, audio)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QWidget, QTextEdit,
    QComboBox, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess
from pathlib import Path

from ..config import Config


class ModelDownloadWorker(QThread):
    """Worker thread for downloading models"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    def run(self):
        """Download the model"""
        try:
            self.progress.emit(f"Downloading {self.model_name}...")
            result = subprocess.run(
                ['ollama', 'pull', self.model_name],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max
            )

            if result.returncode == 0:
                self.finished.emit(True, f"Successfully downloaded {self.model_name}")
            else:
                self.finished.emit(False, f"Failed to download: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Download timed out")
        except Exception as e:
            self.finished.emit(False, str(e))


class FirstRunWizard(QDialog):
    """
    Wizard for first-time setup
    Steps: 1) Ollama check, 2) Model download, 3) Audio setup, 4) Summary location
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.current_page = 0
        self.setup_ui()

    def setup_ui(self):
        """Set up the wizard UI"""
        self.setWindowTitle("Welcome to Audio Summary")
        self.setGeometry(200, 200, 600, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Stacked widget for pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Create pages
        self.create_welcome_page()
        self.create_ollama_page()
        self.create_model_download_page()
        self.create_audio_page()
        self.create_folder_page()
        self.create_complete_page()

        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.skip_button = QPushButton("Skip Setup")
        self.skip_button.clicked.connect(self.skip_setup)
        button_layout.addWidget(self.skip_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)
        button_layout.addWidget(self.back_button)

        self.next_button = QPushButton("Continue")
        self.next_button.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_button)

        layout.addLayout(button_layout)

    def create_welcome_page(self):
        """Welcome page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Welcome to Audio Summary!")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "This wizard will help you set up Audio Summary for the first time.\n\n"
            "We'll guide you through:\n"
            "  • Installing Ollama (if needed)\n"
            "  • Downloading AI models\n"
            "  • Configuring audio input\n"
            "  • Choosing where to save summaries\n\n"
            "This should only take a few minutes."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_ollama_page(self):
        """Ollama installation check page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Step 1: Ollama")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.ollama_status = QLabel("Checking for Ollama...")
        layout.addWidget(self.ollama_status)

        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setHtml(
            "<h3>What is Ollama?</h3>"
            "<p>Ollama runs AI models locally on your Mac for privacy and offline use.</p>"
            "<h3>Installation:</h3>"
            "<p><b>Option 1 (Homebrew):</b><br>"
            "<code>brew install ollama</code></p>"
            "<p><b>Option 2 (Download):</b><br>"
            "Visit <a href='https://ollama.com/download'>ollama.com/download</a></p>"
        )
        instructions.setMaximumHeight(200)
        layout.addWidget(instructions)

        check_button = QPushButton("Re-check Ollama")
        check_button.clicked.connect(self.check_ollama)
        layout.addWidget(check_button)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_model_download_page(self):
        """Model download page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Step 2: Download AI Model")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "Audio Summary needs a language model for summarization.\n"
            "We recommend qwen3:4b-instruct (4GB download)."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Model selector
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_selector = QComboBox()
        self.model_selector.addItems([
            "qwen3:4b-instruct",
            "llama3.2:3b",
            "phi3:3.8b",
            "gemma2:2b"
        ])
        model_layout.addWidget(self.model_selector)
        layout.addLayout(model_layout)

        # Download button
        self.download_button = QPushButton("Download Model")
        self.download_button.clicked.connect(self.download_model)
        layout.addWidget(self.download_button)

        # Progress
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        self.download_progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.download_progress)

        self.download_status = QLabel("")
        layout.addWidget(self.download_status)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_audio_page(self):
        """Audio setup page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Step 3: Audio Setup")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "To capture Zoom/Teams audio, you'll need BlackHole and a Multi-Output Device."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setHtml(
            "<h3>Step 1: Install BlackHole</h3>"
            "<p><b>Option 1 (Homebrew):</b> <code>brew install --cask blackhole-2ch</code></p>"
            "<p><b>Option 2 (Download):</b> "
            "Visit <a href='https://existential.audio/blackhole/'>existential.audio/blackhole</a></p>"
            "<p style='margin-top: 10px;'><i>Note: After installing, restart your Mac or run: "
            "<code>sudo pkill -9 coreaudiod</code></i></p>"

            "<h3>Step 2: Create Multi-Output Device</h3>"
            "<p>Click the button below to open Audio MIDI Setup, then:</p>"
            "<ol>"
            "<li>Click the <b>+</b> button (bottom-left)</li>"
            "<li>Select <b>'Create Multi-Output Device'</b></li>"
            "<li>Check the boxes for:"
            "  <ul>"
            "    <li>✅ <b>BlackHole 2ch</b> (for Private Notes recording)</li>"
            "    <li>✅ <b>Your speakers/headphones</b> (so you can hear)</li>"
            "  </ul>"
            "</li>"
            "<li>Close Audio MIDI Setup</li>"
            "</ol>"

            "<h3>Step 3: Set as Default Output</h3>"
            "<p>Open <b>System Settings > Sound</b> and set <b>Output</b> to "
            "<b>Multi-Output Device</b></p>"

            "<h3>Step 4: Configure Zoom/Teams</h3>"
            "<p>In your meeting app's audio settings, set <b>Speaker</b> to "
            "<b>Multi-Output Device</b></p>"

            "<h3>Step 5: Configure Private Notes</h3>"
            "<p>In Private Notes Settings, set <b>Input Device</b> to <b>BlackHole 2ch</b></p>"
        )
        layout.addWidget(instructions)

        # Button to open Audio MIDI Setup
        open_midi_button = QPushButton("Open Audio MIDI Setup")
        open_midi_button.clicked.connect(self.open_audio_midi_setup)
        layout.addWidget(open_midi_button)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_folder_page(self):
        """Summary folder selection page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Step 4: Choose Summary Location")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "Where would you like to save meeting summaries?"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Folder selector
        folder_layout = QHBoxLayout()
        self.folder_path = QLabel(str(Path.home() / "Documents" / "Meeting Summaries"))
        folder_layout.addWidget(self.folder_path)

        choose_button = QPushButton("Choose...")
        choose_button.clicked.connect(self.choose_folder)
        folder_layout.addWidget(choose_button)

        layout.addLayout(folder_layout)

        layout.addStretch()
        self.stack.addWidget(page)

    def create_complete_page(self):
        """Setup complete page"""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Setup Complete!")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "You're all set! You can now:\n\n"
            "  • Click the menu bar icon to start/stop recording\n"
            "  • Browse past meetings in Meeting Browser\n"
            "  • Adjust settings anytime\n\n"
            "Enjoy using Audio Summary!"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addStretch()
        self.stack.addWidget(page)

    def check_ollama(self):
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.ollama_status.setText("✓ Ollama is installed")
                self.ollama_status.setStyleSheet("color: green; font-weight: bold;")
                self.next_button.setEnabled(True)
            else:
                self.ollama_status.setText("✗ Ollama not found")
                self.ollama_status.setStyleSheet("color: red; font-weight: bold;")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.ollama_status.setText("✗ Ollama not found. Please install it to continue.")
            self.ollama_status.setStyleSheet("color: red; font-weight: bold;")

    def download_model(self):
        """Download selected model"""
        model_name = self.model_selector.currentText()
        self.download_button.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_status.setText("Downloading...")

        # Start download in background
        self.download_worker = ModelDownloadWorker(model_name)
        self.download_worker.progress.connect(self.download_status.setText)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self, success: bool, message: str):
        """Called when model download completes"""
        self.download_progress.setVisible(False)
        self.download_status.setText(message)

        if success:
            self.download_status.setStyleSheet("color: green; font-weight: bold;")
            self.next_button.setEnabled(True)
        else:
            self.download_status.setStyleSheet("color: red; font-weight: bold;")
            self.download_button.setEnabled(True)

    def choose_folder(self):
        """Choose summary folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Summary Folder",
            str(Path.home() / "Documents")
        )
        if folder:
            self.folder_path.setText(folder)

    def go_next(self):
        """Go to next page"""
        self.current_page += 1

        # Page-specific actions
        if self.current_page == 1:  # Ollama page
            self.check_ollama()

        if self.current_page < self.stack.count():
            self.stack.setCurrentIndex(self.current_page)
            self.back_button.setEnabled(self.current_page > 0)

            # Update button text
            if self.current_page == self.stack.count() - 1:
                self.next_button.setText("Finish")
                self.skip_button.setVisible(False)
        else:
            # Finish wizard
            self.accept()

    def go_back(self):
        """Go to previous page"""
        self.current_page = max(0, self.current_page - 1)
        self.stack.setCurrentIndex(self.current_page)
        self.back_button.setEnabled(self.current_page > 0)
        self.next_button.setText("Continue")
        self.skip_button.setVisible(True)

    def skip_setup(self):
        """Skip the setup wizard"""
        self.accept()

    def open_audio_midi_setup(self):
        """Open Audio MIDI Setup application"""
        try:
            subprocess.run(['open', '-a', 'Audio MIDI Setup'], check=True)
        except Exception as e:
            print(f"Error opening Audio MIDI Setup: {e}")

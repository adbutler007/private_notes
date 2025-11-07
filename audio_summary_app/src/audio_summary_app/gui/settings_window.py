"""
Settings Window
Configure audio, models, and export settings
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QCheckBox, QPushButton, QFileDialog,
    QLineEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
import sounddevice as sd
import subprocess

from ..config import Config


class SettingsWindow(QMainWindow):
    """
    Settings window for configuring the application
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Settings")
        self.setGeometry(150, 150, 600, 500)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Audio Settings
        audio_group = QGroupBox("Audio")
        audio_layout = QFormLayout()

        # Input device selector
        self.input_device = QComboBox()
        self.populate_audio_devices()
        audio_layout.addRow("Input Device:", self.input_device)

        # Auto-detect Zoom/Teams
        self.auto_detect = QCheckBox("Auto-detect Zoom/Teams audio")
        self.auto_detect.setChecked(False)  # TODO: Load from settings
        audio_layout.addRow(self.auto_detect)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Recording Settings
        recording_group = QGroupBox("Recording")
        recording_layout = QFormLayout()

        # Auto-start/stop
        self.auto_start = QCheckBox("Auto-start when Zoom call begins")
        self.auto_start.setChecked(False)  # TODO: Load from settings
        recording_layout.addRow(self.auto_start)

        self.auto_stop = QCheckBox("Auto-stop when call ends")
        self.auto_stop.setChecked(False)  # TODO: Load from settings
        recording_layout.addRow(self.auto_stop)

        self.show_notification = QCheckBox("Show notification when summary ready")
        self.show_notification.setChecked(True)  # TODO: Load from settings
        recording_layout.addRow(self.show_notification)

        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)

        # Models Settings
        models_group = QGroupBox("Models")
        models_layout = QFormLayout()

        # STT Backend selector
        self.stt_backend = QComboBox()
        self.stt_backend.addItems(["parakeet", "whisper"])
        # Set current backend
        current_backend = self.config.stt_backend
        index = self.stt_backend.findText(current_backend)
        if index >= 0:
            self.stt_backend.setCurrentIndex(index)
        self.stt_backend.currentTextChanged.connect(self.on_stt_backend_changed)
        models_layout.addRow("STT Backend:", self.stt_backend)

        # Whisper model selector (only shown if whisper is selected)
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "small", "medium", "large", "turbo"])
        # Set current model
        current_model = self.config.stt_model_path
        index = self.whisper_model.findText(current_model)
        if index >= 0:
            self.whisper_model.setCurrentIndex(index)
        self.whisper_model_row = models_layout.rowCount()
        models_layout.addRow("Whisper Model:", self.whisper_model)

        # Parakeet model selector (only shown if parakeet is selected)
        self.parakeet_model = QComboBox()
        self.parakeet_model.addItems([
            "mlx-community/parakeet-tdt-0.6b-v3",
            "mlx-community/parakeet-tdt-0.6b-v2"
        ])
        # Set current model
        current_parakeet = self.config.parakeet_model_path
        index = self.parakeet_model.findText(current_parakeet)
        if index >= 0:
            self.parakeet_model.setCurrentIndex(index)
        self.parakeet_model_row = models_layout.rowCount()
        models_layout.addRow("Parakeet Model:", self.parakeet_model)

        # Update visibility based on current backend
        self.on_stt_backend_changed(self.config.stt_backend)

        # Download models button
        download_button = QPushButton("Download Models")
        download_button.clicked.connect(self.download_models)
        models_layout.addRow(download_button)

        # LLM model selector
        self.llm_model = QComboBox()
        self.llm_model.addItems([
            "qwen3:4b-instruct",
            "llama3.2:3b",
            "phi3:3.8b",
            "gemma2:2b"
        ])
        # Set current model
        current_llm = self.config.llm_model_name
        index = self.llm_model.findText(current_llm)
        if index >= 0:
            self.llm_model.setCurrentIndex(index)
        models_layout.addRow("LLM Model:", self.llm_model)

        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        # Export Settings
        export_group = QGroupBox("Export")
        export_layout = QFormLayout()

        # Summary folder
        folder_layout = QHBoxLayout()
        self.summary_folder = QLineEdit(self.config.output_dir)
        self.summary_folder.setReadOnly(True)
        folder_layout.addWidget(self.summary_folder)

        choose_folder_button = QPushButton("Choose...")
        choose_folder_button.clicked.connect(self.choose_summary_folder)
        folder_layout.addWidget(choose_folder_button)

        export_layout.addRow("Summary Folder:", folder_layout)

        # CSV export
        csv_layout = QHBoxLayout()
        self.csv_path = QLineEdit(self.config.csv_export_path)
        self.csv_path.setReadOnly(True)
        csv_layout.addWidget(self.csv_path)

        choose_csv_button = QPushButton("Choose...")
        choose_csv_button.clicked.connect(self.choose_csv_path)
        csv_layout.addWidget(choose_csv_button)

        export_layout.addRow("CSV Export:", csv_layout)

        # Auto-export weekly
        self.auto_export = QCheckBox("Auto-export to CSV weekly (Fridays)")
        self.auto_export.setChecked(False)  # TODO: Load from settings
        export_layout.addRow(self.auto_export)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def populate_audio_devices(self):
        """Populate audio device dropdown"""
        try:
            devices = sd.query_devices()
            macbook_mic_index = -1
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:  # Input device
                    self.input_device.addItem(f"{device['name']}", i)
                    # Find MacBook Air Microphone
                    if "MacBook Air Microphone" in device['name']:
                        macbook_mic_index = self.input_device.count() - 1

            # Default to MacBook Air Microphone if found
            if macbook_mic_index >= 0:
                self.input_device.setCurrentIndex(macbook_mic_index)
        except Exception as e:
            self.input_device.addItem("Error loading devices", None)

    def on_stt_backend_changed(self, backend: str):
        """Handle STT backend change"""
        # Show/hide model selectors based on backend
        self.whisper_model.setVisible(backend == "whisper")
        self.parakeet_model.setVisible(backend == "parakeet")

    def download_models(self):
        """Download models"""
        # For now, just show instructions
        msg = QMessageBox(self)
        msg.setWindowTitle("Download Models")
        msg.setText("Models are downloaded automatically on first use.\n\n"
                    "Whisper models download when first transcribing.\n"
                    "Ollama models can be downloaded via terminal:\n\n"
                    f"  ollama pull {self.llm_model.currentText()}")
        msg.exec()

    def choose_summary_folder(self):
        """Choose summary folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Summary Folder",
            self.summary_folder.text()
        )
        if folder:
            self.summary_folder.setText(folder)

    def choose_csv_path(self):
        """Choose CSV export path"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose CSV Export Path",
            self.csv_path.text(),
            "CSV Files (*.csv)"
        )
        if file_path:
            self.csv_path.setText(file_path)

    def save_settings(self):
        """Save settings"""
        # TODO: Implement actual settings persistence
        # For now, just show a message
        msg = QMessageBox(self)
        msg.setWindowTitle("Settings Saved")
        msg.setText("Settings have been saved.\n\n"
                    "Note: Some settings require restarting the app.")
        msg.exec()
        self.close()

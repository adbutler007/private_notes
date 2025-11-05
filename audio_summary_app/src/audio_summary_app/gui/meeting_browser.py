"""
Meeting Browser Window
Browse, search, and filter all meeting summaries
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt
from pathlib import Path
import json
from datetime import datetime, timedelta

from ..config import Config


class MeetingBrowser(QMainWindow):
    """
    Window for browsing all meeting summaries
    Features: search, filter by date/company, preview
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.current_summaries = []
        self.setup_ui()
        self.load_summaries()

    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Meeting Browser")
        self.setGeometry(100, 100, 1000, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Top bar: Search and filters
        top_layout = QHBoxLayout()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search meetings...")
        self.search_box.textChanged.connect(self.filter_summaries)
        top_layout.addWidget(self.search_box)

        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItems([
            "All Time",
            "Today",
            "Yesterday",
            "This Week",
            "Last Week",
            "This Month",
            "Last Month"
        ])
        self.date_filter.currentTextChanged.connect(self.filter_summaries)
        top_layout.addWidget(self.date_filter)

        # Company filter (will be populated dynamically)
        self.company_filter = QComboBox()
        self.company_filter.addItem("All Companies")
        self.company_filter.currentTextChanged.connect(self.filter_summaries)
        top_layout.addWidget(self.company_filter)

        layout.addLayout(top_layout)

        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Meeting list
        self.meeting_list = QListWidget()
        self.meeting_list.itemClicked.connect(self.show_preview)
        splitter.addWidget(self.meeting_list)

        # Preview pane
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        self.preview_title = QLabel("Select a meeting to preview")
        self.preview_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        preview_layout.addWidget(self.preview_title)

        self.preview_meta = QLabel("")
        preview_layout.addWidget(self.preview_meta)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        # Action buttons
        button_layout = QHBoxLayout()
        open_button = QPushButton("Open in Editor")
        open_button.clicked.connect(self.open_current_summary)
        button_layout.addWidget(open_button)

        open_folder_button = QPushButton("Show in Finder")
        open_folder_button.clicked.connect(self.show_in_finder)
        button_layout.addWidget(open_folder_button)

        preview_layout.addLayout(button_layout)

        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)  # List gets 1/3
        splitter.setStretchFactor(1, 2)  # Preview gets 2/3

        layout.addWidget(splitter)

    def load_summaries(self):
        """Load all summaries from output directory"""
        output_dir = Path(self.config.output_dir)
        if not output_dir.exists():
            return

        summaries = []
        companies = set()

        # Get all summary files
        for txt_file in sorted(output_dir.glob("summary_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True):
            timestamp_str = txt_file.stem.replace("summary_", "")

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except ValueError:
                continue

            # Try to load JSON for structured data
            json_file = txt_file.parent / f"summary_{timestamp_str}.json"
            contact_name = ""
            company_name = ""

            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        contacts = data.get('contacts', [])
                        companies_list = data.get('companies', [])

                        if contacts:
                            contact_name = contacts[0].get('name', '')
                        if companies_list:
                            company_name = companies_list[0].get('name', '')
                            if company_name:
                                companies.add(company_name)
                except:
                    pass

            summaries.append({
                'txt_file': txt_file,
                'json_file': json_file if json_file.exists() else None,
                'timestamp': timestamp,
                'contact_name': contact_name,
                'company_name': company_name,
            })

        self.current_summaries = summaries

        # Update company filter
        self.company_filter.clear()
        self.company_filter.addItem("All Companies")
        for company in sorted(companies):
            if company:
                self.company_filter.addItem(company)

        # Display all
        self.filter_summaries()

    def filter_summaries(self):
        """Filter summaries based on search and filters"""
        search_text = self.search_box.text().lower()
        date_filter = self.date_filter.currentText()
        company_filter = self.company_filter.currentText()

        # Calculate date range
        now = datetime.now()
        date_cutoff = None

        if date_filter == "Today":
            date_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Yesterday":
            yesterday = now - timedelta(days=1)
            date_cutoff = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "This Week":
            date_cutoff = now - timedelta(days=now.weekday())
            date_cutoff = date_cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Last Week":
            date_cutoff = now - timedelta(days=now.weekday() + 7)
            date_cutoff = date_cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "This Month":
            date_cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Last Month":
            last_month = now.replace(day=1) - timedelta(days=1)
            date_cutoff = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Filter summaries
        filtered = []
        for summary in self.current_summaries:
            # Date filter
            if date_cutoff and summary['timestamp'] < date_cutoff:
                if date_filter in ["Yesterday", "Last Week", "Last Month"]:
                    # These are ranges, not "since" filters
                    pass  # TODO: Implement proper range filtering
                else:
                    continue

            # Company filter
            if company_filter != "All Companies" and summary['company_name'] != company_filter:
                continue

            # Search filter
            if search_text:
                searchable = f"{summary['contact_name']} {summary['company_name']}".lower()
                if search_text not in searchable:
                    continue

            filtered.append(summary)

        # Update list
        self.meeting_list.clear()
        for summary in filtered:
            # Format display
            if summary['company_name'] and summary['contact_name']:
                display = f"{summary['company_name']} - {summary['contact_name']}"
            elif summary['company_name']:
                display = summary['company_name']
            elif summary['contact_name']:
                display = summary['contact_name']
            else:
                display = "Meeting"

            date_str = summary['timestamp'].strftime("%b %d, %Y %I:%M %p")
            display = f"{display}\n{date_str}"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, summary)
            self.meeting_list.addItem(item)

    def show_preview(self, item: QListWidgetItem):
        """Show preview of selected summary"""
        summary = item.data(Qt.ItemDataRole.UserRole)

        # Set title
        if summary['company_name'] and summary['contact_name']:
            title = f"{summary['company_name']} - {summary['contact_name']}"
        elif summary['company_name']:
            title = summary['company_name']
        elif summary['contact_name']:
            title = summary['contact_name']
        else:
            title = "Meeting"

        self.preview_title.setText(title)

        # Set metadata
        date_str = summary['timestamp'].strftime("%B %d, %Y at %I:%M %p")
        self.preview_meta.setText(date_str)

        # Load and show summary text
        try:
            with open(summary['txt_file'], 'r', encoding='utf-8') as f:
                text = f.read()
            self.preview_text.setPlainText(text)
        except Exception as e:
            self.preview_text.setPlainText(f"Error loading summary: {e}")

        # Store current summary for actions
        self.current_summary = summary

    def open_current_summary(self):
        """Open current summary in default editor"""
        if hasattr(self, 'current_summary'):
            import subprocess
            subprocess.run(['open', str(self.current_summary['txt_file'])])

    def show_in_finder(self):
        """Show current summary in Finder"""
        if hasattr(self, 'current_summary'):
            import subprocess
            subprocess.run(['open', '-R', str(self.current_summary['txt_file'])])

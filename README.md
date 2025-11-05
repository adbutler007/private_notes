# Audio Summary App

Privacy-first audio summarization for sales discovery calls using on-device AI.

## Features

- **Real-time transcription** using MLX Whisper (optimized for Apple Silicon)
- **Rolling summaries** every 5 minutes using Ollama (on-device LLM)
- **Structured data extraction** for contacts, companies, and deals
- **Privacy-first**: Audio and transcripts never saved, only summaries
- **CSV export** for CRM integration (Salesforce, HubSpot, etc.)

## Installation

### For End Users (Recommended)

**Install via Homebrew:**

```bash
# Add the tap
brew tap adbutler007/audio-summary

# Install
brew install --cask audio-summary

# Download the LLM model
ollama pull qwen3:4b-instruct
```

Then launch **Audio Summary** from your Applications folder or menu bar.

See the [User Guide](audio_summary_app/USER_GUIDE.md) for complete setup instructions.

### For Developers

#### Prerequisites

1. **macOS** with Apple Silicon (M1/M2/M3/M4)
2. **Python 3.11+**
3. **Ollama** for LLM inference
4. **uv** for dependency management

#### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama
brew install ollama

# Pull the LLM model
ollama pull qwen3:4b-instruct

# Install dependencies
cd audio_summary_app
uv sync
```

## Usage

### GUI Mode (Recommended)

```bash
uv run audio-summary-gui
```

Or simply launch the **Audio Summary** app from your menu bar.

See [User Guide](audio_summary_app/USER_GUIDE.md) for complete usage instructions.

### CLI Mode (For developers)

#### Interactive Mode (Real-time Recording)

```bash
uv run python -m audio_summary_app
> start   # Begin recording
> stop    # Stop and generate summary
> quit    # Exit application
```

#### Batch Mode (Process Audio File)

```bash
uv run python audio_summary_app/process_audio_file.py path/to/audio.mp3
```

## Output Files

After each recording, a folder is created with:

```
~/Documents/Meeting Summaries/
└── 2025-11-05 Acme Capital - John Smith/
    ├── summary.txt    # Human-readable summary (3-5 paragraphs)
    └── data.json      # Structured data (contacts, companies, deals)
```

Plus a cumulative `meetings.csv` with all meetings.

## Configuration

Edit `src/audio_summary_app/config.py` to customize:

- **Whisper model**: `stt_model_path` (tiny, small, medium, large, turbo)
- **LLM model**: `llm_model_name` (qwen3:4b-instruct, llama3.2:3b, etc.)
- **Token limits**: `chunk_summary_max_tokens`, `final_summary_max_tokens`
- **Summary prompts**: Customize for your use case
- **Output paths**: `output_dir`, `csv_export_path`

## Architecture

### Privacy-First Design

- Audio captured in RAM only (never saved to disk)
- Transcripts held in memory buffer (deleted after chunk summarization)
- Only summaries and structured data are persisted

### Map-Reduce Summarization

1. **MAP Phase**: Every 5 minutes, create chunk summary from transcript buffer
2. **REDUCE Phase**: After recording stops, combine chunk summaries into final summary
3. **EXTRACTION Phase**: Extract structured data (contacts, companies, deals) using Ollama structured outputs

### Technology Stack

- **MLX Whisper**: 3-5x faster speech-to-text on Apple Silicon
- **Ollama**: On-device LLM inference (no cloud API calls)
- **Pydantic**: Type-safe structured data validation
- **uv**: Fast Python package manager

## Documentation

- **[User Guide](audio_summary_app/USER_GUIDE.md)** - Complete usage instructions
- **[Deployment Guide](audio_summary_app/DEPLOYMENT.md)** - Building and distributing the app
- [Structured Data Extraction](audio_summary_app/STRUCTURED_DATA.md)
- [CSV Export Examples](audio_summary_app/CSV_EXAMPLE.md)

## Features Completed

- ✅ macOS GUI with menu bar icon
- ✅ Meeting Browser with search and filters
- ✅ Auto-naming using contact/company data
- ✅ Settings window
- ✅ First-Run Setup Wizard
- ✅ Homebrew Cask formula
- ✅ Privacy-first architecture
- ✅ Real-time transcription and summarization
- ✅ Structured data extraction
- ✅ CSV export for CRM integration

## Roadmap

- [ ] Auto-detect Zoom/Teams audio (process monitoring)
- [ ] Zoom/Teams auto-start/stop
- [ ] Quick Look plugin for Finder previews
- [ ] Spotlight integration
- [ ] Windows support (Faster-Whisper backend)
- [ ] Code signing and notarization

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

---

Built with privacy and efficiency in mind for sales professionals.

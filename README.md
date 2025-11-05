# Audio Summary App

Privacy-first audio summarization for sales discovery calls using on-device AI.

## Features

- **Real-time transcription** using MLX Whisper (optimized for Apple Silicon)
- **Rolling summaries** every 5 minutes using Ollama (on-device LLM)
- **Structured data extraction** for contacts, companies, and deals
- **Privacy-first**: Audio and transcripts never saved, only summaries
- **CSV export** for CRM integration (Salesforce, HubSpot, etc.)

## Quick Start

### Prerequisites

1. **macOS** with Apple Silicon (M1/M2/M3/M4)
2. **Python 3.11+**
3. **Ollama** for LLM inference
4. **uv** for dependency management

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama
brew install ollama

# Pull the LLM model
ollama pull qwen3:4b-instruct

# Install dependencies
uv sync
```

### Usage

#### Interactive Mode (Real-time Recording)

```bash
uv run python -m audio_summary_app
> start   # Begin recording
> stop    # Stop and generate summary
> quit    # Exit application
```

#### Batch Mode (Process Audio File)

```bash
uv run python process_audio_file.py path/to/audio.mp3
```

## Output Files

After each recording, three files are generated in `./summaries/`:

1. **`summary_YYYYMMDD_HHMMSS.txt`** - Human-readable summary (3-5 paragraphs)
2. **`summary_YYYYMMDD_HHMMSS.json`** - Structured data (contacts, companies, deals)
3. **`meetings.csv`** - Cumulative spreadsheet (one row per meeting)

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

- [Structured Data Extraction](audio_summary_app/STRUCTURED_DATA.md)
- [CSV Export](audio_summary_app/CSV_EXAMPLE.md)

## Roadmap

- [ ] macOS GUI with menu bar icon
- [ ] Auto-detect Zoom/Teams audio (BlackHole integration)
- [ ] Meeting Browser with search and filters
- [ ] Homebrew distribution
- [ ] Windows support (Faster-Whisper backend)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

---

Built with privacy and efficiency in mind for sales professionals.

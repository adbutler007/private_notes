# Audio Summary App

A privacy-focused desktop application that captures audio (both microphone input and system output), transcribes it in real-time using **OpenAI Whisper**, and generates intelligent summaries using **Ollama** - all running locally on your computer.

## ✨ What's New

- 🚀 **Simplified Setup** - Uses Ollama (no manual model downloads!)
- ⚡ **Faster Installation** - Managed by `uv` for 10-100x faster dependency installation
- 🤖 **Better Models** - Qwen3:1.7b for efficient, high-quality summaries
- 🎯 **Auto-Download** - Whisper models download automatically on first use
- 💻 **Native Support** - Runs on any modern Mac or Windows PC

## 🚀 Quick Start (5 minutes)

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Windows: Download from https://ollama.com/download
# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the Model
```bash
ollama pull qwen3:1.7b
```

### 3. Install Dependencies
```bash
# Using uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
source .venv/bin/activate

# Or using pip
pip install -r requirements.txt
```

### 4. Run It!
```bash
python main.py
```

**That's it!** Whisper will auto-download on first run (~140MB).

📖 **For detailed setup instructions, see [SETUP.md](SETUP.md)**

## 🔒 Privacy First

- **No data saved to disk** except final summaries
- **No cloud services** - all processing happens locally
- Audio streams directly to transcription (never written to files)
- Transcripts kept only in RAM buffer
- You control what gets saved

## 🏗️ Architecture

```
┌─────────────┐
│ Microphone  │──┐
└─────────────┘  │
                 │    ┌──────────────┐      ┌──────────────┐
┌─────────────┐  ├───→│   Whisper    │─────→│  Transcript  │
│System Audio │──┘    │ (Speech-to-  │      │   Buffer     │
└─────────────┘       │    Text)     │      │ (In Memory)  │
                      └──────────────┘      └──────┬───────┘
                                                    │
                                                    ▼
                      ┌──────────────┐      ┌──────────────┐
                      │    Final     │◀─────│    Ollama    │
                      │   Summary    │      │(Map-Reduce   │
                      │  (Saved to   │      │ Summarizer)  │
                      │    Disk)     │      └──────────────┘
                      └──────────────┘
```

### Components

1. **Audio Capture Manager** ([audio_capture.py](audio_capture.py))
   - Captures microphone input (what you say)
   - Captures system audio output (what you hear)
   - Streams audio directly to processing pipeline
   - Audio data never touches disk

2. **Streaming Transcriber** ([transcriber.py](transcriber.py))
   - On-device speech-to-text using **OpenAI Whisper**
   - Processes audio chunks in real-time
   - Auto-downloads models on first use
   - Supports: tiny, base, small, medium, large

3. **Transcript Buffer** ([transcript_buffer.py](transcript_buffer.py))
   - Circular buffer in RAM (auto-discards old data)
   - Thread-safe transcript storage
   - Organizes segments into chunks for summarization
   - Completely in-memory, never touches disk

4. **Map-Reduce Summarizer** ([summarizer.py](summarizer.py))
   - Uses **Ollama** with **Qwen3:1.7b** for summarization
   - MAP Phase: Summarize individual time-based chunks (every 5 min)
   - REDUCE Phase: Combine chunk summaries into final comprehensive summary
   - All processing happens locally

## 📋 Requirements

**Minimum:**
- Python 3.9+
- 4 GB RAM
- 3 GB disk space (for models)
- Dual-core CPU

**Recommended:**
- Python 3.11+
- 8 GB RAM
- 5 GB disk space
- Quad-core CPU

## 🎯 Use Cases

- 📝 Meeting notes and summaries
- 🎓 Lecture transcription
- 🎤 Interview documentation
- 🏥 Confidential discussions (HIPAA-friendly)
- 🔬 Research interviews
- ♿ Accessibility support
- 📓 Personal voice journaling

## ⚙️ Configuration

Edit [config.py](config.py) to customize:

```python
class Config:
    # Audio
    sample_rate: int = 16000  # 16kHz for speech
    channels: int = 1         # Mono

    # Transcription (Whisper)
    stt_model_path: str = "base"  # tiny, base, small, medium, large

    # Summarization (Ollama)
    llm_model_name: str = "qwen3:1.7b"  # Or: llama3.2:3b, phi3:3.8b

    # Summary
    summary_interval: int = 300  # Rolling summary every 5 minutes
    output_dir: str = "./summaries"
```

### Available Models

**Whisper** (auto-download):
- `tiny` (39 MB) - Fastest
- `base` (74 MB) - **Recommended**
- `small` (244 MB) - Better accuracy
- `medium` (769 MB) - High accuracy
- `large` (1.5 GB) - Best accuracy

**Ollama** (must pull separately):
- `qwen3:1.7b` (1.1 GB) - **Recommended** - Fast & efficient
- `llama3.2:3b` (2 GB) - Better quality
- `phi3:3.8b` (2.3 GB) - Good reasoning
- `gemma2:2b` (1.6 GB) - Fast alternative

```bash
ollama pull llama3.2:3b  # Example: use a different model
```

## 🎮 Usage

### Start the app:
```bash
python main.py
```

### Commands:
- `start` - Begin recording and transcription
- `stop` - Stop recording and generate final summary
- `quit` - Exit the application

### Example Session:
```
$ python main.py
[STT] Loading Whisper model: base
[STT] Model loaded successfully
[LLM] Using Ollama model: qwen3:1.7b
[LLM] Model qwen3:1.7b is ready

Audio Summary App started.
Commands: start, stop, quit

> start
Recording started...

> stop
Recording stopped.
Generating final summary...
Summary saved to: ./summaries/summary_20250105_143022.txt

> quit
Goodbye!
```

## 🧪 Demo Mode

Test without audio hardware:
```bash
python demo.py
```

This runs a simulation with mock data to verify the installation.

## 📁 Project Structure

```
audio_summary_app/
├── SETUP.md                # Quick setup guide (START HERE!)
├── README.md               # This file
├── pyproject.toml          # Modern Python project config
├── requirements.txt        # Dependencies (pip)
├── .python-version         # Python version for uv
├── config.py               # Configuration settings
├── main.py                 # Application entry point
├── demo.py                 # Hardware-free demo
├── audio_capture.py        # Audio input/output capture
├── transcriber.py          # Whisper speech-to-text
├── transcript_buffer.py    # In-memory transcript storage
├── summarizer.py           # Ollama-based summarization
├── ARCHITECTURE.md         # Detailed system design
├── DATA_FLOW.md           # Privacy architecture
├── INSTALL.md             # Platform-specific setup
├── INSTALL_UV.md          # Installation with uv
└── UV_MIGRATION.md        # Migration guide
```

## 🔧 Troubleshooting

### Ollama not found
```bash
# Make sure Ollama is running
ollama list

# Start Ollama (usually auto-starts)
ollama serve
```

### Audio capture not working
See [SETUP.md](SETUP.md#step-4-configure-audio-capture) for platform-specific audio configuration.

### Out of memory
Use smaller models:
```python
stt_model_path = "tiny"      # Smaller Whisper
llm_model_name = "qwen3:1.7b"  # Already smallest recommended
```

### Slow performance
- Use GPU for Whisper (auto-detected if available)
- Use smaller models
- Increase summary interval: `summary_interval = 600`

## 📚 Documentation

- [SETUP.md](SETUP.md) - **Quick setup guide** (recommended)
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and components
- [DATA_FLOW.md](DATA_FLOW.md) - Privacy architecture and data lifecycle
- [INSTALL.md](INSTALL.md) - Detailed platform-specific installation
- [INSTALL_UV.md](INSTALL_UV.md) - Installation using uv
- [UV_MIGRATION.md](UV_MIGRATION.md) - Migration from pip to uv

## 🛠️ Development

### Install with dev tools:
```bash
uv sync --extra dev
```

### Run tests:
```bash
pytest
```

### Format code:
```bash
black .
ruff check .
```

## 💾 What Gets Saved?

| Data Type | Location | Saved? |
|-----------|----------|--------|
| Raw Audio | Audio Queue | ❌ No |
| Audio Buffer | STT Component | ❌ No |
| Transcripts | Transcript Buffer | ❌ No |
| Intermediate Summaries | Summarizer (RAM) | ❌ No |
| **Final Summary** | **./summaries/** | **✅ Yes** |

Only final summaries (2-5 KB text files) are saved to disk.

## 🔐 Security & Privacy

- 🔒 **100% Local Processing** - No data leaves your computer
- 🔒 **No Cloud APIs** - Everything runs on-device
- 🔒 **Minimal Disk Usage** - Only summaries saved
- 🔒 **Open Source** - Inspect the code yourself
- 🔒 **No Telemetry** - No tracking or analytics
- 🔒 **HIPAA Friendly** - Suitable for confidential discussions

## 🤝 Contributing

Contributions welcome! This is a privacy-first project focused on:
- Local-first processing
- Minimal disk persistence
- User control and transparency

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built with:
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Ollama](https://ollama.com/) - Local LLM inference
- [Qwen3](https://ollama.com/library/qwen3) - Efficient language model
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

---

**Get started in 5 minutes:** See [SETUP.md](SETUP.md)

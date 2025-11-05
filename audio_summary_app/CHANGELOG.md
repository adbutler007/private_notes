# Changelog

## Version 2.0.0 - Native Mac/Windows Support (2025-01-05)

### 🎉 Major Changes

This release completely modernizes the Audio Summary App for native support on Mac and Windows, with simplified setup and better performance.

### ✨ New Features

#### Simplified Model Management
- **Ollama Integration** - Replaced llama-cpp-python with Ollama for easier setup
  - No manual model downloads required
  - Models managed through simple `ollama pull` command
  - Better performance and stability
  - Default model: `qwen3:1.7b` (1.1GB, fast and efficient)

- **OpenAI Whisper** - Switched to official OpenAI Whisper implementation
  - Auto-downloads models on first use
  - Better accuracy and reliability
  - Native GPU support (auto-detected)
  - No compilation required

#### Modern Python Packaging
- **uv Support** - Added support for uv package manager
  - 10-100x faster than pip
  - Automatic virtual environment management
  - Lockfile support for reproducible builds
  - `pyproject.toml` configuration

- **Project Metadata** - Added comprehensive project configuration
  - CLI entry points: `audio-summary` and `audio-summary-demo`
  - Optional dependency groups for alternative backends
  - Development tools included (pytest, black, ruff, mypy)

#### Better Documentation
- **SETUP.md** - New quick setup guide (5-minute install)
- **UV_MIGRATION.md** - Migration guide from pip to uv
- **INSTALL_UV.md** - Detailed uv installation instructions
- **CHANGELOG.md** - This file!

### 🔄 Changed

#### Dependencies
**Removed:**
- `faster-whisper>=0.10.0` → Moved to optional
- `llama-cpp-python>=0.2.0` → Moved to optional

**Added:**
- `openai-whisper>=20230918` → Default STT
- `ollama>=0.1.0` → Default LLM

**Kept:**
- `sounddevice>=0.4.6`
- `numpy>=1.24.0`
- `python-dateutil>=2.8.2`

#### Configuration ([config.py](config.py))
**Changed:**
- `stt_model_path: str = "base"` (was `"base.en"`)
  - Removed `.en` suffix for OpenAI Whisper compatibility
  - Options: tiny, base, small, medium, large

- `llm_model_path` → `llm_model_name: str = "qwen3:1.7b"`
  - Changed from file path to Ollama model name
  - Other options: llama3.2:3b, phi3:3.8b, gemma2:2b

**Updated:**
- Model setup instructions now reference Ollama
- Auto-download information for both models

#### Code

**[transcriber.py](transcriber.py):**
- Replaced faster-whisper with OpenAI Whisper
- Added automatic model loading with fallback to mock
- Improved error handling and logging
- Better audio normalization

**[summarizer.py](summarizer.py):**
- Replaced llama-cpp-python with Ollama
- Added `OllamaLLM` class for Ollama integration
- Auto-downloads missing Ollama models
- Improved error handling with fallback to mock
- Better prompt engineering for qwen3

**[main.py](main.py):**
- Updated to use `model_name` instead of `model_path`
- Compatible with new config structure

**[pyproject.toml](pyproject.toml):** (NEW)
- Modern Python project configuration
- Dependency management
- Optional dependency groups
- CLI entry points
- Tool configurations (black, ruff, mypy)

### 📝 Documentation Updates

#### New Files
- `SETUP.md` - Quick 5-minute setup guide
- `README_UPDATED.md` - Updated README with new instructions
- `CHANGELOG.md` - This changelog
- `UV_MIGRATION.md` - Migration guide for uv
- `INSTALL_UV.md` - Detailed uv installation
- `pyproject.toml` - Project configuration
- `.python-version` - Python version specification

#### Updated Files
- `requirements.txt` - Updated dependencies
- `config.py` - New model settings
- `README.md` → `README_UPDATED.md` (new version)
- `INSTALL.md` - Still available for traditional setup

### 🚀 Performance Improvements

- **Faster Installation** - uv provides 10-100x faster dependency resolution
- **Better Models** - Qwen3:1.7b is optimized for speed and efficiency
- **Simpler Setup** - No manual model downloads or compilation
- **Auto-Download** - Both Whisper and Ollama handle models automatically

### 🐛 Bug Fixes

- Fixed audio normalization in transcriber
- Improved thread safety in summarizer
- Better error handling throughout
- Graceful fallback when models aren't available

### 🔧 Installation

#### New Installation (Recommended)
```bash
# Install Ollama
brew install ollama  # macOS
# or download from ollama.com for Windows/Linux

# Pull model
ollama pull qwen3:1.7b

# Install with uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

#### Traditional Installation
```bash
# Install Ollama (same as above)
brew install ollama
ollama pull qwen3:1.7b

# Install with pip
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 📊 Model Comparisons

#### Whisper Models
| Model | Size | Speed | Accuracy | Recommendation |
|-------|------|-------|----------|----------------|
| tiny | 39 MB | Fastest | Lower | Testing only |
| **base** | **74 MB** | **Fast** | **Good** | **Recommended** |
| small | 244 MB | Medium | Better | High accuracy needs |
| medium | 769 MB | Slow | High | Professional use |
| large | 1.5 GB | Slowest | Best | Maximum accuracy |

#### Ollama Models
| Model | Size | Speed | Quality | Recommendation |
|-------|------|-------|---------|----------------|
| **qwen3:1.7b** | **1.1 GB** | **Fastest** | **Good** | **Recommended** |
| gemma2:2b | 1.6 GB | Fast | Good | Alternative |
| llama3.2:3b | 2 GB | Medium | Better | Higher quality |
| phi3:3.8b | 2.3 GB | Medium | Better | Good reasoning |

### 🔄 Migration Guide

#### For Existing Users

1. **Install Ollama:**
   ```bash
   brew install ollama
   ollama pull qwen3:1.7b
   ```

2. **Update Dependencies:**
   ```bash
   # With uv
   uv sync

   # Or with pip
   pip install -r requirements.txt
   ```

3. **Update Config (if customized):**
   - Change `llm_model_path` → `llm_model_name`
   - Change `stt_model_path` from `"base.en"` → `"base"`

4. **Your data is preserved:**
   - Existing summaries in `./summaries/` are unchanged
   - No breaking changes to saved data

### ⚠️ Breaking Changes

#### Configuration
- `Config.llm_model_path` (str) → `Config.llm_model_name` (str)
- `stt_model_path` values changed from `"base.en"` → `"base"`

#### Dependencies
- `faster-whisper` is now optional (install with `uv sync --extra faster-whisper-backend`)
- `llama-cpp-python` is now optional (install with `uv sync --extra llama-cpp`)

#### Code
- `MapReduceSummarizer.__init__()` now takes `model_name` instead of `model_path`
- Whisper models use OpenAI API instead of faster-whisper API

### 🎯 System Requirements

**Minimum (unchanged):**
- Python 3.9+
- 4 GB RAM
- 3 GB disk space
- Dual-core CPU

**Recommended:**
- Python 3.11+ (was 3.9+)
- 8 GB RAM (was 4 GB)
- 5 GB disk space (was 10 GB)
- Quad-core CPU

### 🔐 Privacy & Security

**No changes to privacy model:**
- ✅ Still 100% local processing
- ✅ Still no cloud services
- ✅ Still minimal disk usage
- ✅ Still only summaries saved
- ✅ Ollama runs locally (like llama-cpp-python did)

### 📦 Package Structure

```
audio_summary_app/
├── pyproject.toml          # NEW: Modern project config
├── .python-version         # NEW: Python version
├── SETUP.md                # NEW: Quick setup
├── CHANGELOG.md            # NEW: This file
├── README_UPDATED.md       # NEW: Updated README
├── UV_MIGRATION.md         # NEW: Migration guide
├── INSTALL_UV.md           # NEW: uv installation
├── requirements.txt        # UPDATED: New dependencies
├── config.py               # UPDATED: New model settings
├── transcriber.py          # UPDATED: OpenAI Whisper
├── summarizer.py           # UPDATED: Ollama
├── main.py                 # UPDATED: New config
├── demo.py                 # UNCHANGED
├── audio_capture.py        # UNCHANGED
├── transcript_buffer.py    # UNCHANGED
├── README.md               # PRESERVED (original)
├── ARCHITECTURE.md         # UNCHANGED
├── DATA_FLOW.md           # UNCHANGED
├── INSTALL.md             # UNCHANGED
└── PROJECT_OVERVIEW.md    # UNCHANGED
```

### 🚧 Backwards Compatibility

#### Fully Compatible
- Existing summary files
- Existing configuration format (with migration)
- Audio capture settings
- Buffer settings
- Output directory structure

#### Requires Changes
- Model paths → model names (in config)
- Direct API calls to faster-whisper → OpenAI Whisper
- Direct API calls to llama-cpp-python → Ollama

### 🔮 Future Plans

- [ ] Web UI for easier interaction
- [ ] Real-time streaming summaries
- [ ] Multiple language support
- [ ] Custom prompt templates
- [ ] Export formats (PDF, Markdown, JSON)
- [ ] Audio device hot-swapping
- [ ] Background mode / system tray

### 🙏 Credits

**New Dependencies:**
- [Ollama](https://ollama.com/) - Local LLM runtime
- [Qwen3](https://ollama.com/library/qwen3) - Efficient language model
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [uv](https://github.com/astral-sh/uv) - Fast package manager

**Maintained Dependencies:**
- [sounddevice](https://python-sounddevice.readthedocs.io/)
- [NumPy](https://numpy.org/)

### 📞 Support

For issues with:
- **Setup/Installation**: See [SETUP.md](SETUP.md)
- **Audio Capture**: See [INSTALL.md](INSTALL.md)
- **Ollama**: Visit [ollama.com/docs](https://ollama.com/docs)
- **Whisper**: Visit [github.com/openai/whisper](https://github.com/openai/whisper)
- **uv**: Visit [github.com/astral-sh/uv](https://github.com/astral-sh/uv)

---

## Version 1.0.0 - Initial Release

### Features

- Privacy-first audio capture and transcription
- On-device speech-to-text using faster-whisper
- Map-reduce summarization with llama-cpp-python
- Circular buffer for memory efficiency
- Thread-safe processing pipeline
- Mock implementations for testing
- Comprehensive documentation

### Components

- Audio Capture Manager
- Streaming Transcriber
- Transcript Buffer
- Map-Reduce Summarizer
- Demo mode

### Documentation

- README.md
- ARCHITECTURE.md
- DATA_FLOW.md
- INSTALL.md
- PROJECT_OVERVIEW.md

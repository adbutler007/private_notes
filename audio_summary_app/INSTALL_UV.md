# Installation Guide (Using uv)

This guide covers installing the Audio Summary App using [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

## Why uv?

- **10-100x faster** than pip for installing dependencies
- **Built-in virtual environment management**
- **Lockfile support** for reproducible installations
- **Drop-in replacement** for pip and pip-tools

## Prerequisites

### 1. Install uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

### 2. System Dependencies

The app requires audio capture capabilities. Install the appropriate system dependencies:

#### macOS
```bash
# For system audio capture
brew install blackhole-2ch
# OR
brew install jack
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-dev
```

#### Windows
Download and install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)

## Installation

### Basic Installation

1. **Clone or navigate to the project directory:**
```bash
cd audio_summary_app
```

2. **Create a virtual environment and install dependencies:**
```bash
# uv will automatically create a venv and install dependencies
uv sync
```

This command:
- Creates a virtual environment (if not exists)
- Installs all dependencies from pyproject.toml
- Creates a uv.lock file for reproducible builds

3. **Activate the virtual environment:**
```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Installation with GPU Support (NVIDIA CUDA)

For faster LLM inference with CUDA support:

```bash
# Set CMAKE arguments for CUDA support
CMAKE_ARGS="-DLLAMA_CUBLAS=on" uv pip install llama-cpp-python --force-reinstall

# Or add to your environment
export CMAKE_ARGS="-DLLAMA_CUBLAS=on"
uv sync --reinstall-package llama-cpp-python
```

### Installation with Alternative Backends

**OpenAI Whisper instead of faster-whisper:**
```bash
uv sync --extra whisper-alternative
```

**Transformers + PyTorch for LLM:**
```bash
uv sync --extra transformers
```

**All extras:**
```bash
uv sync --extra all
```

### Development Installation

For development with testing and linting tools:

```bash
uv sync --extra dev
```

## Download AI Models

### 1. Speech-to-Text Model (Whisper)

The Whisper model will auto-download on first run. To manually download:

```bash
# Activate venv first
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

python -c "from faster_whisper import WhisperModel; WhisperModel('base.en')"
```

**Available models:**
- `tiny.en` (39 MB) - Fastest, lowest quality
- `base.en` (74 MB) - **Recommended for testing**
- `small.en` (244 MB) - Good balance
- `medium.en` (769 MB) - High quality
- `large-v2` (1.5 GB) - Best quality

### 2. LLM Model (for Summarization)

Download a quantized Llama model from HuggingFace:

```bash
# Create models directory
mkdir -p models
cd models

# Download Llama-2-7B-Chat (Q4 quantized, ~4GB)
# Using wget or curl
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

# Or use huggingface-cli
uv pip install huggingface-hub
huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF llama-2-7b-chat.Q4_K_M.gguf --local-dir .
```

**Recommended models:**
- Llama-2-7B-Chat Q4_K_M (~4 GB) - Good balance
- Mistral-7B-Instruct Q4_K_M (~4 GB) - Better quality
- Llama-2-13B-Chat Q4_K_M (~7 GB) - Higher quality, slower

Update `config.py` with your model path:
```python
llm_model_path = "./models/llama-2-7b-chat.Q4_K_M.gguf"
```

## Verify Installation

Run the demo (no hardware required):

```bash
# Make sure venv is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

python demo.py
```

## Running the Application

### Start the app:
```bash
python main.py
```

### Available commands:
- `start` - Begin recording and transcription
- `stop` - Stop recording and generate final summary
- `quit` - Exit the application

## Common uv Commands

### Update dependencies:
```bash
uv sync --upgrade
```

### Add a new dependency:
```bash
uv add package-name
```

### Remove a dependency:
```bash
uv remove package-name
```

### Lock dependencies (create/update uv.lock):
```bash
uv lock
```

### Install from lock file (reproducible):
```bash
uv sync --frozen
```

### Run commands without activating venv:
```bash
uv run python main.py
uv run python demo.py
```

### Show installed packages:
```bash
uv pip list
```

## Troubleshooting

### uv sync fails with compilation errors

**Issue:** llama-cpp-python fails to compile

**Solution:**
```bash
# Install build dependencies (macOS)
brew install cmake

# Install build dependencies (Linux)
sudo apt-get install build-essential cmake

# Install build dependencies (Windows)
# Download and install Visual Studio Build Tools
# https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
```

### Audio capture not working

See the main [INSTALL.md](INSTALL.md) for platform-specific audio configuration.

### Module not found errors

Ensure the virtual environment is activated:
```bash
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate      # Windows
```

Or use uv run:
```bash
uv run python main.py
```

### CUDA/GPU support not working

Verify CUDA installation:
```bash
nvidia-smi  # Should show GPU info
```

Reinstall llama-cpp-python with CUDA:
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" uv pip install llama-cpp-python --force-reinstall
```

## System Requirements

**Minimum:**
- Python 3.9+
- 4 GB RAM
- 10 GB disk space (for models)
- Dual-core CPU

**Recommended:**
- Python 3.11+
- 16 GB RAM
- 20 GB disk space
- Quad-core CPU
- NVIDIA GPU with 6+ GB VRAM (for GPU acceleration)

## Migration from pip/requirements.txt

If you have an existing installation using requirements.txt:

```bash
# Remove old venv (optional)
rm -rf venv/

# Install with uv
uv sync

# Your existing config.py and data will be preserved
```

## Next Steps

1. Configure audio devices (see [INSTALL.md](INSTALL.md))
2. Download AI models (see above)
3. Review [README.md](README.md) for usage
4. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
5. Review [DATA_FLOW.md](DATA_FLOW.md) for privacy details

## Support

For issues with:
- **uv itself:** https://github.com/astral-sh/uv/issues
- **Audio Summary App:** Create an issue in the project repository

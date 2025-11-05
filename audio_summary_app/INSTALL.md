# Installation Guide

Complete setup instructions for the Audio Summary App on all major platforms.

## Quick Install (All Platforms)

```bash
# 1. Clone or download the repository
git clone <repo-url>
cd audio_summary_app

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Download models (see platform-specific sections)

# 4. Run the demo
python demo.py

# 5. Run the app
python main.py
```

---

## Platform-Specific Setup

### Windows 10/11

#### Prerequisites
```bash
# Install Python 3.8+
# Download from: https://www.python.org/downloads/

# Install Visual C++ Redistributable (for llama-cpp)
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### System Audio Capture
**Required: VB-Audio Virtual Cable**

1. Download VB-Cable: https://vb-audio.com/Cable/
2. Install VB-CABLE_Driver_Pack43.zip
3. Set as default playback device:
   - Right-click speaker icon in taskbar
   - Open Sound settings
   - Set output to "CABLE Input"
4. Create a listening device (optional, to hear audio):
   - Sound Control Panel → Recording
   - Right-click "CABLE Output" → Properties
   - Listen tab → Check "Listen to this device"

#### Python Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For GPU support (NVIDIA only)
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

#### Model Downloads
```bash
# Create models directory
mkdir models

# Download LLM (example: Llama-2-7B)
# Visit: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
# Download: llama-2-7b-chat.Q4_K_M.gguf
# Place in: models/

# Whisper auto-downloads on first run
```

#### Running
```bash
venv\Scripts\activate
python main.py
```

---

### macOS (Intel & Apple Silicon)

#### Prerequisites
```bash
# Install Python 3.8+ via Homebrew
brew install python@3.11

# For Apple Silicon, use Python 3.10+ for better compatibility
```

#### System Audio Capture
**Required: BlackHole**

1. Install BlackHole:
   ```bash
   brew install blackhole-2ch
   ```

2. Create Multi-Output Device:
   - Open Audio MIDI Setup (Spotlight: "Audio MIDI")
   - Click "+" → Create Multi-Output Device
   - Check both "BlackHole 2ch" and your speakers
   - Right-click → "Use This Device For Sound Output"

3. Create Aggregate Device (for input):
   - Click "+" → Create Aggregate Device
   - Check "BlackHole 2ch" and your microphone
   - Use this as input device

#### Python Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For Apple Silicon, install Metal-optimized llama-cpp
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall
```

#### Model Downloads
```bash
# Create models directory
mkdir models

# Download LLM
cd models
# For Intel Macs:
wget https://huggingface.co/.../llama-2-7b-chat.Q4_K_M.gguf

# For Apple Silicon (M1/M2/M3):
# Use Metal-optimized models when available
# Or use same GGUF models (Metal acceleration automatic)
```

#### Running
```bash
source venv/bin/activate
python main.py
```

#### macOS Permissions

First run will request:
- Microphone access
- Screen recording (for system audio)

Grant both permissions in System Preferences → Security & Privacy.

---

### Linux (Ubuntu/Debian)

#### Prerequisites
```bash
# Update system
sudo apt update

# Install Python and development tools
sudo apt install python3.10 python3-pip python3-venv
sudo apt install build-essential portaudio19-dev

# Install PulseAudio (if not present)
sudo apt install pulseaudio pavucontrol
```

#### System Audio Capture
**Using PulseAudio Monitor**

1. PulseAudio automatically creates monitor sources
2. List available devices:
   ```bash
   pactl list sources
   ```

3. Find monitor sources (e.g., "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor")

4. The app will auto-detect monitor sources

Optional GUI tool:
```bash
# Install PulseAudio Volume Control
sudo apt install pavucontrol

# Run to see all audio devices
pavucontrol
```

#### Python Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For CUDA support (NVIDIA GPU)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

#### Model Downloads
```bash
# Create models directory
mkdir -p models

# Download LLM
cd models
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

# Whisper auto-downloads
```

#### Running
```bash
source venv/bin/activate
python main.py
```

#### Permissions

If permission errors occur:
```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Log out and back in for changes to take effect
```

---

### Linux (Arch/Manjaro)

```bash
# Install dependencies
sudo pacman -S python python-pip base-devel portaudio

# Install PulseAudio if using
sudo pacman -S pulseaudio pavucontrol

# Rest same as Ubuntu instructions above
```

---

### Linux (Fedora/RHEL)

```bash
# Install dependencies
sudo dnf install python3 python3-pip gcc portaudio-devel

# Install PulseAudio
sudo dnf install pulseaudio pavucontrol

# Rest same as Ubuntu instructions above
```

---

## Model Selection Guide

### Speech-to-Text (Whisper)

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| tiny.en | 39 MB | ~1 GB | ⚡⚡⚡⚡ | ⭐⭐ | Testing |
| base.en | 74 MB | ~1 GB | ⚡⚡⚡ | ⭐⭐⭐ | **Recommended** |
| small.en | 244 MB | ~2 GB | ⚡⚡ | ⭐⭐⭐⭐ | Better quality |
| medium.en | 769 MB | ~5 GB | ⚡ | ⭐⭐⭐⭐⭐ | Best quality |

**Recommended**: `base.en` - Good balance of speed and quality

### LLM (Summarization)

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| Llama-2-7B Q4 | 4 GB | 6 GB | ⚡⚡⚡ | ⭐⭐⭐ | **Recommended** |
| Llama-2-7B Q5 | 5 GB | 7 GB | ⚡⚡ | ⭐⭐⭐⭐ | Better quality |
| Mistral-7B Q4 | 4 GB | 6 GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | More concise |
| Llama-2-13B Q4 | 8 GB | 10 GB | ⚡ | ⭐⭐⭐⭐⭐ | Best quality |

**Recommended**: `Llama-2-7B-Chat Q4` - Good summaries, runs on most hardware

### Download Links

**Whisper** (auto-downloads):
- Will download on first run
- Or download manually: https://huggingface.co/Systran/faster-whisper-base.en

**LLMs** (manual download):
- Llama-2-7B: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
- Mistral-7B: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF

---

## Verification

### Test Installation

```bash
# 1. Check Python
python --version
# Should be 3.8 or higher

# 2. Check dependencies
pip list | grep -E "sounddevice|faster-whisper|llama"

# 3. List audio devices
python -c "import sounddevice as sd; sd.query_devices()"

# 4. Run demo
python demo.py
```

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'sounddevice'`
```bash
# Solution
pip install sounddevice
```

**Issue**: `FileNotFoundError: Model not found`
```bash
# Solution: Download model to models/ directory
# Or update config.py with correct path
```

**Issue**: No system audio captured
```bash
# Windows: Install VB-Cable
# macOS: Create Multi-Output Device
# Linux: Check PulseAudio monitors
```

**Issue**: Slow transcription
```bash
# Solution: Use smaller model (tiny.en or base.en)
# Or enable GPU acceleration
```

---

## GPU Acceleration

### NVIDIA CUDA

```bash
# Install CUDA Toolkit
# Download from: https://developer.nvidia.com/cuda-downloads

# Reinstall llama-cpp with CUDA
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

### Apple Silicon (Metal)

```bash
# Automatically enabled on M1/M2/M3 Macs
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall
```

### AMD ROCm (Linux)

```bash
# Install ROCm
# Visit: https://rocm.docs.amd.com/

# Compile with ROCm support
CMAKE_ARGS="-DLLAMA_HIPBLAS=on" pip install llama-cpp-python --force-reinstall
```

---

## Docker Installation

For easier deployment:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    build-essential \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
# Build
docker build -t audio-summary-app .

# Run with audio access
docker run -it --device /dev/snd audio-summary-app
```

---

## Post-Installation

### Configure Settings

Edit `config.py`:
```python
class Config:
    # Choose your models
    stt_model_path = "base.en"  # or path to downloaded model
    llm_model_path = "./models/llama-2-7b-chat.Q4_K_M.gguf"
    
    # Adjust intervals
    summary_interval = 300  # seconds (5 minutes)
    chunk_duration = 300    # seconds per chunk
```

### First Run

```bash
python main.py

# Commands:
# > start  # Begin recording
# > stop   # Generate summary
# > quit   # Exit
```

---

## Troubleshooting

### Get Help

```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test microphone
python -c "import sounddevice as sd; import numpy as np; sd.rec(int(3*16000), 16000, 1); sd.wait()"

# Check PulseAudio (Linux)
pactl list sources

# Check permissions (macOS)
# System Preferences → Security & Privacy → Privacy
```

### Support Resources

- GitHub Issues: (your repo)
- Whisper Docs: https://github.com/openai/whisper
- Llama.cpp: https://github.com/ggerganov/llama.cpp
- sounddevice: https://python-sounddevice.readthedocs.io/

---

## Next Steps

1. Run `python demo.py` to see the workflow
2. Configure `config.py` for your hardware
3. Start `python main.py` and test recording
4. Customize prompts in `summarizer.py` if needed

Enjoy your privacy-focused audio summarization! 🎉

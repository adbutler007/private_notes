# Audio Summary App - Quick Setup Guide

A privacy-focused app that captures audio, transcribes it using **Whisper**, and generates summaries using **Ollama** - all running locally on your Mac or Windows PC.

## Prerequisites

- Python 3.9 or later
- 8GB+ RAM recommended
- Internet connection (for initial model downloads only)

## Installation (5 minutes)

### Step 1: Install Ollama

Ollama provides the LLM for summarization and runs completely locally.

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download and install from [ollama.com/download](https://ollama.com/download)

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull the Qwen3 Model

```bash
ollama pull qwen3:1.7b
```

This downloads a 1.1GB language model optimized for speed and quality.

### Step 3: Install Python Dependencies

**Using uv (recommended - faster):**
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to project directory
cd audio_summary_app

# Install dependencies (creates venv automatically)
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

**Using pip (traditional):**
```bash
# Navigate to project directory
cd audio_summary_app

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate    # macOS/Linux
# or
venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Audio Capture

Audio capture requires system-specific setup to record both your microphone and system audio.

#### macOS

Install BlackHole for system audio capture:
```bash
brew install blackhole-2ch
```

Then configure in System Settings:
1. Go to **System Settings → Sound**
2. Create a **Multi-Output Device** in Audio MIDI Setup
3. Include both your speakers and BlackHole 2ch

#### Windows

1. Download [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
2. Install and restart
3. Set VB-Cable as your default playback device (or use as monitor)

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-dev pulseaudio
```

Configure PulseAudio to create monitor sources (usually enabled by default).

### Step 5: Verify Installation

Run the demo (no audio hardware required):
```bash
python demo.py
```

You should see:
- Mock transcription being generated
- Rolling summaries being created
- A final summary saved to `./demo_output/`

## First Run

### Start the Application

```bash
python main.py
```

On first run, Whisper will automatically download the speech recognition model (~140MB for base model).

### Commands

Once running, use these commands:
- `start` - Begin recording and transcription
- `stop` - Stop recording and generate final summary
- `quit` - Exit the application

### Example Session

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

## Configuration

Edit [config.py](config.py) to customize:

```python
class Config:
    # Audio Settings
    sample_rate: int = 16000  # 16kHz for speech
    channels: int = 1         # Mono audio

    # Transcription (Whisper)
    stt_model_path: str = "base"  # Options: tiny, base, small, medium, large

    # Summarization (Ollama)
    llm_model_name: str = "qwen3:1.7b"  # Or: llama3.2:3b, phi3:3.8b

    # Summary Settings
    summary_interval: int = 300  # Generate rolling summary every 5 minutes
    output_dir: str = "./summaries"
```

### Model Options

**Whisper models** (auto-downloaded on first use):
- `tiny` (39 MB) - Fastest, lower accuracy
- `base` (74 MB) - **Recommended** - Good balance
- `small` (244 MB) - Better accuracy
- `medium` (769 MB) - High accuracy
- `large` (1.5 GB) - Best accuracy

**Ollama models** (must pull separately):
- `qwen3:1.7b` (1.1 GB) - **Recommended** - Fast and efficient
- `llama3.2:3b` (2 GB) - Better quality
- `phi3:3.8b` (2.3 GB) - Good reasoning
- `gemma2:2b` (1.6 GB) - Fast alternative

To use a different model:
```bash
ollama pull llama3.2:3b
```

Then update `config.py`:
```python
llm_model_name: str = "llama3.2:3b"
```

## How It Works

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

**Privacy Features:**
- ✅ Audio streams directly to transcription (never saved)
- ✅ Transcripts stored only in RAM
- ✅ All AI processing happens locally
- ✅ No cloud services or API calls
- ✅ Only final summaries are saved to disk

## Troubleshooting

### Ollama Connection Error

Make sure Ollama is running:
```bash
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve
```

On macOS/Windows, Ollama usually runs as a background service after installation.

### Whisper Model Download Fails

If the initial download fails, manually download:
```bash
python -c "import whisper; whisper.load_model('base')"
```

### Audio Capture Not Working

**Check available audio devices:**
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

**macOS:** Ensure BlackHole is installed and Multi-Output Device is configured

**Windows:** Make sure VB-Cable is set as a recording device

**Linux:** Check PulseAudio is running: `pulseaudio --check`

### Import Errors

Make sure the virtual environment is activated:
```bash
source .venv/bin/activate  # or venv/bin/activate
```

### Out of Memory

If you get memory errors:
- Use a smaller Whisper model: `stt_model_path = "tiny"`
- Use a smaller Ollama model: `llm_model_name = "qwen3:1.7b"`
- Reduce buffer size in config: `max_buffer_size = 1000`

### Slow Performance

**For faster transcription:**
- Use GPU if available (Whisper will auto-detect CUDA)
- Use smaller model: `tiny` or `base`

**For faster summarization:**
- Use smaller Ollama model: `qwen3:1.7b`
- Reduce summary frequency: `summary_interval = 600` (10 minutes)

## System Requirements

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
- GPU (optional, for faster Whisper transcription)

## What Gets Saved?

**Saved to Disk:**
- ✅ Final summaries only (in `./summaries/`)
- ✅ Each summary is 2-5 KB of text

**Never Saved:**
- ❌ Raw audio data
- ❌ Audio recordings
- ❌ Transcripts
- ❌ Intermediate summaries

## Use Cases

- 📝 Meeting notes and summaries
- 🎓 Lecture transcription and summaries
- 🎤 Interview documentation
- 🏥 Confidential discussions (HIPAA-friendly, all local)
- 🔬 Research interviews
- ♿ Accessibility support
- 📓 Voice journaling

## Next Steps

1. ✅ Run `python demo.py` to verify setup
2. ✅ Run `python main.py` to start the app
3. ✅ Test with a short recording
4. ✅ Review summary in `./summaries/`
5. ✅ Customize config if needed

## Additional Documentation

- [README.md](README.md) - Full documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [DATA_FLOW.md](DATA_FLOW.md) - Privacy architecture
- [INSTALL_UV.md](INSTALL_UV.md) - Detailed uv installation
- [UV_MIGRATION.md](UV_MIGRATION.md) - Migration from pip

## Getting Help

If you encounter issues:
1. Check this setup guide
2. Review [Troubleshooting](#troubleshooting) section
3. Check [INSTALL.md](INSTALL.md) for detailed platform setup
4. Verify Ollama is running: `ollama list`
5. Test with demo: `python demo.py`

## Privacy & Security

- 🔒 **100% Local Processing** - No data leaves your computer
- 🔒 **No Cloud APIs** - Everything runs on-device
- 🔒 **Minimal Disk Usage** - Only summaries saved
- 🔒 **Open Source** - Inspect the code yourself
- 🔒 **No Telemetry** - No tracking or analytics

---

**Ready to start? Run:**
```bash
python main.py
```

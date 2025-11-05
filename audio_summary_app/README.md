# Audio Summary App

A privacy-focused desktop application that captures audio (both microphone input and system output), transcribes it in real-time, and generates intelligent summaries using on-device AI models. 

## 🔒 Privacy First

- **No data saved to disk** except final summaries
- **No cloud services** - all processing happens locally
- Audio streams directly to transcription (never written to files)
- Transcripts kept only in RAM buffer
- You control what gets saved

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Audio Summary App                       │
└─────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐     ┌───────────┐
    │  Audio    │      │Transcript │     │    Map    │
    │  Capture  │─────▶│  Buffer   │────▶│  Reduce   │
    │  Manager  │      │(In Memory)│     │Summarizer │
    └───────────┘      └───────────┘     └───────────┘
         │                                      │
         │ (Audio never                        │
         │  saved to disk)                     ▼
         │                              ┌────────────┐
         ▼                              │  Summary   │
    ┌──────────┐                       │   File     │
    │Streaming │                       │ (Saved)    │
    │   STT    │                       └────────────┘
    └──────────┘
    (On-device)
```

### Components

1. **Audio Capture Manager** (`audio_capture.py`)
   - Captures microphone input (what you say)
   - Captures system audio output (what you hear)
   - Streams audio directly to processing pipeline
   - Audio data never touches disk

2. **Streaming Transcriber** (`transcriber.py`)
   - On-device speech-to-text using Whisper
   - Processes audio chunks in real-time
   - No audio files created

3. **Transcript Buffer** (`transcript_buffer.py`)
   - In-memory circular buffer (deque)
   - Automatically discards old segments
   - Organizes into chunks for summarization
   - Cleared after summary generation

4. **Map-Reduce Summarizer** (`summarizer.py`)
   - **MAP**: Summarizes individual time chunks
   - **REDUCE**: Combines summaries into final overview
   - Uses local LLM (Llama, etc.)
   - Only summaries are saved to disk

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Download models (first time only)
# Whisper will auto-download on first run
# Download an LLM model (e.g., Llama-2-7B-Chat GGUF)
```

### Model Setup

1. **Whisper (STT)**: Auto-downloads or specify path in config
   - Default: `base.en` (74MB, good balance)
   - Options: `tiny.en`, `small.en`, `medium.en`, `large-v2`

2. **LLM (Summarization)**: Download GGUF model
   ```bash
   mkdir models
   # Download from HuggingFace, e.g.:
   # https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
   ```

### System Audio Capture Setup

**Windows:**
- Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
- Set as default playback device

**macOS:**
- Install [BlackHole](https://github.com/ExistentialAudio/BlackHole)
- Create Multi-Output Device in Audio MIDI Setup

**Linux:**
- PulseAudio: Monitor sources available by default
- Or use JACK for more control

### Running

```bash
python main.py
```

Commands:
- `start` - Begin recording
- `stop` - Stop recording and generate summary
- `quit` - Exit application

## 💡 How It Works

### Flow

1. **User starts recording**
   - Audio streams begin (mic + system audio)
   - Real-time transcription starts

2. **During recording**
   - Audio → STT → Transcript buffer (RAM only)
   - Every 5 minutes: Generate rolling summary (MAP phase)
   - Rolling summaries stored in memory

3. **User stops recording**
   - Final REDUCE phase combines all summaries
   - One comprehensive summary generated
   - Summary saved to `./summaries/summary_TIMESTAMP.txt`
   - All buffers cleared from memory

4. **After recording**
   - No audio files on disk
   - No transcript files on disk
   - Only the summary exists

### Map-Reduce Summarization

```
Transcript Stream (5 min chunks)
    │
    ├─▶ Chunk 1 ──▶ Summary 1 ┐
    │                          │
    ├─▶ Chunk 2 ──▶ Summary 2 ├──▶ Final Summary
    │                          │     (saved to disk)
    ├─▶ Chunk 3 ──▶ Summary 3 ┐
    │                          
    └─▶ Chunk N ──▶ Summary N ┘

    (MAP phase)      (REDUCE phase)
```

Benefits:
- Handles arbitrarily long recordings
- Maintains context across conversation
- More accurate than single-pass summarization
- Efficient memory usage

## 🔧 Configuration

Edit `config.py` to customize:

```python
class Config:
    sample_rate = 16000        # Audio quality
    max_buffer_size = 2000     # Max segments in memory
    chunk_duration = 300       # Seconds per chunk (5 min)
    stt_model_path = "base.en" # Whisper model
    llm_model_path = "./models/llama-2-7b-chat.Q4_K_M.gguf"
    summary_interval = 300     # Summary frequency
    output_dir = "./summaries" # Where to save summaries
```

## 📊 Performance

### Model Sizes vs. Speed

| Whisper Model | Size   | Speed (RTF) | Quality |
|--------------|--------|-------------|---------|
| tiny.en      | 39 MB  | ~0.1x       | Fair    |
| base.en      | 74 MB  | ~0.3x       | Good    |
| small.en     | 244 MB | ~0.7x       | Better  |
| medium.en    | 769 MB | ~2.0x       | Great   |

RTF = Real-time factor (1.0 = real-time, <1.0 = faster than real-time)

### LLM Recommendations

- **Fast**: Llama-2-7B-Chat (Q4 quantized) - ~4GB RAM
- **Better**: Mistral-7B (Q5 quantized) - ~5GB RAM
- **Best**: Llama-2-13B-Chat (Q4 quantized) - ~8GB RAM

## 🎯 Use Cases

- **Meeting Notes**: Record and summarize calls/meetings
- **Lecture Summaries**: Capture key points from talks
- **Interview Transcription**: Document conversations
- **Research**: Analyze spoken content
- **Accessibility**: Real-time captions + summaries
- **Personal Journal**: Summarize voice memos

## 🛡️ Privacy & Security

### What's NOT Saved

- ❌ Raw audio recordings
- ❌ Audio files of any kind
- ❌ Full transcripts
- ❌ Temporary buffers
- ❌ Any personal identifiers

### What IS Saved

- ✅ Text summaries only
- ✅ Timestamp of summary generation
- ✅ Metadata (duration, chunk count)

### Why This Matters

- HIPAA/GDPR friendly (audio not persisted)
- Safe for confidential meetings
- Minimal storage footprint
- Complete local processing
- No internet required

## 🔌 Advanced Usage

### Custom LLM Backend

Replace `MockLLM` in `summarizer.py`:

```python
from llama_cpp import Llama

class RealLLM:
    def __init__(self, model_path):
        self.model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=4,
            n_gpu_layers=32  # GPU acceleration
        )
```

### Different STT Models

Use alternative backends in `transcriber.py`:

```python
# Option 1: OpenAI Whisper
import whisper
model = whisper.load_model("base")

# Option 2: Transformers
from transformers import pipeline
pipe = pipeline("automatic-speech-recognition")
```

### Integration

The app can be integrated into:
- Desktop apps (Electron, Qt)
- CLI tools
- System tray applications
- Automation workflows

## 📝 File Structure

```
audio_summary_app/
├── main.py               # Application entry point
├── audio_capture.py      # Audio input/output capture
├── transcriber.py        # Speech-to-text engine
├── transcript_buffer.py  # In-memory transcript storage
├── summarizer.py         # Map-reduce summarization
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── README.md           # This file
└── summaries/          # Output directory (summaries only)
```

## 🐛 Troubleshooting

**No system audio captured:**
- Windows: Install VB-Cable
- macOS: Install BlackHole and create aggregate device
- Linux: Check PulseAudio monitor sources

**Slow transcription:**
- Use smaller Whisper model (tiny.en or base.en)
- Enable GPU acceleration
- Reduce chunk size in config

**High memory usage:**
- Reduce `max_buffer_size` in config
- Decrease `chunk_duration`
- Use quantized models (Q4, Q5)

**Poor summary quality:**
- Use larger LLM (13B vs 7B)
- Increase summary interval for better context
- Adjust prompts in `summarizer.py`

## 🤝 Contributing

This is a prototype. Improvements welcome:
- Better audio mixing (input + output)
- GUI interface
- More LLM backends
- Language support beyond English
- Diarization (speaker identification)
- Real-time display of summaries

## 📄 License

MIT License - feel free to use and modify.

## ⚠️ Disclaimer

This app processes audio locally but does not implement encryption at rest. If you need military-grade security, add encryption to the summary output or run in a secure enclave.

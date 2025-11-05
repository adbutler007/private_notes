# Audio Summary App - Architecture Document

## System Overview

The Audio Summary App is designed with privacy and efficiency at its core. It captures, processes, and summarizes audio in real-time while ensuring that raw audio and complete transcripts never touch the disk.

## Design Principles

1. **Privacy First**: Audio and transcripts exist only in memory
2. **On-Device Processing**: No cloud services, all AI local
3. **Streaming Architecture**: Process data as it arrives
4. **Memory Efficient**: Circular buffers prevent unbounded growth
5. **Modular Design**: Components can be swapped/upgraded

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Application                         │
│                           (main.py)                              │
│  - Orchestrates all components                                   │
│  - Manages lifecycle (start/stop)                                │
│  - Coordinates threading                                         │
└───────────────┬──────────────────────────┬──────────────────────┘
                │                          │
                │                          │
    ┌───────────▼──────────┐   ┌──────────▼───────────┐
    │   Audio Capture      │   │  Configuration       │
    │   (audio_capture.py) │   │  (config.py)         │
    │                      │   │                      │
    │ • Mic input stream   │   │ • Model paths        │
    │ • System audio stream│   │ • Buffer sizes       │
    │ • Queue management   │   │ • Intervals          │
    └──────────┬───────────┘   └──────────────────────┘
               │
               │ Audio Queue
               │ (in-memory only)
               ▼
    ┌──────────────────────┐
    │  Streaming STT       │
    │  (transcriber.py)    │
    │                      │
    │ • Whisper model      │
    │ • Audio buffering    │
    │ • On-device inference│
    └──────────┬───────────┘
               │
               │ Transcript Queue
               │ (text only)
               ▼
    ┌──────────────────────┐
    │  Transcript Buffer   │
    │(transcript_buffer.py)│
    │                      │
    │ • Circular deque     │
    │ • Chunk organization │
    │ • Auto-discard old   │
    └──────────┬───────────┘
               │
               │ Chunks
               │ (structured text)
               ▼
    ┌──────────────────────┐
    │  Map-Reduce          │
    │  Summarizer          │
    │  (summarizer.py)     │
    │                      │
    │ • Chunk summaries    │
    │ • Final aggregation  │
    │ • LLM inference      │
    └──────────┬───────────┘
               │
               │ Final Summary
               │ (text only)
               ▼
    ┌──────────────────────┐
    │  File System         │
    │  (summaries/ dir)    │
    │                      │
    │ • .txt files only    │
    │ • Timestamped        │
    │ • User-controlled    │
    └──────────────────────┘
```

## Data Flow

### 1. Audio Capture Phase

```
Microphone ──┐
             ├─▶ Audio Queue ──▶ (memory only, not saved)
Speaker  ────┘
```

- Both input and output audio captured simultaneously
- Audio data placed in queue as numpy arrays
- **Critical**: Audio never written to files or temp storage
- Queue size limited to prevent memory overflow

### 2. Transcription Phase

```
Audio Queue ──▶ STT Worker ──▶ Transcript Queue
                (Whisper)
```

- Worker thread continuously processes audio chunks
- Whisper model runs on-device (CPU or GPU)
- Output: Text strings with timestamps
- **Critical**: Audio consumed and discarded after transcription

### 3. Buffering Phase

```
Transcript Queue ──▶ Transcript Buffer ──▶ Organized Chunks
                     (Circular Deque)
```

- Transcripts accumulated in circular buffer
- Automatic organization into time-based chunks
- Old segments automatically discarded when buffer full
- **Critical**: Transcripts only in RAM, never disk

### 4. Summarization Phase

```
Chunks ──▶ MAP (chunk summaries) ──▶ REDUCE (final summary) ──▶ File
          (every N minutes)          (on stop)                (saved)
```

- Rolling summaries generated during recording
- Final reduce step combines all summaries
- LLM runs on-device for privacy
- **Critical**: Only the final summary saved to disk

## Threading Model

The application uses multiple threads for concurrent processing:

```
Main Thread
├── CLI/UI handling
└── Lifecycle management

Audio Capture Thread
├── Input stream callback
└── Output stream callback

Transcription Worker Thread
├── Dequeue audio chunks
├── Run Whisper inference
└── Enqueue transcripts

Summary Worker Thread
├── Dequeue transcripts
├── Accumulate for intervals
└── Generate rolling summaries
```

All threads communicate via thread-safe queues.

## Memory Management

### Circular Buffers

```python
deque(maxlen=2000)  # Automatically discards oldest
```

Benefits:
- O(1) append and pop operations
- Fixed memory footprint
- No manual cleanup needed

### Audio Buffers

```
┌────────────────────────────┐
│ Short-term accumulation    │  ← New audio
│ (1-2 seconds)              │
└────────────────────────────┘
         │
         ▼
    Transcribed & Discarded
```

### Transcript Chunks

```
┌─────┬─────┬─────┬─────┐
│Chunk│Chunk│Chunk│Chunk│ ... ← New chunks push old ones out
│  1  │  2  │  3  │  N  │
└─────┴─────┴─────┴─────┘
  ▲                    ▲
  Old              Current
```

## Privacy Architecture

### What Happens to Data

| Data Type | Location | Duration | Saved? |
|-----------|----------|----------|--------|
| Raw Audio | Audio Queue | <1 second | ❌ No |
| Audio Buffers | STT Component | 1-2 seconds | ❌ No |
| Transcripts | Transcript Buffer | Until buffer full | ❌ No |
| Chunk Text | Summarizer | Until summary generated | ❌ No |
| Rolling Summaries | Summarizer | Until final summary | ❌ No |
| Final Summary | File System | Permanent | ✅ Yes |

### Security Considerations

1. **No Temp Files**: Application never creates temporary files
2. **Memory Only**: All processing in RAM
3. **Clean Shutdown**: Buffers cleared on exit
4. **Local Models**: No data sent to external servers
5. **User Control**: Recording starts/stops explicitly

## Performance Characteristics

### CPU Usage

- Audio capture: ~2-5% (minimal, hardware-accelerated)
- STT (Whisper base): ~15-30% (single thread)
- LLM (Llama-2-7B): ~40-60% (during summarization)
- Total: ~20-40% average (spikes during summary generation)

### Memory Usage

- Base application: ~100 MB
- Whisper model (base): ~150 MB
- LLM model (7B Q4): ~4-5 GB
- Transcript buffer: ~5-10 MB
- Total: ~5-6 GB RAM required

### Disk Usage

- Models: 5-10 GB (one-time download)
- Summaries: ~1-5 KB per session
- No audio or transcript files

### Real-Time Performance

- Audio latency: <500ms
- Transcription lag: 1-3 seconds (depends on model)
- Summary generation: 5-30 seconds (depends on chunk size)

## Scalability

### Handling Long Sessions

The map-reduce architecture enables processing arbitrarily long recordings:

```
1 hour recording:
  → 12 chunks (5 min each)
  → 12 intermediate summaries
  → 1 final summary

10 hour recording:
  → 120 chunks
  → 120 intermediate summaries
  → 1 final summary (same size as 1 hour)
```

### Memory Bounds

- Transcript buffer: Fixed size (2000 segments)
- Audio queues: Limited to 100 items
- Intermediate summaries: Grows with duration, but text-only (small)

## Error Handling

### Resilience Features

1. **Audio Dropout**: Continue with available stream
2. **Transcription Errors**: Skip failed chunks, continue
3. **Model Failures**: Fallback to mock/simplified models
4. **Memory Pressure**: Aggressive buffer pruning
5. **Interruption**: Graceful shutdown, save partial summary

### Failure Modes

| Issue | Behavior | Recovery |
|-------|----------|----------|
| Mic disconnected | Continue with system audio | Auto-reconnect if available |
| System audio unavailable | Continue with mic only | Warn user |
| Whisper crash | Skip chunk, continue | Restart model |
| LLM crash | Use fallback summarization | Restart model |
| Out of memory | Reduce buffer sizes | Warn user, continue |

## Extension Points

### Swappable Components

1. **Audio Backend**
   - Current: sounddevice
   - Alternative: PyAudio, JACK, PulseAudio direct

2. **STT Engine**
   - Current: faster-whisper
   - Alternative: OpenAI Whisper, Vosk, DeepSpeech

3. **LLM Backend**
   - Current: llama-cpp-python
   - Alternative: transformers, ONNX Runtime, MLX

4. **Storage**
   - Current: Plain text files
   - Alternative: Database, encrypted storage, cloud backup

### Future Enhancements

- **GUI**: Electron or Qt-based interface
- **Diarization**: Speaker identification and separation
- **Live Display**: Real-time transcript view
- **Multi-language**: Support for non-English
- **Export Formats**: Markdown, JSON, PDF
- **Custom Prompts**: User-defined summary styles
- **Keyword Extraction**: Automatic tagging
- **Search**: Find past summaries by content

## Deployment Considerations

### Operating System Specific

**Windows**:
- Requires VB-Cable for system audio
- Visual Studio C++ runtime for some dependencies

**macOS**:
- Requires BlackHole for system audio
- Permission prompts for microphone access

**Linux**:
- PulseAudio preferred for audio routing
- May need additional audio permissions

### Hardware Requirements

**Minimum**:
- 4 GB RAM
- 10 GB disk space (models)
- Dual-core CPU
- Integrated audio

**Recommended**:
- 16 GB RAM
- 20 GB disk space
- Quad-core CPU (or better)
- NVIDIA GPU (for faster inference)

### Installation Modes

1. **Development**: Clone repo, install from requirements.txt
2. **User**: PyInstaller bundle (single executable)
3. **Container**: Docker image with pre-downloaded models

## Testing Strategy

### Unit Tests
- Each component tested independently
- Mock audio/transcript data
- Verify no disk writes (except summaries)

### Integration Tests
- End-to-end flow with simulated data
- Threading and queue behavior
- Memory leak detection

### Performance Tests
- Real-time factor for transcription
- Memory usage over long sessions
- CPU utilization profiles

## Conclusion

This architecture prioritizes privacy, efficiency, and user control. By keeping audio and transcripts in memory only and processing everything locally, users can confidently capture and summarize sensitive conversations without privacy concerns.

The modular design allows for easy customization and improvement while maintaining the core privacy guarantees.

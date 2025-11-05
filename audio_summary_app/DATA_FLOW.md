# Audio Summary App - Data Flow Diagram

## Complete System Data Flow

```
                    AUDIO SUMMARY APP - PRIVACY ARCHITECTURE
                    ========================================

HARDWARE                 PROCESSING                    STORAGE
--------                 ----------                    -------

┌──────────┐
│Microphone│
│  Input   │─┐
└──────────┘ │
             │
┌──────────┐ │         ┌─────────────────┐
│ System   │ ├────────▶│  Audio Capture  │
│  Audio   │ │         │    Manager      │
│ (Speakers│─┘         └────────┬────────┘
└──────────┘                    │
                                │ [Audio Queue]
                                │ (In Memory ONLY)
                                │ 🔒 Never Saved
                                │
                                ▼
                        ┌───────────────┐
                        │  Streaming    │
                        │     STT       │
                        │  (Whisper)    │
                        └───────┬───────┘
                                │
                                │ [Transcript Queue]
                                │ (Text Only)
                                │ 🔒 Never Saved
                                │
                                ▼
                        ┌───────────────┐
                        │  Transcript   │
                        │    Buffer     │
                        │ (Circular)    │
                        └───────┬───────┘
                                │
                                │ [Chunks]
                                │ 🔒 Never Saved
                                │
                                ▼
                        ┌───────────────┐
                        │  Map-Reduce   │
                        │  Summarizer   │
                        │   (LLM)       │
                        └───────┬───────┘
                                │
                                │ [Final Summary]
                                │ (Text Only)
                                │
                                ▼
                        ┌───────────────┐
                        │    DISK       │
                        │  📁 SAVED     │      ✅ ONLY THING SAVED!
                        │ summary.txt   │
                        └───────────────┘
```

## Memory vs. Disk: What Gets Saved?

```
DATA LIFECYCLE VISUALIZATION
============================

AUDIO STREAM
┌─────────────────────────────────────────────────────────────┐
│ 🎤 Microphone: "Hello, how are you today?"                  │
│ 🔊 Speaker:    "I'm doing well, thanks for asking!"         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                    ⚡ Processed in Memory
                    ❌ NEVER SAVED TO DISK
                          │
                          ▼
TRANSCRIPT SEGMENTS (in RAM)
┌─────────────────────────────────────────────────────────────┐
│ [00:00:01] "Hello, how are you today?"                      │
│ [00:00:03] "I'm doing well, thanks for asking!"             │
│ [00:00:05] "That's great to hear!"                          │
│ ... (more segments in circular buffer)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                    ⚡ Organized in Memory
                    ❌ NEVER SAVED TO DISK
                          │
                          ▼
INTERMEDIATE SUMMARIES (in RAM)
┌─────────────────────────────────────────────────────────────┐
│ Summary 1: "Conversation began with greetings and check-in" │
│ Summary 2: "Discussion of project status and next steps"    │
│ Summary 3: "Team coordination and task assignments"         │
│ ... (accumulated during recording)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
                    ⚡ Combined by LLM
                    🔄 One-time processing
                          │
                          ▼
FINAL SUMMARY (saved to disk)
┌─────────────────────────────────────────────────────────────┐
│ 📁 /summaries/summary_20240115_143022.txt                   │
│                                                               │
│ The conversation covered project updates, with team members  │
│ discussing current progress, upcoming milestones, and task   │
│ assignments. Key action items were identified for follow-up. │
│                                                               │
│ ✅ THIS IS THE ONLY FILE SAVED                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                    ALL BUFFERS CLEARED
                    Memory freed, ready for next session
```

## Privacy Comparison Table

```
╔══════════════════╦════════════╦═══════════╦════════════╗
║   Data Type      ║  Location  ║ Duration  ║   Saved?   ║
╠══════════════════╬════════════╬═══════════╬════════════╣
║ Raw Audio        ║ RAM Queue  ║ <1 sec    ║ ❌ Never   ║
║ Audio Buffer     ║ STT Module ║ 1-2 sec   ║ ❌ Never   ║
║ Transcripts      ║ RAM Buffer ║ Minutes*  ║ ❌ Never   ║
║ Text Chunks      ║ RAM Array  ║ Minutes*  ║ ❌ Never   ║
║ Summaries        ║ RAM Array  ║ Minutes*  ║ ❌ Never   ║
║ Final Summary    ║ Disk       ║ Permanent ║ ✅ Yes     ║
╚══════════════════╩════════════╩═══════════╩════════════╝

* Cleared after summary generation
```

## Threading Architecture

```
CONCURRENT PROCESSING THREADS
==============================

Main Thread
│
├─▶ [CLI/UI Loop]
│   ├─ Accept user commands (start/stop/quit)
│   └─ Coordinate application lifecycle
│
├─▶ [Audio Capture Thread]
│   ├─ Input stream callback  ─┐
│   ├─ Output stream callback ─┼─▶ Audio Queue (memory)
│   └─ Non-blocking capture    ─┘
│
├─▶ [Transcription Worker]
│   ├─ Dequeue audio chunks ◀──── Audio Queue
│   ├─ Run Whisper model
│   └─ Enqueue transcripts ─────▶ Transcript Queue
│
└─▶ [Summary Worker]
    ├─ Dequeue transcripts ◀──── Transcript Queue
    ├─ Accumulate text
    ├─ Generate summaries (every N minutes)
    └─ Store in memory (not disk)

    On Stop:
    └─▶ Generate final summary
        └─▶ Save to disk (only this step writes files)
```

## Map-Reduce Summarization Flow

```
MAP PHASE (Parallel Processing)
================================

Transcript Stream
│
├─▶ [Chunk 1: 0-5 min]
│   │
│   └─▶ LLM Summary 1: "Initial discussion about project goals"
│
├─▶ [Chunk 2: 5-10 min]
│   │
│   └─▶ LLM Summary 2: "Technical implementation details"
│
├─▶ [Chunk 3: 10-15 min]
│   │
│   └─▶ LLM Summary 3: "Resource allocation and timeline"
│
└─▶ [Chunk N: ...]
    │
    └─▶ LLM Summary N: "Action items and next steps"


REDUCE PHASE (Aggregation)
===========================

All Intermediate Summaries
│
├─ Summary 1 ┐
├─ Summary 2 ├─▶ LLM Combine ─▶ Final Summary ─▶ 💾 DISK
├─ Summary 3 │
└─ Summary N ┘
```

## Storage Architecture

```
FILE SYSTEM USAGE
=================

Application Directory
│
├── /audio_summary_app/
│   ├── main.py
│   ├── config.py
│   ├── [other .py files]
│   └── ... (code only, no data)
│
├── /models/                    ← AI Models (pre-downloaded)
│   ├── whisper_base.bin        (74 MB)
│   └── llama-2-7b-chat.gguf    (4 GB)
│
└── /summaries/                 ← OUTPUT (only thing app creates)
    ├── summary_20240115_143022.txt  (2 KB)
    ├── summary_20240115_150137.txt  (3 KB)
    └── summary_20240116_091542.txt  (2 KB)

Total App Data:
  - Models:    ~4-5 GB (one-time)
  - Summaries: ~2-5 KB per session
  - Total:     ~4 GB + (2KB × sessions)

NO AUDIO FILES ANYWHERE! 🎉
```

## Real-Time Data Size

```
MEMORY FOOTPRINT OVER TIME
==========================

         Memory Usage (MB)
         │
    6000 │           ┌─────┐ LLM loads for summary
         │           │     │
    5000 │     ┌─────┘     └───── LLM unloads
         │     │ Recording with transcript buffer
    4000 │────┐│ Models loaded
         │    ││
    3000 │    ││
         │    └┘
    2000 │   Models pre-loaded
         │ 
    1000 │ Baseline
         │
       0 └──────────────────────────────────────▶ Time
           Start  Record   Summary   Stop   Clear

Data Written to Disk Over Time:

    Disk Usage (KB)
         │
       5 │                           ┌── Summary saved (2KB)
         │                           │
       4 │                           │
         │                           │
       3 │                           │
         │                           │
       2 │                           │
         │                           │
       1 │                           │
         │                           │
       0 └───────────────────────────┴────────▶ Time
           Start  Record   Summary   Stop   Clear
           
           (Flat line until stop - no disk writes during recording!)
```

## Privacy Guarantees

```
🔒 SECURITY LAYERS
==================

Layer 1: NO NETWORK
├─ All processing on-device
├─ No API calls to external services
└─ Models run locally

Layer 2: NO DISK PERSISTENCE
├─ Audio: Streamed through memory
├─ Transcripts: RAM buffer only
└─ Only summaries written to disk

Layer 3: USER CONTROL
├─ Explicit start/stop commands
├─ User chooses when to save
└─ Summary files user-accessible

Layer 4: MEMORY CLEANUP
├─ Buffers cleared after use
├─ No residual data in RAM
└─ Clean shutdown process

Result: MAXIMUM PRIVACY ✅
```

## Comparison with Traditional Recording

```
TRADITIONAL RECORDING APP          THIS APP
========================           ========

Record ─▶ 💾 audio.wav (100 MB)   Record ─▶ 🧠 Memory only
           │                                   │
           ▼                                   ▼
       Transcribe                        Transcribe
           │                                   │
           ▼                                   ▼
       💾 transcript.txt (500 KB)        🧠 Memory only
           │                                   │
           ▼                                   ▼
       Summarize                         Summarize
           │                                   │
           ▼                                   ▼
       💾 summary.txt (2 KB)             💾 summary.txt (2 KB)

Total Disk: 100 MB + 500 KB + 2 KB   Total Disk: 2 KB
           = ~100.5 MB                           = 2 KB

PRIVACY RISK: ❌ High                PRIVACY RISK: ✅ Minimal
(Audio & transcript recoverable)     (Only summary exists)
```

---

## Legend

```
Symbols Used:
═════════════

🎤  Microphone input
🔊  Speaker output
🧠  In-memory processing
💾  Saved to disk
⚡  Fast processing
🔒  Privacy protected
❌  Never saved
✅  Saved (intentionally)
📁  File on disk
🔄  One-time processing
```

## Summary

This architecture ensures:

1. **Privacy**: Audio and transcripts never touch disk
2. **Efficiency**: Streaming processing, no file I/O overhead
3. **Scalability**: Map-reduce handles arbitrarily long sessions
4. **Control**: User decides what gets saved (only summaries)
5. **Security**: All processing local, no cloud dependencies

**Bottom line**: Your conversations stay private. Only the summary you choose to save exists on disk.

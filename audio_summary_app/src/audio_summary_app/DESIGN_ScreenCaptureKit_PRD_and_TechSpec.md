# Audio Summary – ScreenCaptureKit Architecture

This file combines the Product Requirements Document (PRD) and Technical Specification for the new Swift-oriented ScreenCaptureKit architecture.

---

## 1. Problem & Goals

### 1.1 Problem

Current Audio Summary functionality works well for:

- Live speech from the MacBook microphone (CLI and partially GUI).
- Local summarization using Parakeet/Whisper and Ollama.

However, it does **not** provide a reliable, user-friendly way to capture Zoom/Teams calls because:

- It depends on manual setup of BlackHole and Multi-Output devices in Audio MIDI Setup.
- Behavior is fragile and hard to reason about (loopback path, levels, per-app routing).
- Non-technical users cannot be expected to manage device routing and virtual drivers.

### 1.2 Primary Goal

Deliver a **menu-bar Mac app** that:

- Captures **Zoom/Teams call audio** directly via ScreenCaptureKit.
- Streams that audio into the existing **Python STT + summarizer engine**.
- Produces accurate, privacy-preserving summaries and structured data.
- Requires **minimal or no manual audio device configuration** for end users.

### 1.3 Secondary Goals

- Allow **editing of chunk and final summary prompts** via the GUI.
- Allow selection of STT backend (Whisper vs Parakeet) for internal/test builds.
- Keep all heavy ML and transcription **fully on-device**, without cloud dependencies.

---

## 2. Target Users & Use Cases

### 2.1 Target Users

- **Primary:** Sales reps / client-facing professionals who join Zoom/Teams calls with 1–3 participants and want concise summaries and extracted data.
- **Secondary:** Sales ops, product, and power users configuring prompts, models, and data export paths.

### 2.2 Use Cases

1. **Zoom call capture + summary**
   - User joins a Zoom call.
   - Starts Audio Summary from the menu bar.
   - After the call, they receive a textual summary and structured JSON, with optional CSV logging.

2. **Teams call capture + summary**
   - Same as above, with Microsoft Teams.

3. **Prompt customization**
   - Sales ops edits the **chunk summary prompt** (MAP) and **final summary prompt** (REDUCE) via GUI.
   - Changes apply to subsequent calls for that user.

4. **Mic-only fallback**
   - If ScreenCaptureKit is unavailable or denied, app falls back to laptop mic capture and clearly labels those runs as "Mic only".

---

## 3. High-Level Solution

### 3.1 Architecture Overview

Two main components:

1. **Swift macOS menu-bar app (GUI + capture)**
   - Owns:
     - ScreenCaptureKit integration (Zoom/Teams app audio capture).
     - macOS permissions (Screen Recording / optional mic).
     - System tray UI (Start/Stop, Settings, Prompts, Recent Summaries).
     - Status and notifications.

2. **Python "engine" service**
   - Owns:
     - Audio ingestion (PCM chunks from Swift).
     - STT (Whisper/Parakeet) with proper resampling.
     - Transcript buffering and map-reduce chunking.
     - Summarization and structured data extraction via Ollama.
     - Saving summaries, JSON, and CSV.

These components communicate via **HTTP over localhost**.

- Engine binds to `127.0.0.1:PORT`.
- Swift app uses `URLSession` to send JSON requests (`start_session`, `audio_chunk`, `stop_session`).

### 3.2 Key Design Choices

- **Swift for macOS-specific responsibilities**: ScreenCaptureKit, entitlements, menu bar UI.
- **Python as a local service**: engine is independent and testable; GUI is a thin controller.
- **HTTP/localhost IPC**: simple, debuggable, secure on a single machine.
- **No BlackHole / manual device wiring**: all capture uses ScreenCaptureKit or mic.

### 3.3 Code Reuse vs. New Code

- **Reuse (Python engine – keep and extend)**
  - Reuse current modules in `audio_summary_app/src/audio_summary_app/`:
    - `transcriber.py` (Whisper/Parakeet + resampling).
    - `transcript_buffer.py`.
    - `summarizer.py` (MapReduce + prompts + Ollama).
    - `config.py` (prompts, model names, output paths).
    - `ollama_manager.py`.
  - Add a thin HTTP layer to expose `/health`, `/start_session`, `/audio_chunk`, and `/stop_session`.

- **De-prioritize / eventually retire**
  - Treat the existing Qt/PyInstaller GUI as legacy:
    - `gui/app.py`, `gui/settings_window.py`, `gui/recording_controller.py`, etc.
    - PyInstaller build scripts and casks targeting the Qt GUI.
  - Keep them in the repo initially but do not ship in the new architecture.

- **New code (Swift GUI)**
  - Add a new Swift macOS project under this repo, e.g.:
    - `audio_summary_app/macos_gui/AudioSummaryGUI.xcodeproj`.
  - This project is the only GUI we ship going forward.

---

## 4. Functional Requirements

### 4.1 Menu-Bar GUI (Swift)

**FR1 – Status bar app**

- App runs as a menu-bar app (`LSUIElement = true`).
- Status bar icon states:
  - Idle.
  - Recording.
  - Error (optional).
- Menu items:
  - `Start Recording` / `Stop Recording` (toggle).
  - `Settings…`
  - `Recent Summaries` (submenu with last 5 calls).
  - `Quit`.

**FR2 – First-run wizard**

On first launch or until successfully completed:

1. **Welcome Screen**
   - Explain what Audio Summary does and reassure that audio stays local.

2. **Select Capture App**
   - Enumerate available apps/windows with ScreenCaptureKit.
   - Highlight Zoom and Microsoft Teams if found.
   - Allow manual selection of another app/window for testing.

3. **Permissions**
   - Trigger ScreenCaptureKit permission prompts (screen/audio capture) if necessary.
   - Provide inline guidance if the user must enable permissions in System Settings.

4. **Audio Test**
   - Start a short ScreenCaptureKit audio capture from the selected app.
   - Show a live volume meter (RMS/peak).
   - Show a "We hear your call audio" confirmation if levels exceed a configurable threshold.

- Store a persistent flag (`first_run_completed = true`) when wizard succeeds.

**FR3 – Start/Stop Recording**

- On **Start Recording**:
  - Ensure engine is running (`GET /health`). If not, spawn engine process.
  - Issue `POST /start_session` with:
    - `session_id` (UUID v4).
    - Selected STT backend and model.
    - Current prompts and export settings.
  - Start ScreenCaptureKit audio-only stream for the selected app.
  - Begin feeding PCM chunks via `POST /audio_chunk` calls.
  - Update status icon to recording.
  - Show notification: "Recording Zoom/Teams audio".

- On **Stop Recording**:
  - Stop ScreenCaptureKit stream.
  - Issue `POST /stop_session`.
  - Show "Processing…" until engine responds.
  - On success:
    - Show notification: "Summary ready".
    - Update Recent Summaries list.

**FR4 – Settings UI**

Sections:

1. **Capture**
   - Label: "Capturing from: [App Name / Window Title]".
   - Button: `Re-run Audio Setup Wizard…` to re-select app and revalidate audio.

2. **Models**
   - STT backend dropdown (internal builds): `whisper` (default), `parakeet` (optional/experimental).
   - Whisper model dropdown: `tiny`, `small`, `medium`, `large`, `turbo`.
   - Parakeet model dropdown (if enabled): `v3`, `v2`.
   - LLM model dropdown: `qwen3:4b-instruct` (default), `llama3.2:3b`, etc.

3. **Prompts**
   - Multi-line text area: **Chunk Summary Prompt** (MAP).
   - Multi-line text area: **Final Summary Prompt** (REDUCE).
   - `Reset to Defaults` button.

4. **Export**
   - Output directory selector (default: `~/Documents/Meeting Summaries`).
   - CSV path (default: `~/Documents/Meeting Summaries/meetings.csv`).
   - Checkbox: `Append calls to CSV`.

5. **Advanced**
   - Checkbox: `Enable debug logging (~/Library/Logs/Audio Summary/last.log)`.
   - Checkbox: `Allow mic fallback if app capture fails`.

**FR5 – Recent Summaries menu**

- Menu `Recent Summaries` shows the 5 most recent calls:
  - Label uses: `YYYY-MM-DD HH:MM – <Company> – <Contact>`, falling back to timestamp only.
- Clicking an item opens `summary.txt` in the default editor.

### 4.2 Engine Service (Python)

**FR6 – Process lifecycle**

- Engine is a standalone Python process that can be started:
  - Manually (for development), or
  - Automatically by the Swift app when `GET /health` fails.

- Swift tracks engine status via periodic `GET /health`.

**FR7 – HTTP API**

- Bind address: `127.0.0.1` only. Binding to any other address is considered a configuration error.
- Port: configurable, default `8756`.

Endpoints:

1. `GET /health`
   - Response:
     ```json
     {
       "status": "ok",
       "engine_version": "1.0.0",
       "api_version": "1",
       "stt_backends": ["whisper", "parakeet"],
       "llm_models": ["qwen3:4b-instruct", "llama3.2:3b"]
     }
     ```

2. `POST /start_session`

   - Request:
     ```json
     {
       "session_id": "uuid4",
       "model": "whisper",           // or "parakeet"
       "sample_rate": 16000,
       "user_settings": {
         "chunk_summary_prompt": "...",
         "final_summary_prompt": "...",
         "llm_model_name": "qwen3:4b-instruct",
         "output_dir": "~/Documents/Meeting Summaries",
         "csv_export_path": "~/Documents/Meeting Summaries/meetings.csv",
         "append_csv": true
       }
     }
     ```
   - Behavior:
     - If another session is already active and concurrent sessions are not allowed (default behavior), return `409` with `error_code: "SESSION_ALREADY_ACTIVE"`.
     - Otherwise, initialize per-session structures:
       - STT backend (Whisper/Parakeet) via a factory.
       - TranscriptBuffer.
       - MapReduceSummarizer with provided prompts.
     - Create any required directories (output, CSV) with tilde expansion.
   - Response on success: `{"status": "ok"}`.

3. `POST /audio_chunk`

   - Request:
     ```json
     {
       "session_id": "uuid4",
       "timestamp": 1731693200.123,
       "pcm_b64": "<base64 float32 mono PCM>",
       "sample_rate": 48000
     }
     ```
   - Behavior:
     - Validate `session_id`; if unknown or stopped, return `404` with `error_code: "SESSION_NOT_FOUND"`.
     - Decode base64 to `np.ndarray` float32, 1D.
     - Use `sample_rate` to compute duration and resample as needed for the STT backend.
     - Feed into the active session’s STT buffer.
     - Optionally track `buffered_seconds` and `queue_depth` for backpressure.
   - Response example:
     ```json
     {
       "status": "ok",
       "buffered_seconds": 2.5,
       "queue_depth": 10
     }
     ```
   - If internal queues exceed a configured threshold, the engine may respond with `429` (`Too Many Requests`) and `error_code: "ENGINE_OVERLOADED"`; Swift must then slow down or drop frames according to its policy.

4. `POST /stop_session`

   - Request:
     ```json
     { "session_id": "uuid4" }
     ```
   - Behavior:
     - If session does not exist or is already stopped:
       - Either return `404` with `error_code: "SESSION_NOT_FOUND"`, or treat as idempotent and return `200` with `status: "already_stopped"` (implementation must choose and stay consistent).
     - For a running session:
       1. Call `transcriber.flush_buffer()` and feed any final transcript text into `TranscriptBuffer.add(...)`.
       2. Call `TranscriptBuffer.force_finalize_chunk()`.
          - If non-empty, call `MapReduceSummarizer.summarize_chunk(chunk_text)` and store via `add_intermediate_summary`.
       3. If `intermediate_summaries` is still empty, perform low-content analysis:
          - Use `TranscriptBuffer.get_full_transcript()` to compute total characters/words.
          - If below configured thresholds and dominated by filler phrases (e.g., repeated "thank you"):
            - Set `session_status = "insufficient_content"`.
            - Prepare a canned summary like: "No usable call audio was captured from the target app. Please check your capture configuration."
       4. If `intermediate_summaries` is non-empty or `session_status != "insufficient_content"`:
          - Call `generate_final_summary()`.
       5. Call `extract_structured_data(data_extraction_prompt)` to produce `MeetingData` JSON.
       6. Write `summary.txt` and `data.json` to `output_dir`.
       7. Append a CSV row to `csv_export_path` if `append_csv = true`.
   - Response:
     ```json
     {
       "status": "ok",
       "summary_path": "...",
       "data_path": "...",
       "csv_path": "...",
       "session_status": "completed"   // or "insufficient_content"
     }
     ```

#### 4.2.1 Error Model

- All endpoints must use HTTP status codes:
  - `200` for success.
  - `400` for malformed input (missing fields, invalid types).
  - `401` for unauthorized access if an engine auth token is enabled.
  - `404` for unknown `session_id`.
  - `409` for conflicting operations (e.g., session already active).
  - `429` for backpressure/overload.
  - `500` for internal errors.

- Error responses must use a unified JSON structure:

  ```json
  {
    "status": "error",
    "error_code": "SESSION_NOT_FOUND",
    "message": "Session abc not found",
    "details": {"hint": "Start a new session via /start_session"}
  }
  ```

#### 4.2.2 Audio Format Contract

- `/audio_chunk` uses the following audio contract:
  - `pcm_format`: `"f32_mono"` (float32, mono).
  - `sample_rate`: provided per chunk; default 48000.
  - `range`: `[-1.0, 1.0]`.

- Engine must:
  - Validate that `sample_rate` is positive and reasonable (e.g., 8k–96k).
  - Resample from capture rate to model rate as needed for **both** Whisper and Parakeet.
  - Derive durations from the capture `sample_rate`, not the model rate.

### 4.2.3 STT Backend Factory & Modes

- `/start_session.user_settings.model` must be one of: `"whisper"`, `"parakeet"`.
- Engine must instantiate a backend through a factory:

  ```py
  def create_transcriber(backend: str, cfg: Config, mode: str) -> BaseTranscriber:
      ...
  ```

- Engine runtime mode:
  - `mode = "prod"` (default for shipped builds):
    - Mock STT/LLM backends are **not allowed**.
    - If MLX or Ollama are unavailable, engine must return a clear `500` error (e.g., `STT_BACKEND_UNAVAILABLE`).
  - `mode = "dev"` (development/testing):
    - Mock STT/LLM are permitted for local demos.

### 4.3 Audio Processing Behavior (FR8)

- STT backends (Whisper and Parakeet):
  - Must accept capture `sample_rate` and resample to the model's internal rate.
  - Must use the same interface (`transcribe`, `flush_buffer`).

- Summarization:
  - Use MapReduceSummarizer with GUI-provided prompts.
  - For short sessions with no periodic summaries, create a chunk summary from the final buffer before calling `generate_final_summary`.

- Low-content guard:
  - Engine must detect if content is below configured thresholds and dominated by filler, and mark session as `"insufficient_content"` as described in `POST /stop_session`.

---

## 4.3 Non-Functional Requirements

**NFR1 – Performance**

- Must handle calls up to 2 hours without falling behind by more than ~10–15 seconds.
- CPU/RAM:
  - Target Apple Silicon with 16 GB RAM as baseline.
  - Provide option to switch STT model (e.g., Whisper tiny) for lower-spec machines.

**NFR2 – Security & Privacy**

- All audio and summaries processed **locally**.
- Engine must bind only to `127.0.0.1`; binding to any other address is an error.
- Optionally support an engine auth token:
  - A random token passed by Swift when starting the engine.
  - Sent as `X-Engine-Token` header on all HTTP requests.
  - Engine rejects requests missing/invalid token with `401` and `error_code: "UNAUTHORIZED"`.
- Logs must not store raw audio or full transcripts in production; only metadata (durations, counts, IDs).

**NFR3 – Reliability**

- Engine should:
  - Recover cleanly if restarted between calls.
  - Reject `audio_chunk` for unknown or stopped sessions.
- GUI:
  - Must detect engine unavailability and show a clear error with instructions.

**NFR4 – Observability**

- Engine logs (per session):
  - Start/stop times.
  - STT backend and model.
  - Summary length and structured data counts.
  - Error codes and stack traces.

- GUI logs:
  - App selection.
  - Permission status.
  - Capture start/stop events.
  - Engine health/connection status.

In production mode, neither engine nor GUI logs may include transcript text or prompts.

---

## 5. Dependencies

- macOS 12+ (Monterey) with ScreenCaptureKit (prefer 13+).
- Xcode (latest stable) for Swift and entitlements.
- Python 3.11 (as used by existing engine).
- MLX / parakeet_mlx and/or mlx_whisper for STT.
- Ollama for LLM summarization (already used).

---

## 6. Risks & Mitigations

- **ScreenCaptureKit permissions**
  - Risk: Users deny screen/audio capture; app cannot attach to Zoom/Teams.
  - Mitigation: First-run wizard with clear guidance; graceful fallback to mic-only mode with clear labeling.

- **Wrong app/window selected**
  - Risk: User picks the wrong window; app captures the wrong audio.
  - Mitigation: Clearly label candidate windows with app name and title; pre-select Zoom/Teams meeting windows when possible.

- **High CPU/RAM usage**
  - Risk: Long calls with large models consume too many resources.
  - Mitigation: Chunked map-reduce summarization, optional smaller STT models, and guidance on hardware requirements.

- **Version skew between GUI and engine**
  - Risk: GUI and engine protocols diverge.
  - Mitigation: Include `api_version` in `/health` and enforce compatibility in the GUI.

---

## 7. Implementation Plan

**Phase 1 – Engine API & CLI harness**

- Implement `/health`, `/start_session`, `/audio_chunk`, `/stop_session` in Python.
- Add a small CLI harness that reads PCM from a file and sends it over HTTP, to validate the API.

**Phase 2 – Swift ScreenCaptureKit prototype**

- Create a minimal Swift app (non-menu-bar at first) that:
  - Lists apps/windows.
  - Lets user pick Zoom/Teams.
  - Captures audio via ScreenCaptureKit.
  - Sends chunks to engine and prints engine responses.

**Phase 3 – Full menu-bar integration**

- Convert prototype to NSStatusItem-based app.
- Implement Settings, Recent Summaries, notifications.
- Wire Start/Stop to ScreenCaptureKit and engine API.

**Phase 4 – Hardening & packaging**

- Add mic fallback.
- Improve error handling and logging.
- Sign, notarize, and staple Swift app.
- Zip as `AudioSummary-<version>.zip` and update Homebrew cask.

---

End of document.

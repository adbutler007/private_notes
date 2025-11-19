Audio Summary – Open Issues and Fix Path (Nov 2025)

Summary of user‑visible problems, environment, mitigations attempted, and recommended next actions.

Environment
- macOS Sonoma/Sequoia on Apple Silicon
- Private Homebrew tap install (non‑notarized), PyInstaller build
- Optional system‑audio capture via BlackHole 2ch + Multi‑Output Device

Key Symptoms Observed
1) First‑run Gatekeeper block (“app is damaged”) – resolved via cask quarantine removal.
2) Notarization queue stuck “In Progress” for hours when using Apple ID auth – mitigated; long‑term plan is API key notarization.
3) Microphone permission prompt did not appear; app not listed under Privacy > Microphone – mitigated with an AVFoundation permission helper + foreground launch; finally prompted and was granted.
4) After granting mic permission, clicking Record flashes the orange mic indicator briefly, then stops; System Settings > Privacy > Microphone window opens repeatedly; no recording starts (current blocker).
5) When forcing a prompt earlier, macOS sometimes grabbed the iPhone Continuity mic instead of the Mac mic.
6) Short meetings initially produced “No content to summarize” because no transcript arrived and rolling summaries were set to 5 min.
7) Homebrew cask SHA mismatches during upgrades; occasional app bundle missing from /Applications.

Fixes Implemented to Date
- Packaging & Tap
  - Unified app name/IDs to “Audio Summary”; cask preflight + postflight `xattr -dr com.apple.quarantine`.
  - Livecheck added; tap updated to versions 0.1.0 → 0.1.4 as fixes shipped.
  - Build scripts: py2app/PyInstaller hardened, zip naming consistent, auto‑SHA print; added optional sign/notarize step.
- Audio & STT Reliability
  - Default sample rate to 48 kHz (matches macOS/BlackHole); transcribers compute timing from actual sample rate.
  - Short‑call defaults: chunk_duration=60s, summary_interval=60s.
  - Input‑channel clamp to device capability; reduced min buffer to 2s for faster STT feedback.
  - Resolved device by name as well as index; prefer user’s selected device; removed eager preference for BlackHole when a valid mic is selected.
- Mic Permission and Prompting
  - AVFoundation helper (`ensure_mic_permission`) invoked on app start to show the OS dialog.
  - “Start Recording” gated on permission; added minimal stream‑open test on current device (Mac mic preferred) to force stubborn prompts without bouncing to Settings.
  - Avoid opening System Settings automatically once permission is granted; proceed straight to recording on success.
- Routing / Diagnostics
  - Verified BlackHole path via `sounddevice` capture (afplay test produced non‑zero signal).
  - CLI path (`python -m audio_summary_app`) used to surface STT logs during debugging.

Current Status (Blocker)
- With mic permission granted and Input Device set to MacBook Air Microphone, clicking Record flashes orange mic then stops; the app brings up the Privacy > Microphone pane again even though permission exists. No audio capture begins.

Hypotheses
1) The preflight `InputStream` open still fails quickly (e.g., channel/sample‑rate mismatch or device index churn), causing early abort.
2) LSUIElement/menu‑bar launch + Qt event loop timing issue around opening streams from the GUI thread.
3) TCC state is granted, but the selected device resolves to the wrong CoreAudio device at the moment of open (e.g., Continuity/iPhone briefly steals focus), leading to an exception and our safety stop.
4) Auto‑open of System Settings persists from a residual code path (now mostly removed) or an exception handler path that still executes.

What Works Reliably
- Foreground launch of the bundle (Dock app), granting mic access at least once, then BlackHole/system‑audio capture produces measurable input and summaries when run via CLI runner.
- After prompt acceptance, saving summary files works when audio is known to reach the transcriber.

Immediate Next Actions (Proposed)
1) Add targeted logging (single‑file, user‑toggle) to capture:
   - Selected device name/index, stream open parameters (sr/channels), and any `sounddevice` exception message.
   - Whether the permission helper reports Authorized at click time.
   - Whether we route into any remaining “open Settings” code path.
   File: `~/Library/Logs/Audio Summary/last.log`.
2) Force stream open in a worker thread (not the main Qt GUI thread) with a 1–2s timeout; on success, immediately start capture using the same parameters (no second open to avoid races).
3) Add an option to temporarily disable any UI automation (no Settings launches); surface status in the tray only.
4) Expose a “Select by Name” input list in Settings and persist the human‑readable name; on startup, re‑resolve the index each time.
5) If needed, ship a minimal “Input Level” overlay for 1–2 releases to validate capture visually; remove after stability confirmed.

Notarization Track (Later)
- Use App Store Connect API key for reliable `notarytool` submits; add CI to build, sign, notarize, staple, and publish cask updates automatically.

Repro Steps (Current Blocker)
1) Launch app (mic already granted; app listed under Privacy > Microphone).
2) Settings → Audio → Input Device = “MacBook Air Microphone”, Save.
3) Click Record. Result: orange mic icon flashes then stops; Settings > Privacy > Microphone window opens; no recording begins; no files saved.

Owner Notes
- Most mitigations are in 0.1.4 local build; cask update pending once capture starts reliably from GUI without bouncing.
- Add logging and thread‑based open next, then re‑test two clean cycles.


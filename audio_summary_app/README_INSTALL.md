**Audio Summary – Install Guide (New Macs)**

- macOS: Big Sur (11.0) or newer
- Architecture: Apple Silicon (arm64)
- Distribution: Private Homebrew tap (quarantine removed automatically)

**Quick Install**
- Add tap: `brew tap adbutler007/private-notes`
- Install: `brew install --cask audio-summary`
- Launch: `open -g "/Applications/Audio Summary.app"`

Notes:
- The cask strips the macOS quarantine attribute in preflight and postflight, so Gatekeeper should not block first launch on typical machines.
- This is suitable for a private tap. For distribution outside trusted users, use a notarized build (see Advanced below).

**First Launch**
- Audio Summary runs as a menu bar app (no Dock icon).
- On first launch you should see a macOS Microphone prompt. Click OK.
- Look for the tray icon and follow the First‑Run Wizard.

**Model Setup (Once)**
- LLM via Ollama: `brew install ollama` (if not present) then `ollama pull qwen3:4b-instruct`.
- Optional system‑audio capture (Zoom/Teams): `brew install --cask blackhole-2ch`.

**Troubleshooting Gatekeeper**
- Check quarantine: `xattr -p com.apple.quarantine "/Applications/Audio Summary.app" || echo "no quarantine"`
- If you saw the Gatekeeper dialog and clicked “Cancel” (not “Move to Trash”):
  1) Remove quarantine: `xattr -dr com.apple.quarantine "/Applications/Audio Summary.app"`
  2) Launch again: `open -a "Audio Summary"` (or right‑click → Open → Open)
- If you clicked “Move to Trash”, reinstall first: `brew reinstall --cask audio-summary`
- One‑time bypass alternative: right‑click the app in Applications → Open → Open.
- If an IT policy blocks quarantine removal, use a notarized build.

**Uninstall / Clean Reinstall**
- Uninstall: `brew uninstall --cask audio-summary`
- Remove user data:
  - `rm -f  "$HOME/Library/Preferences/com.audiosummary.app.plist"`
  - `rm -rf "$HOME/Library/Application Support/Audio Summary"`
  - `rm -rf "$HOME/Library/Saved Application State/com.audiosummary.app.savedState"`
  - `rm -rf "$HOME/Documents/Meeting Summaries"`
- Fresh install: `brew install --cask audio-summary`

**Troubleshooting Microphone**
- If you don’t see the macOS Microphone prompt and the app isn’t listed in System Settings → Privacy & Security → Microphone:
  1) Quit the app.
  2) Reset any stale mic record: `tccutil reset Microphone com.audiosummary.app` then `killall coreaudiod`.
  3) Launch the executable once to trigger the prompt: `/Applications/Audio\ Summary.app/Contents/MacOS/Audio\ Summary`.
  4) From the tray menu, use “Troubleshoot Microphone…” to open the correct System Settings page.

**Advanced: Notarized Builds (Optional)**
- Not required for this private tap, but recommended for broad distribution or managed Macs.
- Signed + notarized builds avoid quarantine workarounds and always pass Gatekeeper.
- Internal workflow (already scripted in this repo):
  - Build: `audio_summary_app/build_pyinstaller.sh`
  - Apple‑ID notarization profile (works, can be slow): store via `xcrun notarytool store-credentials ...`; set `NOTARY_PROFILE` before building.
  - Organization accounts can use an App Store Connect API key for reliable notarization (see `audio_summary_app/macos/NOTARIZATION.md`).

**Requirements Recap**
- macOS 11+ on Apple Silicon, ~4 GB for the LLM model, ~1 GB for Parakeet TDT.
- Network access the first time to download models.

**Support**
- Repo: `private_notes` → `audio_summary_app/`
- Tap: `homebrew-private-notes` → `Casks/audio-summary.rb`

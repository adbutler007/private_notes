cask "audio-summary" do
  version "0.2.0"
  sha256 "7af85f78e4c6a7742b69c81fa59cccd0914a8ecdd22a577cbecdf12c4bd76102"  # Update after building: shasum -a 256 AudioSummary-#{version}.zip

  url "https://github.com/adbutler007/private_notes/releases/download/v#{version}/AudioSummary-#{version}.zip"
  name "Audio Summary"
  desc "Privacy-first audio transcription and summarization for sales calls"
  homepage "https://github.com/adbutler007/private_notes"

  livecheck do
    url :url
    strategy :github_latest
  end

  # Requires macOS 11.0+ (Big Sur) for Apple Silicon support
  depends_on macos: ">= :big_sur"
  depends_on arch: :arm64  # Apple Silicon only (MLX requirement)

  # Required dependencies
  depends_on formula: "ollama"
  depends_on formula: "uv"  # Python package manager for engine

  # Recommend BlackHole in caveats instead of a hard dependency

  app "Audio Summary.app"

  postflight do
    # Optionally remove quarantine to allow launching without notarization.
    # This is acceptable in a private tap but will be rejected in Homebrew core.
    # If you prefer to keep quarantine, install with: brew install --cask audio-summary --no-quarantine
    begin
      system_command "/usr/bin/xattr",
                     args: ["-dr", "com.apple.quarantine", "#{appdir}/Audio Summary.app"],
                     must_succeed: false
    rescue StandardError
    end

    # Install Python dependencies for the engine
    project_path = "#{Dir.home}/Projects/private_notes"
    if Dir.exist?(project_path)
      puts "Installing Python dependencies for Audio Summary engine..."
      system_command "/opt/homebrew/bin/uv",
                     args: ["sync"],
                     chdir: project_path,
                     must_succeed: false
    end

    # Show first-run instructions
    puts <<~EOS
      ====================================
      Audio Summary installed!
      ====================================

      First-time setup:

      1. Download the LLM model:
         ollama pull qwen3:4b-instruct

      2. (Optional) Install BlackHole for Zoom/Teams audio:
         brew install --cask blackhole-2ch

      3. Launch Audio Summary from Applications or menu bar

      The app will automatically start the backend engine.
      Engine logs: ~/Library/Logs/AudioSummary/engine.log

      The First-Run Wizard will guide you through setup.

      Documentation: https://github.com/adbutler007/private_notes/tree/main/audio_summary_app
    EOS
  end

  # Also strip quarantine from the staged app before it is moved, to be extra sure
  preflight do
    begin
      system_command "/usr/bin/xattr",
                     args: ["-dr", "com.apple.quarantine", "#{staged_path}/Audio Summary.app"],
                     must_succeed: false
    rescue StandardError
    end
  end

  zap trash: [
    "~/Library/Preferences/com.audiosummary.app.plist",
    "~/Library/Application Support/Audio Summary",
    "~/Documents/Meeting Summaries",
  ]

  caveats <<~EOS
    Audio Summary is a menu bar application.
    Look for the icon in your menu bar after launching.

    Privacy Note:
    - Audio and transcripts are NEVER saved to disk
    - Only summaries and structured data are persisted
    - All AI processing happens on-device (no cloud)

    Requires:
    - Ollama (installed automatically)
    - ~4GB disk space for LLM model
    - ~1GB disk space for Parakeet TDT transcription model (auto-downloads)
    - ~16GB RAM recommended (32GB optimal for M4)

    Transcription:
    - Uses NVIDIA Parakeet TDT 0.6B (~2x faster than Whisper)
    - Industry-leading 6.05% word error rate
    - Built-in punctuation and capitalization
    - Optimized for Apple Silicon (M-series chips)

    For Zoom/Teams audio capture, install BlackHole:
      brew install --cask blackhole-2ch

    If macOS Gatekeeper blocks launch and you intentionally skip notarization,
    you can install with Homebrew's no-quarantine flag instead:
      brew reinstall --cask --no-quarantine audio-summary
    Or remove quarantine manually:
      xattr -dr com.apple.quarantine "/Applications/Audio Summary.app"
  EOS
end

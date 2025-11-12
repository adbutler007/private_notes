cask "audio-summary" do
  version "0.1.0"
  sha256 "5b9336cb7ee981e3dcb6cebfbf565768fffcbb54709c2ee6519dcc484c132305"  # Update after building: shasum -a 256 AudioSummary-#{version}.zip

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

  # Recommend BlackHole in caveats instead of a hard dependency

  app "Audio Summary.app"

  postflight do
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

      The First-Run Wizard will guide you through setup.

      Documentation: https://github.com/adbutler007/private_notes/tree/main/audio_summary_app
    EOS
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
  EOS
end

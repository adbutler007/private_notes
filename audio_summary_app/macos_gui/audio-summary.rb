cask "audio-summary" do
  version "0.2.0"
  sha256 "PLACEHOLDER_SHA256"  # Update after building and signing

  url "https://github.com/YOUR_USERNAME/audio-summary/releases/download/v#{version}/AudioSummary-#{version}.zip"
  name "Audio Summary"
  desc "Menu-bar app that captures and summarizes Zoom/Teams calls using local AI"
  homepage "https://github.com/YOUR_USERNAME/audio-summary"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates false
  depends_on macos: ">= :ventura"

  app "Audio Summary.app"

  postflight do
    # Ensure engine dependencies are available
    system_command "#{HOMEBREW_PREFIX}/bin/python3",
                   args: ["-m", "pip", "list"],
                   print_stderr: false
  end

  zap trash: [
    "~/Library/Logs/Audio Summary",
    "~/Library/Preferences/com.audiosummary.gui.plist",
    "~/Library/Application Support/com.audiosummary.gui",
  ]

  caveats <<~EOS
    Audio Summary requires the Python engine to be running.

    To install the engine:
      cd #{HOMEBREW_PREFIX}/share/audio-summary-app
      uv sync

    To start the engine manually:
      uv run audio-summary-server

    Or, set up the engine to start automatically when the GUI launches.

    Permissions needed:
    - Screen Recording: For capturing Zoom/Teams audio
    - Notifications: For summary ready alerts

    All audio processing happens locally on your Mac.
  EOS
end

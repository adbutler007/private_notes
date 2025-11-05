# Audio Summary - User Guide

Privacy-first audio transcription and summarization for sales discovery calls.

## Table of Contents

- [Installation](#installation)
- [First-Time Setup](#first-time-setup)
- [Basic Usage](#basic-usage)
- [Meeting Browser](#meeting-browser)
- [Settings](#settings)
- [Zoom/Teams Integration](#zoomteams-integration)
- [Exporting Data](#exporting-data)
- [Troubleshooting](#troubleshooting)

## Installation

### Via Homebrew (Recommended)

```bash
# Add the tap
brew tap adbutler007/audio-summary

# Install
brew install --cask audio-summary
```

### Manual Installation

1. Download `AudioSummary-0.1.0.zip` from [GitHub Releases](https://github.com/adbutler007/private_notes/releases)
2. Unzip the file
3. Move `Audio Summary.app` to `/Applications`
4. Right-click the app and select "Open" (first time only)

## First-Time Setup

When you launch Audio Summary for the first time, the Setup Wizard will guide you through:

### Step 1: Ollama Installation

Ollama runs the AI models locally on your Mac.

**Option 1 - Homebrew:**
```bash
brew install ollama
```

**Option 2 - Direct Download:**
Visit [ollama.com/download](https://ollama.com/download)

### Step 2: Download AI Model

The app needs a language model for summarization:

```bash
ollama pull qwen3:4b-instruct
```

This downloads ~4GB. The wizard can do this for you.

**Other models you can try:**
- `llama3.2:3b` - Faster, less accurate
- `phi3:3.8b` - Balanced
- `gemma2:2b` - Smallest

### Step 3: Audio Setup (Optional)

To capture Zoom/Teams audio, install BlackHole:

```bash
brew install blackhole-2ch
```

Then in Zoom/Teams settings:
1. Set **Speaker** to "BlackHole 2ch"
2. In macOS Sound settings, create a **Multi-Output Device** with both BlackHole and your speakers
3. Set this as your default output

### Step 4: Choose Summary Location

Pick where to save meeting summaries (default: `~/Documents/Meeting Summaries`)

## Basic Usage

### Starting a Recording

1. Click the Audio Summary icon in your menu bar
2. Select **"Start Recording"**
3. The icon changes to show recording is active
4. You'll see a notification: "Recording Started"

### During Recording

- The app transcribes audio in real-time
- Every 5 minutes, it creates a "chunk summary"
- Transcripts are held in RAM only (never saved to disk)

### Stopping a Recording

1. Click the menu bar icon
2. Select **"Stop Recording"**
3. The app generates:
   - Final summary (3-5 paragraphs)
   - Structured data (contacts, companies, deals)
   - CSV export

A notification appears when the summary is ready.

### Viewing Summaries

**From menu bar:**
- Click icon → **"Recent Summaries"**
- Shows last 5 meetings

**From Meeting Browser:**
- Click icon → **"Meeting Browser..."**
- See all meetings with search and filters

## Meeting Browser

The Meeting Browser helps you find and manage all your meeting summaries.

### Features

**Search:**
- Type in the search box to filter by contact or company name
- Real-time filtering as you type

**Date Filters:**
- Today
- Yesterday
- This Week
- Last Week
- This Month
- Last Month
- All Time

**Company Filter:**
- Filter by specific companies
- Populated from your meeting data

**Preview Pane:**
- Click a meeting to preview the summary
- See contact name, company, date

**Actions:**
- **Open in Editor** - Opens the summary .txt file
- **Show in Finder** - Reveals the meeting folder

### Meeting Folders

Each meeting is saved in its own folder:

```
~/Documents/Meeting Summaries/
├── 2025-11-05 Acme Capital - John Smith/
│   ├── summary.txt         # Human-readable summary
│   └── data.json           # Structured data
├── 2025-11-06 Harbor Investments - Sarah Johnson/
│   ├── summary.txt
│   └── data.json
└── meetings.csv            # Master CSV of all meetings
```

**Folder naming:**
- Format: `YYYY-MM-DD Company Name - Contact Name`
- If no company/contact extracted: `YYYY-MM-DD Meeting HHMMSS`

## Settings

Access via menu bar icon → **"Settings..."**

### Audio Settings

- **Input Device:** Select your microphone or BlackHole
- **Auto-detect Zoom/Teams:** Automatically start recording when calls begin (coming soon)

### Recording Settings

- **Auto-start when call begins:** Start recording automatically
- **Auto-stop when call ends:** Stop recording when Zoom/Teams closes
- **Show notifications:** Get notifications when summaries are ready

### Models

- **Whisper Model:** Choose transcription quality
  - `tiny` - Fastest, lowest accuracy
  - `small` - Good balance
  - `medium` - Better accuracy
  - `large` - Best accuracy (recommended)
  - `turbo` - Large-v3-turbo (fast + accurate)

- **LLM Model:** Choose summarization model
  - `qwen3:4b-instruct` - Recommended (best quality)
  - `llama3.2:3b` - Faster alternative
  - `phi3:3.8b` - Balanced
  - `gemma2:2b` - Smallest/fastest

### Export

- **Summary Folder:** Where to save meeting folders
- **CSV Export:** Path to `meetings.csv`
- **Auto-export weekly:** Automatically export on Fridays (coming soon)

## Zoom/Teams Integration

### Setup for Zoom

1. Install BlackHole: `brew install blackhole-2ch`

2. In **Zoom Settings** → **Audio**:
   - Set **Speaker** to "BlackHole 2ch"

3. In **macOS System Settings** → **Sound**:
   - Create a **Multi-Output Device**:
     - Click "+" → "Create Multi-Output Device"
     - Check both "BlackHole 2ch" and your speakers
   - Set this as your default output

4. Audio Summary Settings:
   - Set **Input Device** to "BlackHole 2ch"

Now when you join a Zoom call:
- You hear audio through your speakers (via Multi-Output)
- Audio Summary captures via BlackHole

### Setup for Microsoft Teams

Same as Zoom:
1. Teams Settings → Devices
2. Set **Speaker** to "BlackHole 2ch"
3. Audio Summary captures the audio

### Manual Recording (Without BlackHole)

You can also just use your microphone:
1. Audio Summary Settings → Input Device → Built-in Microphone
2. Place your Mac near the speakers to capture audio

## Exporting Data

### Viewing Summary Files

Summaries are saved as:
- **`summary.txt`** - Plain text, readable in any editor
- **`data.json`** - Structured JSON with contacts, companies, deals

### CSV Export

The `meetings.csv` file contains all meetings in spreadsheet format:

| meeting_date | company_name | contact_name | contact_role | deal_ticket_size | products_of_interest |
|--------------|--------------|--------------|--------------|------------------|----------------------|
| 2025-11-05 | Acme Capital | John Smith | CIO | $50-100M | RSSB, RSST |
| 2025-11-06 | Harbor Inv | Sarah Johnson | PM | $25-50M | BTGD |

**Open in:**
- Excel: `open meetings.csv`
- Google Sheets: File → Import → Upload
- Numbers: `open -a Numbers meetings.csv`

### Importing to CRM

The CSV can be imported into:
- Salesforce
- HubSpot
- Pipedrive
- Any CRM that supports CSV import

Map the columns to your CRM fields.

## Troubleshooting

### "App is damaged" error

macOS Gatekeeper blocks unsigned apps. Fix:

```bash
xattr -cr "/Applications/Audio Summary.app"
```

Then right-click → Open

### "Ollama not found" error

Install Ollama:
```bash
brew install ollama
```

Or download from [ollama.com](https://ollama.com)

### Model download fails

Download manually:
```bash
ollama pull qwen3:4b-instruct
```

Check the model exists:
```bash
ollama list
```

### No audio captured

**Check:**
1. Audio Summary Settings → Input Device is correct
2. macOS Privacy Settings → Microphone → Audio Summary is allowed
3. BlackHole is installed (if using Zoom/Teams audio)

### Transcription is inaccurate

**Try:**
1. Use a larger Whisper model (Settings → Models → Whisper)
2. Ensure good audio quality (minimize background noise)
3. Speak clearly and at a moderate pace

### Summaries are too long

**Adjust:**
1. Edit `config.py`:
   ```python
   chunk_summary_max_tokens = 200  # Lower = more concise
   final_summary_max_tokens = 800  # Lower = more concise
   ```

2. Or use a different LLM model that's more concise

### App crashes or freezes

**Try:**
1. Check Activity Monitor for memory usage
2. Close other apps (summarization needs ~16GB RAM recommended)
3. Use a smaller LLM model (phi3:3.8b or gemma2:2b)

### Can't find summaries

1. Check Settings → Export → Summary Folder path
2. Make sure you stopped the recording (summaries only generated on stop)
3. Look in Meeting Browser for all meetings

## Privacy & Security

### What is saved:
- Meeting summaries (text)
- Structured data (JSON)
- CSV exports

### What is NOT saved:
- Raw audio recordings
- Transcripts (held in RAM only, then deleted)

### Where data is processed:
- **All on-device** - No cloud API calls
- Whisper runs locally (MLX)
- LLM runs locally (Ollama)

### Data locations:
- Summaries: `~/Documents/Meeting Summaries` (or your chosen folder)
- App data: `~/Library/Application Support/Audio Summary`
- Preferences: `~/Library/Preferences/com.audiosummary.app.plist`

## Tips & Best Practices

### For Best Transcription

- Use a good microphone
- Minimize background noise
- Speak clearly
- Use the `turbo` or `large` Whisper model

### For Best Summaries

- Record full meetings (not just snippets)
- Longer meetings = better summaries (map-reduce works best with multiple chunks)
- Mention names, companies, numbers explicitly

### For Organized Summaries

- Mention the company name and contact name early in the meeting
- The auto-naming will use this to create meaningful folder names

### For CSV Analysis

- Export weekly and import to Excel/Sheets
- Use pivot tables to analyze:
  - Meetings per week
  - Top companies
  - Average ticket sizes
  - Product interest distribution

## Support

- **Issues:** [GitHub Issues](https://github.com/adbutler007/private_notes/issues)
- **Documentation:** [GitHub README](https://github.com/adbutler007/private_notes/tree/main/audio_summary_app)

## License

MIT License - see LICENSE file for details

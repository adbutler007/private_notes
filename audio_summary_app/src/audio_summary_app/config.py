"""
Configuration for Audio Summary App
All settings for audio capture, transcription, and summarization
"""

from pathlib import Path


class Config:
    """Application configuration"""
    
    # Audio Settings
    sample_rate: int = 16000  # 16kHz is standard for speech
    channels: int = 1  # Mono audio
    
    # Buffer Settings
    max_buffer_size: int = 2000  # Maximum transcript segments to keep in memory
    chunk_duration: int = 300  # 5 minutes per chunk for map-reduce
    
    # Transcription Settings (MLX Whisper - optimized for Apple Silicon)
    stt_model_path: str = "turbo"  # Whisper model size
    # Options: tiny, small, medium, large, large-v3, turbo
    #   - tiny: Fastest, lowest accuracy (~39M params)
    #   - small: Good balance (~244M params)
    #   - medium: Better accuracy (~769M params)
    #   - large/large-v3: Best accuracy (~1550M params)
    #   - turbo: Large-v3-turbo, faster variant of large
    # Models auto-download on first use
    # Using large on M4 Mac with 32GB RAM for best accuracy
    # MLX provides 3-5x faster transcription on M-series chips

    # Audio buffering for transcription
    stt_min_audio_duration: float = 3.0  # Minimum seconds before transcribing
    # Longer buffers (3-5s) = better accuracy, fewer word cutoffs
    # Shorter buffers (1-2s) = lower latency, more fragmented text
    stt_max_audio_duration: float = 10.0  # Maximum seconds to prevent excessive latency

    # Summarization Settings (Ollama)
    llm_model_name: str = "qwen3:4b-instruct"  # Ollama model name
    # Other options: llama3.2:3b, phi3:3.8b, gemma2:2b, qwen3:1.7b
    summary_interval: int = 300  # Generate rolling summary every 5 minutes

    # Token Limits
    chunk_summary_max_tokens: int = 300  # Max tokens for individual chunk summaries (concise)
    final_summary_max_tokens: int = 1200  # Max tokens for final summary (3-5 paragraphs)

    # Summary Prompts
    chunk_summary_prompt: str = """Summarize this conversation segment in 2-3 concise paragraphs. Focus on:
- Main discussion points and context
- Key decisions or action items
- Important information shared

If contact/company/deal data is mentioned (names, roles, AUM, ticket sizes, products, strategies), note it briefly but do NOT format it as structured lists - that will be extracted separately.

Transcript:
{text}

Summary:"""

    final_summary_prompt: str = """You are summarizing a sales discovery call at an asset management company focused on alternative investments.

Create a concise final summary (3-5 paragraphs maximum) covering:
1. Meeting context and participants
2. Key discussion points and client needs
3. Important decisions or next steps
4. Notable insights or observations

DO NOT repeat structured data (names, roles, AUM, ticket sizes, products) in list format - this will be extracted separately. Keep the summary narrative and flowing.

Segment Summaries:
{summaries_text}

Final Summary:"""

    # Data Extraction Prompt (for structured JSON output after final summary)
    data_extraction_prompt: str = """You are extracting structured data from meeting summaries. Review the summaries below and extract all mentioned information into the specified JSON format.

If information is not mentioned or unclear, use null for that field.

Summaries:
{summaries_text}

Extract the following information as JSON:"""

    # Output Settings
    output_dir: str = "./summaries"  # Where to save summary files (ONLY FILES SAVED)
    # Produces two files per recording:
    #   - summary_YYYYMMDD_HHMMSS.txt: Human-readable summary
    #   - summary_YYYYMMDD_HHMMSS.json: Structured data (contacts, companies, deals)

    # CSV Export Settings
    csv_export_path: str = "./summaries/meetings.csv"  # Path to CSV file for meeting data
    # Each recording appends a row with flattened structured data
    # Useful for tracking all meetings in a spreadsheet
    
    def __init__(self):
        """Initialize configuration and create necessary directories"""
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def __str__(self):
        """String representation of config"""
        return f"""Audio Summary App Configuration:
Audio:
  - Sample Rate: {self.sample_rate} Hz
  - Channels: {self.channels}

Buffer:
  - Max Segments: {self.max_buffer_size}
  - Chunk Duration: {self.chunk_duration}s

Models:
  - STT Model: MLX Whisper {self.stt_model_path}
  - LLM Model: Ollama {self.llm_model_name}

Summary:
  - Interval: {self.summary_interval}s
  - Chunk Summary Max Tokens: {self.chunk_summary_max_tokens}
  - Final Summary Max Tokens: {self.final_summary_max_tokens}

Output:
  - Directory: {self.output_dir}
  - CSV Export: {self.csv_export_path}
"""


# Model setup instructions
MODEL_SETUP_INSTRUCTIONS = """
Model Setup Instructions:
========================

1. Install Ollama:
   - macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh
   - Windows: Download from https://ollama.com/download
   - Or use: brew install ollama (macOS)

2. Pull the Qwen3 model:
   ollama pull qwen3:4b-instruct

3. Speech-to-Text (MLX Whisper):
   - Models auto-download on first run
   - Available: tiny, small, medium, large, large-v3, turbo
   - Recommended for M4 Mac with 32GB RAM:
     * large: Best accuracy (use for meetings/important content)
     * turbo: Faster variant if you need speed over accuracy
   - MLX provides 3-5x faster transcription on Apple Silicon

4. Install Dependencies:
   uv sync
   # or: pip install mlx-whisper ollama sounddevice numpy

That's it! No manual model downloads needed.
Both MLX Whisper and Ollama handle models automatically.
"""

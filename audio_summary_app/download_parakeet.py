#!/usr/bin/env python3
"""
Download Parakeet model for Audio Summary
Called during Homebrew installation to pre-download the model
"""

import sys
from huggingface_hub import snapshot_download

def download_parakeet_model(model_name="mlx-community/parakeet-tdt-0.6b-v3"):
    """Download Parakeet model from Hugging Face"""
    print(f"Downloading Parakeet model: {model_name}")
    print("This may take 3-5 minutes (~2GB)...")

    try:
        # Download model to default cache location
        snapshot_download(
            repo_id=model_name,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
        )
        print(f"✓ Parakeet model downloaded successfully!")
        return 0
    except Exception as e:
        print(f"Error downloading Parakeet model: {e}", file=sys.stderr)
        print("The model will download automatically on first recording.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(download_parakeet_model())

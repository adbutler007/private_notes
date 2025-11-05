"""
Ollama Manager
Utilities to ensure Ollama is running and models are available
"""

import subprocess
import time
import platform
from typing import Optional
import ollama


def is_ollama_running() -> bool:
    """Check if Ollama service is running"""
    try:
        # Try to list models - if this works, Ollama is running
        ollama.list()
        return True
    except Exception:
        return False


def start_ollama_service() -> bool:
    """
    Attempt to start the Ollama service
    Returns True if successful or already running
    """
    if is_ollama_running():
        print("[Ollama] Service is already running")
        return True

    print("[Ollama] Service not running, attempting to start...")

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # On macOS, Ollama usually runs as an app or service
            # Try to start it via the CLI which should auto-start the service
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        elif system == "Linux":
            # On Linux, try to start via systemd or direct command
            try:
                # Try systemd first
                subprocess.run(
                    ["systemctl", "--user", "start", "ollama"],
                    check=False,
                    capture_output=True
                )
            except FileNotFoundError:
                # Fall back to direct command
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

        elif system == "Windows":
            # On Windows, Ollama typically runs as a service
            # Try to start it
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

        # Wait a bit for the service to start
        print("[Ollama] Waiting for service to start...")
        for i in range(10):
            time.sleep(1)
            if is_ollama_running():
                print("[Ollama] Service started successfully")
                return True

        print("[Ollama] Warning: Service may not have started properly")
        return False

    except FileNotFoundError:
        print("[Ollama] Error: 'ollama' command not found")
        print("[Ollama] Please install Ollama from: https://ollama.com/")
        return False
    except Exception as e:
        print(f"[Ollama] Error starting service: {e}")
        return False


def is_model_available(model_name: str) -> bool:
    """Check if a specific model is available locally"""
    try:
        models = ollama.list()
        model_list = models.get('models', [])

        # Handle different model dict structures
        model_names = []
        for m in model_list:
            name = m.get('name') or m.get('model') or str(m)
            model_names.append(name)

        # Check for exact match or partial match (handles tags)
        return any(model_name in name or name.startswith(model_name) for name in model_names)

    except Exception:
        return False


def pull_model(model_name: str) -> bool:
    """
    Pull a model from Ollama registry
    Returns True if successful
    """
    try:
        print(f"[Ollama] Pulling model: {model_name}")
        print(f"[Ollama] This may take a few minutes for first-time download...")

        # Pull the model
        ollama.pull(model_name)

        print(f"[Ollama] Model {model_name} downloaded successfully")
        return True

    except Exception as e:
        print(f"[Ollama] Error pulling model: {e}")
        return False


def ensure_model_ready(model_name: str, auto_pull: bool = True) -> bool:
    """
    Ensure Ollama service is running and model is available

    Args:
        model_name: Name of the model to ensure is ready
        auto_pull: Whether to automatically pull the model if not available

    Returns:
        True if model is ready to use, False otherwise
    """
    print(f"[Ollama] Ensuring model '{model_name}' is ready...")

    # Step 1: Ensure Ollama service is running
    if not start_ollama_service():
        print("[Ollama] Failed to start Ollama service")
        return False

    # Step 2: Check if model is available
    if is_model_available(model_name):
        print(f"[Ollama] Model '{model_name}' is ready")
        return True

    # Step 3: Try to pull the model if auto_pull is enabled
    if auto_pull:
        print(f"[Ollama] Model '{model_name}' not found locally")
        return pull_model(model_name)
    else:
        print(f"[Ollama] Model '{model_name}' not available")
        print(f"[Ollama] Run: ollama pull {model_name}")
        return False


def get_ollama_info() -> Optional[dict]:
    """Get information about Ollama installation and available models"""
    try:
        if not is_ollama_running():
            return None

        models = ollama.list()

        return {
            'running': True,
            'models': models.get('models', []),
            'model_count': len(models.get('models', []))
        }

    except Exception:
        return None

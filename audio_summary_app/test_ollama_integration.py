#!/usr/bin/env python3
"""
Quick test to verify Ollama integration works
"""

from src.audio_summary_app.ollama_manager import (
    is_ollama_running,
    start_ollama_service,
    is_model_available,
    ensure_model_ready,
    get_ollama_info
)
from src.audio_summary_app.summarizer import MapReduceSummarizer

def main():
    print("=" * 80)
    print("Ollama Integration Test")
    print("=" * 80)
    print()

    # Test 1: Check if Ollama is running
    print("Test 1: Checking if Ollama is running...")
    running = is_ollama_running()
    print(f"  Result: {'✓ Running' if running else '✗ Not running'}")
    print()

    # Test 2: Try to start Ollama
    if not running:
        print("Test 2: Attempting to start Ollama service...")
        started = start_ollama_service()
        print(f"  Result: {'✓ Started' if started else '✗ Failed to start'}")
        print()

    # Test 3: Get Ollama info
    print("Test 3: Getting Ollama information...")
    info = get_ollama_info()
    if info:
        print(f"  Status: ✓ Running")
        print(f"  Models available: {info['model_count']}")
        if info['models']:
            print("  Installed models:")
            for model in info['models']:
                # Handle different model dict structures
                model_name = model.get('name') or model.get('model') or str(model)
                print(f"    - {model_name}")
    else:
        print("  Status: ✗ Not available")
    print()

    # Test 4: Check for qwen3:1.7b
    print("Test 4: Checking for qwen3:1.7b model...")
    model_name = "qwen3:1.7b"
    available = is_model_available(model_name)
    print(f"  Result: {'✓ Available' if available else '✗ Not found'}")
    print()

    # Test 5: Ensure model is ready (will pull if needed)
    print("Test 5: Ensuring model is ready...")
    print("  (This may take a few minutes if downloading)")
    ready = ensure_model_ready(model_name, auto_pull=True)
    print(f"  Result: {'✓ Ready' if ready else '✗ Not ready'}")
    print()

    # Test 6: Initialize summarizer (should auto-start Ollama)
    print("Test 6: Initializing MapReduceSummarizer...")
    try:
        summarizer = MapReduceSummarizer(model_name=model_name)
        print("  Result: ✓ Initialized successfully")
        print(f"  LLM type: {type(summarizer.llm).__name__}")

        # Test 7: Generate a test summary
        print()
        print("Test 7: Generating test summary...")
        test_text = """
        This is a test conversation about technology and software development.
        We discussed various programming languages including Python and JavaScript.
        The team agreed to use modern tools and best practices.
        There was consensus on the importance of good documentation.
        """
        summary = summarizer.summarize_chunk(test_text)
        print(f"  Input: {len(test_text.split())} words")
        print(f"  Output: {len(summary.split())} words")
        print(f"  Summary: {summary[:200]}...")
        print("  Result: ✓ Summary generated")

    except Exception as e:
        print(f"  Result: ✗ Failed - {e}")

    print()
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

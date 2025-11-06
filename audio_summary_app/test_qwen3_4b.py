#!/usr/bin/env python3
"""
Test qwen3:4b-instruct model with the new parameters
"""

import ollama

def test_model():
    """Test the qwen3:4b-instruct model with instruction tuning"""

    # Load test text
    transcript_path = "/Users/adambutler/Projects/private_notes/transcript.txt"
    with open(transcript_path, 'r', encoding='latin-1') as f:
        full_text = f.read()

    # Take first 500 words
    words = full_text.split()
    test_text = ' '.join(words[:500])

    print("=" * 80)
    print("Testing qwen3:4b-instruct Model")
    print("=" * 80)
    print(f"\nInput: {len(words[:500])} words")
    print("\nGenerating summary...\n")

    # Create prompt
    prompt = f"""Summarize the following conversation transcript concisely.
Focus on key points, topics discussed, and any important decisions or information.

Transcript:
{test_text}

Summary:"""

    # Call Ollama with new parameters
    response = ollama.generate(
        model="qwen3:4b-instruct",
        prompt=prompt,
        options={
            'num_predict': 200,
            'temperature': 0.7,
            'top_k': 20,
            'top_p': 0.8,
            'repeat_penalty': 1,
            'stop': ['<|im_start|>', '<|im_end|>'],
        }
    )

    # Extract response
    if hasattr(response, 'response') and response.response:
        result = response.response
    elif hasattr(response, 'thinking') and response.thinking:
        result = response.thinking
    elif isinstance(response, dict) and 'response' in response:
        result = response['response']
    elif isinstance(response, dict) and 'thinking' in response:
        result = response['thinking']
    else:
        result = str(response)

    summary = result.strip()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(summary)
    print()
    print("=" * 80)
    print("Statistics:")
    print(f"  Input: {len(words[:500])} words")
    print(f"  Output: {len(summary.split())} words")
    print(f"  Compression: {len(words[:500]) / max(len(summary.split()), 1):.1f}x")
    print("=" * 80)

    if summary and len(summary) > 20:
        print("\n✓ TEST PASSED - Model is generating proper summaries")
        return 0
    else:
        print("\n✗ TEST FAILED - Summary is too short or empty")
        return 1


if __name__ == "__main__":
    exit(test_model())

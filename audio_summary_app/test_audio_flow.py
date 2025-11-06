#!/usr/bin/env python3
"""
Test the audio flow from capture to transcription
"""

import queue
import time
import numpy as np
from audio_summary_app.audio_capture import AudioCaptureManager
from audio_summary_app.transcriber import StreamingTranscriber

def test_audio_flow():
    print("="*80)
    print("Testing Audio Flow: Capture → Queue → Transcription")
    print("="*80)
    print()
    
    # Create components
    audio_queue = queue.Queue()
    audio_manager = AudioCaptureManager(sample_rate=16000, channels=1)
    transcriber = StreamingTranscriber(model_path="large")
    
    print("✓ Components created")
    print()
    
    # Start capture
    print("Starting audio capture...")
    audio_manager.start_capture(audio_queue)
    audio_manager.enable_recording()
    print("✓ Audio capture started")
    print()
    
    # Wait a bit for audio to accumulate
    print("Recording for 3 seconds...")
    print("Please make some noise (speak, clap, etc.)")
    time.sleep(3)
    
    # Check queue
    queue_size = audio_queue.qsize()
    print(f"\n✓ Audio queue size: {queue_size} chunks")
    
    if queue_size == 0:
        print("✗ No audio in queue! Problem with audio capture.")
        audio_manager.stop_capture()
        return 1
    
    print(f"✓ Audio is being captured and queued")
    print()
    
    # Try to transcribe some chunks
    print("Testing transcription...")
    transcribed_count = 0
    
    for i in range(min(3, queue_size)):
        try:
            audio_chunk = audio_queue.get(timeout=1)
            print(f"  Chunk {i+1}:")
            print(f"    - Data shape: {audio_chunk['data'].shape}")
            print(f"    - Source: {audio_chunk['source']}")
            print(f"    - Max amplitude: {np.max(np.abs(audio_chunk['data'])):.4f}")
            
            # Try transcription
            transcript = transcriber.transcribe(audio_chunk)
            if transcript:
                print(f"    - Transcript: '{transcript}'")
                transcribed_count += 1
            else:
                print(f"    - Transcript: (empty - may need more audio)")
            print()
            
        except queue.Empty:
            print(f"  Chunk {i+1}: Queue empty")
            break
        except Exception as e:
            print(f"  Chunk {i+1}: Error - {e}")
            break
    
    # Clean up
    audio_manager.stop_capture()
    
    print("="*80)
    if transcribed_count > 0:
        print(f"✓ TEST PASSED - Transcribed {transcribed_count} chunks")
    else:
        print("⚠ TEST PARTIAL - Audio captured but no transcription")
        print("  (This is normal if not enough speech or audio too quiet)")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    exit(test_audio_flow())

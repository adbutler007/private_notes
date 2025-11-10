"""
Audio Capture Manager
Captures both audio input (microphone) and audio output (system audio/loopback)
Audio is NEVER saved to disk - only sent to processing queue
"""

import numpy as np
import sounddevice as sd
import threading
import queue
from typing import Optional


class AudioCaptureManager:
    """Manages audio capture from both input and output devices"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, input_device: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.input_device = input_device  # None = default device
        self.is_capturing = False
        self.is_recording_enabled = False

        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.InputStream] = None
        self.audio_queue: Optional[queue.Queue] = None

        # Buffer for combining input and output
        self.chunk_size = int(sample_rate * 0.5)  # 500ms chunks
        
    def start_capture(self, audio_queue: queue.Queue):
        """Start capturing audio from both sources"""
        if self.is_capturing:
            return
            
        self.audio_queue = audio_queue
        self.is_capturing = True
        
        # Start input stream (microphone or specified device)
        try:
            self.input_stream = sd.InputStream(
                device=self.input_device,  # None = default, or specific device index
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._input_callback,
                blocksize=self.chunk_size,
                dtype=np.float32
            )
            self.input_stream.start()
            device_name = sd.query_devices(self.input_device if self.input_device is not None else sd.default.device[0])['name']
            print(f"Started audio capture (device: {device_name})")
        except Exception as e:
            print(f"Warning: Could not start audio capture: {e}")
            
        # Start output stream (system audio/loopback)
        # Note: This requires special setup on different OSes
        try:
            # Try to find a loopback/monitor device
            loopback_device = self._find_loopback_device()
            
            if loopback_device is not None:
                self.output_stream = sd.InputStream(
                    device=loopback_device,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=self._output_callback,
                    blocksize=self.chunk_size,
                    dtype=np.float32
                )
                self.output_stream.start()
                print(f"Started system audio capture (device: {sd.query_devices(loopback_device)['name']})")
            else:
                print("Warning: No loopback device found. Only microphone will be captured.")
                print("Setup instructions:")
                print("  - Windows: Install VB-Cable or similar virtual audio cable")
                print("  - macOS: Use BlackHole or enable system audio capture")
                print("  - Linux: Use PulseAudio monitor or JACK")
        except Exception as e:
            print(f"Warning: Could not start system audio capture: {e}")
            
    def stop_capture(self):
        """Stop all audio capture"""
        self.is_capturing = False
        
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
            
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
            
        print("Audio capture stopped")
        
    def enable_recording(self):
        """Enable sending audio to the queue (when user starts recording)"""
        self.is_recording_enabled = True
        
    def disable_recording(self):
        """Disable sending audio to the queue (when user stops recording)"""
        self.is_recording_enabled = False
        
    def _input_callback(self, indata, frames, time_info, status):
        """Callback for microphone input"""
        if status:
            print(f"Input status: {status}")
            
        if self.is_recording_enabled and self.audio_queue:
            # Convert to numpy array and normalize
            audio_data = indata.copy()
            
            # Add metadata to distinguish source
            audio_chunk = {
                'data': audio_data,
                'source': 'input',
                'timestamp': time_info.inputBufferAdcTime
            }
            
            self.audio_queue.put(audio_chunk)
            
    def _output_callback(self, indata, frames, time_info, status):
        """Callback for system audio output"""
        if status:
            print(f"Output status: {status}")
            
        if self.is_recording_enabled and self.audio_queue:
            # Convert to numpy array
            audio_data = indata.copy()
            
            # Add metadata to distinguish source
            audio_chunk = {
                'data': audio_data,
                'source': 'output',
                'timestamp': time_info.inputBufferAdcTime
            }
            
            self.audio_queue.put(audio_chunk)
            
    def _find_loopback_device(self) -> Optional[int]:
        """
        Try to find a loopback/monitor device for capturing system audio
        Returns device index or None if not found
        """
        devices = sd.query_devices()
        
        # Keywords that might indicate a loopback device
        loopback_keywords = [
            'loopback', 'monitor', 'stereo mix', 'wave out', 
            'what u hear', 'blackhole', 'vb-cable', 'virtual'
        ]
        
        for idx, device in enumerate(devices):
            device_name = device['name'].lower()
            
            # Check if it's an input device with loopback keywords
            if device['max_input_channels'] > 0:
                for keyword in loopback_keywords:
                    if keyword in device_name:
                        return idx
                        
        return None
        
    def list_devices(self):
        """List all available audio devices"""
        print("\nAvailable Audio Devices:")
        print("=" * 60)
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            print(f"{idx}: {device['name']}")
            print(f"   Inputs: {device['max_input_channels']}, "
                  f"Outputs: {device['max_output_channels']}")
        print()

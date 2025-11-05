"""
Transcript Buffer
Maintains a rolling window of transcript segments in memory
NEVER saves to disk - only keeps data in RAM
"""

from collections import deque
from datetime import datetime
from typing import List, Dict
import threading


class TranscriptBuffer:
    """
    In-memory buffer for transcript segments
    Uses a deque with maximum size to automatically discard old segments
    """
    
    def __init__(self, max_buffer_size: int = 1000, chunk_duration: int = 300):
        """
        Args:
            max_buffer_size: Maximum number of transcript segments to keep
            chunk_duration: Duration in seconds for each logical chunk (for map-reduce)
        """
        self.max_buffer_size = max_buffer_size
        self.chunk_duration = chunk_duration
        
        # Deque automatically discards old items when maxlen is reached
        self.segments = deque(maxlen=max_buffer_size)
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Track chunks for map-reduce
        self.chunks = []
        self.current_chunk = []
        self.chunk_start_time = datetime.now()
        
    def add_segment(self, text: str, source: str = "mixed"):
        """
        Add a transcript segment to the buffer
        
        Args:
            text: The transcribed text
            source: Source of the audio (input/output/mixed)
        """
        with self.lock:
            timestamp = datetime.now()
            
            segment = {
                'text': text,
                'timestamp': timestamp,
                'source': source
            }
            
            self.segments.append(segment)
            self.current_chunk.append(segment)
            
            # Check if we should finalize the current chunk
            elapsed = (timestamp - self.chunk_start_time).total_seconds()
            if elapsed >= self.chunk_duration:
                self._finalize_chunk()
                
    def _finalize_chunk(self):
        """Finalize the current chunk for map-reduce processing"""
        if self.current_chunk:
            chunk_text = " ".join(seg['text'] for seg in self.current_chunk)
            
            chunk = {
                'text': chunk_text,
                'start_time': self.current_chunk[0]['timestamp'],
                'end_time': self.current_chunk[-1]['timestamp'],
                'segment_count': len(self.current_chunk)
            }
            
            self.chunks.append(chunk)
            
            # Reset for next chunk (data not saved to disk, just reorganized in memory)
            self.current_chunk = []
            self.chunk_start_time = datetime.now()
            
    def get_all_chunks(self) -> List[Dict]:
        """
        Get all finalized chunks for final summary generation
        Returns list of chunks with their text and metadata
        """
        with self.lock:
            # Finalize any remaining chunk
            if self.current_chunk:
                self._finalize_chunk()
                
            return self.chunks.copy()
            
    def get_recent_segments(self, count: int = 10) -> List[Dict]:
        """Get the most recent N segments"""
        with self.lock:
            return list(self.segments)[-count:]
            
    def get_segments_since(self, timestamp: datetime) -> List[Dict]:
        """Get all segments since a specific timestamp"""
        with self.lock:
            return [seg for seg in self.segments if seg['timestamp'] >= timestamp]
            
    def get_buffer_stats(self) -> Dict:
        """Get statistics about the current buffer"""
        with self.lock:
            if not self.segments:
                return {
                    'segment_count': 0,
                    'chunk_count': 0,
                    'total_chars': 0,
                    'buffer_usage': 0.0
                }
                
            total_chars = sum(len(seg['text']) for seg in self.segments)
            
            return {
                'segment_count': len(self.segments),
                'chunk_count': len(self.chunks),
                'total_chars': total_chars,
                'buffer_usage': len(self.segments) / self.max_buffer_size,
                'oldest_timestamp': self.segments[0]['timestamp'],
                'newest_timestamp': self.segments[-1]['timestamp']
            }
            
    def clear(self):
        """
        Clear all data from memory
        This is the only 'deletion' - no disk cleanup needed since nothing was saved
        """
        with self.lock:
            self.segments.clear()
            self.chunks.clear()
            self.current_chunk.clear()
            self.chunk_start_time = datetime.now()
            
        print("Buffer cleared from memory (no disk cleanup needed)")
        
    def get_full_transcript(self) -> str:
        """
        Get the full transcript as a single string
        Use sparingly as this concatenates all segments
        """
        with self.lock:
            return " ".join(seg['text'] for seg in self.segments)

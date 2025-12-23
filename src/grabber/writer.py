"""Asynchronous audio writer for WAV files."""

import threading
import queue
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None


class AudioWriter:
    """
    Thread-safe audio writer that writes PCM data to WAV files asynchronously.
    """
    
    def __init__(
        self,
        filepath: Path,
        sample_rate: int = 48000,
        channels: int = 2,
        subtype: str = "PCM_16",
    ):
        """
        Initialize the audio writer.
        
        Args:
            filepath: Path to the output WAV file.
            sample_rate: Sample rate in Hz.
            channels: Number of audio channels.
            subtype: Audio subtype (PCM_16, PCM_24, PCM_32, FLOAT).
        """
        if sf is None:
            raise ImportError(
                "soundfile is required for audio writing. "
                "Install it with: pip install soundfile"
            )
        
        self.filepath = filepath
        self.sample_rate = sample_rate
        self.channels = channels
        self.subtype = subtype
        
        self._queue: queue.Queue[Optional[np.ndarray]] = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None
        self._file: Optional[sf.SoundFile] = None
        self._running = False
        self._frames_written = 0
        self._lock = threading.Lock()
    
    def start(self) -> None:
        """Start the writer thread."""
        if self._running:
            return
        
        self._running = True
        self._frames_written = 0
        
        # Open the file for writing
        self._file = sf.SoundFile(
            str(self.filepath),
            mode="w",
            samplerate=self.sample_rate,
            channels=self.channels,
            subtype=self.subtype,
        )
        
        # Start the writer thread
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="AudioWriter",
        )
        self._writer_thread.start()
        
        print(f"Writing audio to: {self.filepath}")
    
    def _writer_loop(self) -> None:
        """Main loop for the writer thread."""
        while self._running or not self._queue.empty():
            try:
                data = self._queue.get(timeout=0.1)
                if data is None:
                    break
                
                if self._file is not None:
                    self._file.write(data)
                    with self._lock:
                        self._frames_written += len(data)
                
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error writing audio: {e}")
    
    def write(self, data: np.ndarray) -> None:
        """
        Queue audio data for writing.
        
        Args:
            data: NumPy array of audio samples.
        """
        if not self._running:
            return
        
        self._queue.put(data)
    
    def stop(self) -> None:
        """Stop the writer and close the file."""
        if not self._running:
            return
        
        self._running = False
        
        # Signal the writer thread to stop
        self._queue.put(None)
        
        # Wait for the writer thread to finish
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=5.0)
        
        # Close the file
        if self._file is not None:
            self._file.close()
            self._file = None
        
        duration = self.get_duration()
        print(f"\nRecording saved: {self.filepath}")
        print(f"Duration: {duration:.2f} seconds ({self._frames_written} frames)")
    
    def get_frames_written(self) -> int:
        """Get the number of frames written so far."""
        with self._lock:
            return self._frames_written
    
    def get_duration(self) -> float:
        """Get the current duration in seconds."""
        with self._lock:
            return self._frames_written / self.sample_rate if self.sample_rate > 0 else 0.0
    
    def __enter__(self) -> "AudioWriter":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()



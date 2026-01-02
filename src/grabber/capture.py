"""Audio capture using ScreenCaptureKit."""

import sys
import threading
from typing import Callable, Optional
import numpy as np

try:
    import objc
    from Foundation import NSObject
    import ScreenCaptureKit
    import CoreMedia
    import Quartz
except ImportError as e:
    print(f"Error importing macOS frameworks: {e}", file=sys.stderr)
    sys.exit(1)


# Type alias for audio callback
AudioCallback = Callable[[np.ndarray], None]


# Try to import libdispatch for creating dispatch queues
try:
    from libdispatch import dispatch_queue_create, DISPATCH_QUEUE_SERIAL
    HAS_LIBDISPATCH = True
except ImportError:
    HAS_LIBDISPATCH = False


def create_dispatch_queue(name: bytes):
    """Create a serial dispatch queue, or return None if not available."""
    if HAS_LIBDISPATCH:
        return dispatch_queue_create(name, DISPATCH_QUEUE_SERIAL)
    
    # Try using objc runtime to create a queue
    try:
        import ctypes
        libdispatch = ctypes.CDLL('/usr/lib/system/libdispatch.dylib')
        
        # dispatch_queue_create(const char *label, dispatch_queue_attr_t attr)
        libdispatch.dispatch_queue_create.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        libdispatch.dispatch_queue_create.restype = ctypes.c_void_p
        
        queue = libdispatch.dispatch_queue_create(name, None)
        return objc.objc_object(c_void_p=queue) if queue else None
    except Exception:
        return None


class StreamOutput(NSObject):
    """
    Objective-C delegate class to receive audio samples from SCStream.
    
    Implements SCStreamOutput protocol to handle incoming audio buffers.
    """
    
    def init(self):
        self = objc.super(StreamOutput, self).init()
        if self is None:
            return None
        self._audio_callback: Optional[AudioCallback] = None
        self._sample_rate: int = 48000
        self._channels: int = 2
        return self
    
    def setAudioCallback_(self, callback: AudioCallback) -> None:
        """Set the callback function for audio data."""
        self._audio_callback = callback
    
    def setAudioFormat_channels_(self, sample_rate: int, channels: int) -> None:
        """Set the expected audio format."""
        self._sample_rate = sample_rate
        self._channels = channels
    
    def stream_didOutputSampleBuffer_ofType_(
        self,
        stream: "ScreenCaptureKit.SCStream",
        sample_buffer: "CoreMedia.CMSampleBufferRef",
        output_type: int,
    ) -> None:
        """
        Called when new audio/video samples are available.
        
        This is the SCStreamOutput protocol method.
        """
        # Only process audio samples
        if output_type != ScreenCaptureKit.SCStreamOutputTypeAudio:
            return
        
        if self._audio_callback is None:
            return
        
        try:
            # Extract audio data from CMSampleBuffer
            audio_data = self._extract_audio_data(sample_buffer)
            if audio_data is not None and len(audio_data) > 0:
                self._audio_callback(audio_data)
        except Exception as e:
            print(f"Error processing audio buffer: {e}", file=sys.stderr)
    
    def _extract_audio_data(
        self, sample_buffer: "CoreMedia.CMSampleBufferRef"
    ) -> Optional[np.ndarray]:
        """Extract PCM audio data from a CMSampleBuffer."""
        try:
            # Check if buffer is valid
            if not CoreMedia.CMSampleBufferIsValid(sample_buffer):
                return None
            
            # Get the audio buffer list
            block_buffer = CoreMedia.CMSampleBufferGetDataBuffer(sample_buffer)
            if block_buffer is None:
                return None
            
            # Get the raw data length
            data_length = CoreMedia.CMBlockBufferGetDataLength(block_buffer)
            if data_length == 0:
                return None
            
            # Create a buffer to copy data into
            # CMBlockBufferCopyDataBytes(buffer, offsetToData, dataLength, destination)
            # destination is an "out" parameter that will receive the bytes
            status, data_bytes = CoreMedia.CMBlockBufferCopyDataBytes(
                block_buffer,
                0,  # offset
                data_length,
                None,  # destination - PyObjC will create it
            )
            
            if status != 0:  # noErr is 0
                return None
            
            if data_bytes is None:
                return None
            
            # Convert bytes to numpy array (assuming float32 PCM from ScreenCaptureKit)
            audio_array = np.frombuffer(data_bytes, dtype=np.float32).copy()
            
            # Reshape to stereo if needed
            if self._channels == 2 and len(audio_array) % 2 == 0:
                audio_array = audio_array.reshape(-1, 2)
            
            return audio_array
            
        except Exception as e:
            print(f"Error extracting audio: {e}", file=sys.stderr)
            return None


class StreamDelegate(NSObject):
    """
    Objective-C delegate class for SCStream lifecycle events.
    
    Implements SCStreamDelegate protocol.
    """
    
    def init(self):
        self = objc.super(StreamDelegate, self).init()
        if self is None:
            return None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        return self
    
    def setErrorCallback_(self, callback: Callable[[Exception], None]) -> None:
        """Set the callback for stream errors."""
        self._error_callback = callback
    
    def stream_didStopWithError_(
        self,
        stream: "ScreenCaptureKit.SCStream",
        error: Optional[Exception],
    ) -> None:
        """Called when the stream stops, possibly due to an error."""
        if error and self._error_callback:
            self._error_callback(error)
        elif error:
            print(f"Stream stopped with error: {error}", file=sys.stderr)


class AudioCapture:
    """
    High-level audio capture interface using ScreenCaptureKit.
    """
    
    def __init__(
        self,
        application: "ScreenCaptureKit.SCRunningApplication",
        sample_rate: int = 48000,
        channels: int = 2,
        audio_callback: Optional[AudioCallback] = None,
    ):
        """
        Initialize audio capture for a specific application.
        
        Args:
            application: The SCRunningApplication to capture audio from.
            sample_rate: Sample rate in Hz.
            channels: Number of audio channels.
            audio_callback: Function to call with audio data.
        """
        self.application = application
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_callback = audio_callback
        
        self._stream: Optional["ScreenCaptureKit.SCStream"] = None
        self._stream_output: Optional[StreamOutput] = None
        self._stream_delegate: Optional[StreamDelegate] = None
        self._running = False
        self._error: Optional[Exception] = None
    
    def _create_content_filter(self) -> "ScreenCaptureKit.SCContentFilter":
        """Create a content filter for the target application."""
        # We need to get shareable content to create the filter
        result = {"content": None, "error": None}
        event = threading.Event()
        
        def completion_handler(content, error):
            result["content"] = content
            result["error"] = error
            event.set()
        
        ScreenCaptureKit.SCShareableContent.getShareableContentWithCompletionHandler_(
            completion_handler
        )
        event.wait(timeout=10.0)
        
        if result["error"] or not result["content"]:
            raise RuntimeError("Failed to get shareable content for filter")
        
        content = result["content"]
        
        # Get displays
        displays = content.displays()
        if not displays:
            raise RuntimeError("No displays available")
        
        # Create a filter that includes only this application
        filter_ = (
            ScreenCaptureKit.SCContentFilter.alloc()
            .initWithDisplay_includingApplications_exceptingWindows_(
                displays[0],
                [self.application],
                [],
            )
        )
        
        return filter_
    
    def _create_stream_config(self) -> "ScreenCaptureKit.SCStreamConfiguration":
        """Create the stream configuration."""
        config = ScreenCaptureKit.SCStreamConfiguration.alloc().init()
        
        # Enable audio capture
        config.setCapturesAudio_(True)
        config.setSampleRate_(self.sample_rate)
        config.setChannelCount_(self.channels)
        
        # Exclude audio from our own process
        config.setExcludesCurrentProcessAudio_(True)
        
        # Minimal video configuration (we only want audio, but SCStream requires some video config)
        config.setWidth_(2)
        config.setHeight_(2)
        config.setMinimumFrameInterval_(CoreMedia.CMTimeMake(1, 1))  # 1 FPS minimum
        config.setShowsCursor_(False)
        
        return config
    
    def start(self) -> None:
        """Start audio capture."""
        if self._running:
            return
        
        print(f"Starting audio capture from: {self.application.applicationName()}")
        
        # Create the content filter
        content_filter = self._create_content_filter()
        
        # Create the stream configuration
        config = self._create_stream_config()
        
        # Create the stream delegate
        self._stream_delegate = StreamDelegate.alloc().init()
        self._stream_delegate.setErrorCallback_(self._on_stream_error)
        
        # Create the stream
        self._stream = ScreenCaptureKit.SCStream.alloc().initWithFilter_configuration_delegate_(
            content_filter,
            config,
            self._stream_delegate,
        )
        
        # Create the output handler
        self._stream_output = StreamOutput.alloc().init()
        self._stream_output.setAudioCallback_(self._on_audio_data)
        self._stream_output.setAudioFormat_channels_(self.sample_rate, self.channels)
        
        # Add the output handler for audio (use None for main queue)
        error_result = self._stream.addStreamOutput_type_sampleHandlerQueue_error_(
            self._stream_output,
            ScreenCaptureKit.SCStreamOutputTypeAudio,
            None,  # Use main queue
            None,
        )
        
        # Check for error in result
        if isinstance(error_result, tuple):
            if len(error_result) > 1 and error_result[1]:
                raise RuntimeError(f"Failed to add stream output: {error_result[1]}")
        elif error_result is False:
            raise RuntimeError("Failed to add stream output")
        
        # Start capturing
        result = {"error": None, "completed": False}
        event = threading.Event()
        
        def start_handler(error):
            result["error"] = error
            result["completed"] = True
            event.set()
        
        self._stream.startCaptureWithCompletionHandler_(start_handler)
        
        # Wait for start to complete
        if not event.wait(timeout=10.0):
            raise RuntimeError("Timeout waiting for capture to start")
        
        if result["error"]:
            raise RuntimeError(f"Failed to start capture: {result['error']}")
        
        self._running = True
        print("Audio capture started. Press Ctrl+C to stop...")
    
    def _on_audio_data(self, audio_data: np.ndarray) -> None:
        """Handle incoming audio data."""
        if self.audio_callback:
            self.audio_callback(audio_data)
    
    def _on_stream_error(self, error: Exception) -> None:
        """Handle stream errors."""
        self._error = error
        print(f"Stream error: {error}", file=sys.stderr)
    
    def stop(self) -> None:
        """Stop audio capture."""
        if not self._running:
            return
        
        print("\nStopping audio capture...")
        
        if self._stream:
            result = {"error": None, "completed": False}
            event = threading.Event()
            
            def stop_handler(error):
                result["error"] = error
                result["completed"] = True
                event.set()
            
            self._stream.stopCaptureWithCompletionHandler_(stop_handler)
            
            # Wait for stop to complete
            event.wait(timeout=5.0)
            
            if result["error"]:
                print(f"Warning: Error stopping capture: {result['error']}", file=sys.stderr)
        
        self._running = False
        self._stream = None
        self._stream_output = None
        self._stream_delegate = None
        
        print("Audio capture stopped.")
    
    def is_running(self) -> bool:
        """Check if capture is currently running."""
        return self._running
    
    def get_error(self) -> Optional[Exception]:
        """Get the last error, if any."""
        return self._error
    
    def __enter__(self) -> "AudioCapture":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

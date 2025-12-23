"""Main entry point for PyAudioGrabber CLI."""

import signal
import sys
import time
from pathlib import Path

from .cli import parse_args, get_output_filepath, SUPPORTED_BROWSERS
from .permissions import ensure_permission
from .process import find_browser, list_running_browsers
from .capture import AudioCapture
from .writer import AudioWriter


# Global references for signal handler
_capture = None
_writer = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _capture, _writer
    
    print("\n\nInterrupted by user...")
    
    if _capture:
        _capture.stop()
    
    if _writer:
        _writer.stop()
    
    sys.exit(0)


def print_banner():
    """Print the application banner."""
    print()
    print("=" * 50)
    print("  PyAudioGrabber - Browser Audio Capture")
    print("  macOS ScreenCaptureKit (No drivers needed)")
    print("=" * 50)
    print()


def main():
    """Main entry point."""
    global _capture, _writer
    
    print_banner()
    
    # Parse command line arguments
    args = parse_args()
    
    # Handle --list-browsers flag
    if args.list_browsers:
        print("Supported browsers:")
        for browser in SUPPORTED_BROWSERS:
            print(f"  - {browser}")
        
        print("\nCurrently running browsers:")
        browsers = list_running_browsers()
        if browsers:
            for name, bundle_id, pid in browsers:
                print(f"  - {name} ({bundle_id}) [PID: {pid}]")
        else:
            print("  (none detected)")
        
        return 0
    
    # Check permissions
    ensure_permission()
    
    # Find the target browser
    browser_app = find_browser(args.browser)
    if not browser_app:
        return 1
    
    # Get output file path
    output_path = get_output_filepath(args)
    print(f"\nOutput file: {output_path}")
    print(f"Sample rate: {args.sample_rate} Hz")
    print(f"Channels: {args.channels}")
    print()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create the audio writer
    _writer = AudioWriter(
        filepath=output_path,
        sample_rate=args.sample_rate,
        channels=args.channels,
    )
    
    # Create the audio capture
    _capture = AudioCapture(
        application=browser_app,
        sample_rate=args.sample_rate,
        channels=args.channels,
        audio_callback=_writer.write,
    )
    
    try:
        # Start capturing
        _writer.start()
        _capture.start()
        
        # Keep running until interrupted
        print("\nRecording... Press Ctrl+C to stop.\n")
        
        while _capture.is_running():
            # Print progress
            duration = _writer.get_duration()
            frames = _writer.get_frames_written()
            
            # Simple progress indicator
            sys.stdout.write(f"\r  Duration: {duration:.1f}s | Frames: {frames:,}")
            sys.stdout.flush()
            
            time.sleep(0.5)
            
            # Check for errors
            if _capture.get_error():
                print(f"\nCapture error: {_capture.get_error()}")
                break
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    
    finally:
        # Clean up
        if _capture:
            _capture.stop()
        
        if _writer:
            _writer.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())



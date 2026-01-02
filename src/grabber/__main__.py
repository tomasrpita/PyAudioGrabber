"""Main entry point for PyAudioGrabber CLI."""

import signal
import sys
import time
from pathlib import Path

# Initialize macOS frameworks BEFORE any other imports that use them
# This is required to avoid CGS_REQUIRE_INIT assertion failures
try:
    from AppKit import NSApplication, NSApp
    from Foundation import NSRunLoop, NSDate
    from PyObjCTools import AppHelper
    
    # Create the application instance (required for ScreenCaptureKit)
    app = NSApplication.sharedApplication()
except ImportError as e:
    print(f"Error: Could not initialize macOS frameworks: {e}", file=sys.stderr)
    print("Make sure pyobjc-framework-Cocoa is installed.", file=sys.stderr)
    sys.exit(1)

from .cli import parse_args, get_output_filepath, SUPPORTED_BROWSERS
from .permissions import ensure_permission
from .process import find_browser, list_running_browsers
from .capture import AudioCapture
from .writer import AudioWriter


# Global references for signal handler
_capture = None
_writer = None
_should_stop = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _should_stop
    _should_stop = True
    print("\n\nInterrupted by user...")


def print_banner():
    """Print the application banner."""
    print()
    print("=" * 50)
    print("  PyAudioGrabber - Browser Audio Capture")
    print("  macOS ScreenCaptureKit (No drivers needed)")
    print("=" * 50)
    print()


def run_capture_loop(capture: AudioCapture, writer: AudioWriter) -> int:
    """Run the main capture loop with NSRunLoop integration."""
    global _should_stop
    
    print("\nRecording... Press Ctrl+C to stop.\n")
    
    run_loop = NSRunLoop.currentRunLoop()
    last_print_time = time.time()
    
    while capture.is_running() and not _should_stop:
        # Run the run loop for a short interval to process events
        run_loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
        
        # Print progress every 0.5 seconds
        current_time = time.time()
        if current_time - last_print_time >= 0.5:
            duration = writer.get_duration()
            frames = writer.get_frames_written()
            sys.stdout.write(f"\r  Duration: {duration:.1f}s | Frames: {frames:,}    ")
            sys.stdout.flush()
            last_print_time = current_time
        
        # Check for errors
        if capture.get_error():
            print(f"\nCapture error: {capture.get_error()}")
            return 1
    
    return 0


def main():
    """Main entry point."""
    global _capture, _writer, _should_stop
    
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
    
    result = 0
    
    try:
        # Start capturing
        _writer.start()
        _capture.start()
        
        # Run the capture loop
        result = run_capture_loop(_capture, _writer)
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        result = 1
    
    finally:
        # Clean up
        if _capture:
            _capture.stop()
        
        if _writer:
            _writer.stop()
    
    return result


if __name__ == "__main__":
    sys.exit(main())

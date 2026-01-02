"""CLI argument parsing for PyAudioGrabber."""

import argparse
import os
from pathlib import Path


SUPPORTED_BROWSERS = [
    "Safari",
    "Google Chrome",
    "Firefox",
    "Microsoft Edge",
    "Arc",
    "Brave Browser",
    "Opera",
    "Vivaldi",
]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="grabber",
        description="Capture audio from web browsers on macOS using ScreenCaptureKit",
        epilog="Press Ctrl+C to stop recording and save the file.",
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="output.wav",
        help="Output filename (default: output.wav)",
    )

    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="./",
        help="Output directory (default: current directory)",
    )

    parser.add_argument(
        "-b",
        "--browser",
        type=str,
        default="Safari",
        help=f"Browser to capture audio from (default: Safari). Supported: {', '.join(SUPPORTED_BROWSERS)}",
    )

    parser.add_argument(
        "--bitrate",
        type=str,
        default="192k",
        help="Audio bitrate for AAC encoding (default: 192k)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        choices=[44100, 48000, 96000],
        help="Sample rate in Hz (default: 48000)",
    )

    parser.add_argument(
        "--channels",
        type=int,
        default=2,
        choices=[1, 2],
        help="Number of audio channels (default: 2 for stereo)",
    )

    parser.add_argument(
        "--list-browsers",
        action="store_true",
        help="List available browsers and exit",
    )

    args = parser.parse_args()

    # Validate and expand path
    args.path = os.path.expanduser(args.path)
    args.path = Path(args.path).resolve()

    # Ensure output directory exists
    if not args.path.exists():
        args.path.mkdir(parents=True, exist_ok=True)

    # Ensure filename ends with .wav
    if not args.name.endswith(".wav"):
        args.name = f"{args.name}.wav"

    return args


def get_output_filepath(args: argparse.Namespace) -> Path:
    """Get the full output file path."""
    return args.path / args.name





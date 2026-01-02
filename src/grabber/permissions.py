"""Permission checking for macOS Screen Recording access."""

import sys


def check_screen_capture_permission() -> bool:
    """
    Check if the current process has Screen Recording permission.
    
    Returns:
        True if permission is granted, False otherwise.
    """
    try:
        from Quartz import (
            CGPreflightScreenCaptureAccess,
            CGRequestScreenCaptureAccess,
        )
        
        # Check if we already have permission
        if CGPreflightScreenCaptureAccess():
            return True
        
        # Request permission (this will show the system dialog)
        return CGRequestScreenCaptureAccess()
        
    except ImportError:
        print("Error: Could not import Quartz framework.", file=sys.stderr)
        print("Make sure pyobjc-framework-Quartz is installed.", file=sys.stderr)
        return False


def ensure_permission() -> None:
    """
    Ensure Screen Recording permission is granted.
    
    Exits the program if permission is not granted.
    """
    print("Checking Screen Recording permission...")
    
    if not check_screen_capture_permission():
        print("\n" + "=" * 60, file=sys.stderr)
        print("PERMISSION REQUIRED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(
            "\nThis application requires Screen Recording permission to",
            file=sys.stderr,
        )
        print("capture audio from other applications.", file=sys.stderr)
        print("\nTo grant permission:", file=sys.stderr)
        print("1. Open System Settings > Privacy & Security > Screen Recording", file=sys.stderr)
        print("2. Enable access for Terminal (or your IDE)", file=sys.stderr)
        print("3. Restart the terminal and run this command again", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        sys.exit(1)
    
    print("Screen Recording permission granted.")





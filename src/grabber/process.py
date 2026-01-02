"""Process finder for locating browser applications."""

import sys
from typing import Optional
import threading

# Browser name to Bundle ID mapping
BROWSER_BUNDLE_IDS = {
    "safari": "com.apple.Safari",
    "google chrome": "com.google.Chrome",
    "chrome": "com.google.Chrome",
    "firefox": "org.mozilla.firefox",
    "microsoft edge": "com.microsoft.edgemac",
    "edge": "com.microsoft.edgemac",
    "arc": "company.thebrowser.Browser",
    "brave browser": "com.brave.Browser",
    "brave": "com.brave.Browser",
    "opera": "com.operasoftware.Opera",
    "vivaldi": "com.vivaldi.Vivaldi",
}


def get_bundle_id(browser_name: str) -> Optional[str]:
    """
    Get the bundle ID for a given browser name.
    
    Args:
        browser_name: The name of the browser (case-insensitive).
        
    Returns:
        The bundle ID string, or None if not found.
    """
    return BROWSER_BUNDLE_IDS.get(browser_name.lower())


def find_running_application(bundle_id: str) -> Optional["SCRunningApplication"]:
    """
    Find a running application by its bundle ID using ScreenCaptureKit.
    
    Args:
        bundle_id: The bundle identifier of the application.
        
    Returns:
        SCRunningApplication object if found, None otherwise.
    """
    try:
        import ScreenCaptureKit
    except ImportError:
        print("Error: Could not import ScreenCaptureKit.", file=sys.stderr)
        print("Make sure pyobjc-framework-ScreenCaptureKit is installed.", file=sys.stderr)
        return None
    
    result = {"content": None, "error": None}
    event = threading.Event()
    
    def completion_handler(content, error):
        result["content"] = content
        result["error"] = error
        event.set()
    
    # Get shareable content asynchronously
    ScreenCaptureKit.SCShareableContent.getShareableContentWithCompletionHandler_(
        completion_handler
    )
    
    # Wait for completion
    event.wait(timeout=10.0)
    
    if result["error"]:
        print(f"Error getting shareable content: {result['error']}", file=sys.stderr)
        return None
    
    content = result["content"]
    if not content:
        print("No shareable content available.", file=sys.stderr)
        return None
    
    # Search for the application by bundle ID
    applications = content.applications()
    for app in applications:
        if app.bundleIdentifier() == bundle_id:
            return app
    
    return None


def find_browser(browser_name: str) -> Optional["SCRunningApplication"]:
    """
    Find a running browser by name.
    
    Args:
        browser_name: The name of the browser to find.
        
    Returns:
        SCRunningApplication object if found, None otherwise.
    """
    bundle_id = get_bundle_id(browser_name)
    
    if not bundle_id:
        print(f"Unknown browser: {browser_name}", file=sys.stderr)
        print("Supported browsers:", file=sys.stderr)
        for name in sorted(set(BROWSER_BUNDLE_IDS.values())):
            # Find the primary name for this bundle ID
            primary_name = next(
                k for k, v in BROWSER_BUNDLE_IDS.items() if v == name and " " in k or k == k.lower()
            )
            print(f"  - {primary_name.title()}", file=sys.stderr)
        return None
    
    print(f"Looking for {browser_name} ({bundle_id})...")
    app = find_running_application(bundle_id)
    
    if not app:
        print(f"\n{browser_name} is not running.", file=sys.stderr)
        print("Please start the browser and try again.", file=sys.stderr)
        return None
    
    print(f"Found: {app.applicationName()} (PID: {app.processID()})")
    return app


def list_running_browsers() -> list[tuple[str, str, int]]:
    """
    List all running browsers that can be captured.
    
    Returns:
        List of tuples (name, bundle_id, pid) for each running browser.
    """
    try:
        import ScreenCaptureKit
    except ImportError:
        return []
    
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
        return []
    
    browsers = []
    known_bundle_ids = set(BROWSER_BUNDLE_IDS.values())
    
    for app in result["content"].applications():
        bundle_id = app.bundleIdentifier()
        if bundle_id in known_bundle_ids:
            browsers.append((
                app.applicationName(),
                bundle_id,
                app.processID(),
            ))
    
    return browsers




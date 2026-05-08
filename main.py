"""Entry point for zone-new-companion."""

import sys
import os


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, handling both dev and PyInstaller bundled modes.
    
    When running as a PyInstaller one-file bundle, sys._MEIPASS contains the
    temporary extraction directory. When running as a normal script, use the
    script's directory.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running as normal script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def set_windows_app_id():
    """Set Windows AppUserModelID for proper taskbar icon grouping.
    
    This ensures the application icon appears correctly in the Windows taskbar
    and is properly grouped with its own windows rather than generic python.exe.
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            # Use the app's identifier - this matches the executable name
            app_id = "kidpoleon.zone-new-companion.1.1.6"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            # If this fails (e.g., on older Windows), the app still works
            pass


def main():
    """Main entry point with error handling and debug mode."""
    # Set Windows AppUserModelID before any UI initialization
    set_windows_app_id()
    
    try:
        # Check for debug mode
        debug_mode = os.getenv("DEBUG", "0") == "1"
        if debug_mode:
            print("Debug mode enabled")
            os.environ["QT_LOGGING_RULES"] = "*=true"
        
        # Import and run the application
        from zone_new_companion.app import run
        run()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        if os.getenv("DEBUG", "0") == "1":
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

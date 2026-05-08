"""Entry point for zone-new-companion."""

import sys
import os
from zone_new_companion.app import run


def main():
    """Main entry point with error handling and debug mode."""
    try:
        # Check for debug mode
        debug_mode = os.getenv("DEBUG", "0") == "1"
        if debug_mode:
            print("Debug mode enabled")
            os.environ["QT_LOGGING_RULES"] = "*=true"
        
        # Run the application
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

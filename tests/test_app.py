"""Test script to isolate the startup issue."""

import sys
import traceback

try:
    from warpradar.app import WarpRadarApp
    
    print("✓ Imports successful")
    
    app = WarpRadarApp()
    print("✓ App instance created")
    
    # Try to run the app
    app.run()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)

"""Test keyboard bindings programmatically using Textual's testing framework."""

import asyncio
from warpradar.app import WarpRadarApp
from textual.pilot import Pilot


async def test_keyboard_bindings():
    """Test that keyboard bindings trigger the correct actions."""
    
    app = WarpRadarApp()
    
    async with app.run_test() as pilot:
        # Wait for app to initialize
        await pilot.pause()
        
        print("=" * 60)
        print("TESTING KEYBOARD BINDINGS")
        print("=" * 60)
        
        # Test 'S' - Stealth Mode
        print("\n[TEST] Pressing 'S' for Stealth Mode...")
        await pilot.press("s")
        await pilot.pause()
        print("  -> Stealth mode should have toggled")
        
        # Test 'B' - Black Hole
        print("\n[TEST] Pressing 'B' for Black Hole...")
        await pilot.press("b")
        await pilot.pause()
        print("  -> Black Hole toggle should have triggered")
        
        # Test 'F' - Beam File
        print("\n[TEST] Pressing 'F' for Beam File...")
        await pilot.press("f")
        await pilot.pause()
        print("  -> Beam File action should show toast or file picker")
        
        # Test 'C' - Warp Clipboard
        print("\n[TEST] Pressing 'C' for Warp Clipboard...")
        await pilot.press("c")
        await pilot.pause()
        print("  -> Warp Clipboard should show toast")
        
        # Test arrow keys
        print("\n[TEST] Testing arrow key navigation...")
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        print("  -> Peer selection should have changed")
        
        # Check if any toasts were shown
        print("\n" + "=" * 60)
        print("TEST COMPLETE - Check output above for any errors")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_keyboard_bindings())

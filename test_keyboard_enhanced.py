"""Enhanced test - capture toast messages to verify actions are triggered."""

import asyncio
import sys
sys.path.insert(0, ".")
from warpradar.app import WarpRadarApp


class TestableWarpRadarApp(WarpRadarApp):
    """Subclass that captures toast messages for testing."""
    
    def __init__(self):
        super().__init__()
        self.captured_toasts = []
    
    def _show_toast(self, message: str, msg_type: str = "info") -> None:
        """Override to capture toast messages."""
        self.captured_toasts.append((message, msg_type))
        print(f"  [TOAST] {msg_type.upper()}: {message}")
        super()._show_toast(message, msg_type)


async def test_all_bindings():
    """Test all keyboard bindings and verify toasts are shown."""
    
    app = TestableWarpRadarApp()
    
    async with app.run_test() as pilot:
        print("=" * 60)
        print("ENHANCED KEYBOARD BINDING TEST")
        print("=" * 60)
        
        # Wait for app to fully initialize
        await asyncio.sleep(1)
        
        print("\n[1] Testing STEALTH MODE (S)...")
        app.captured_toasts.clear()
        await pilot.press("s")
        await asyncio.sleep(0.5)
        if any("Stealth" in msg for msg, _ in app.captured_toasts):
            print("  ✅ Stealth mode triggered successfully!")
        else:
            print("  ❌ Stealth mode did NOT trigger")
            print(f"     Captured: {app.captured_toasts}")
        
        print("\n[2] Testing BLACK HOLE (B)...")
        app.captured_toasts.clear()
        await pilot.press("b")
        await asyncio.sleep(0.5)
        if any("Black Hole" in msg for msg, _ in app.captured_toasts):
            print("  ✅ Black Hole triggered successfully!")
        else:
            print("  ❌ Black Hole did NOT trigger")
            print(f"     Captured: {app.captured_toasts}")
        
        print("\n[3] Testing BEAM FILE (F)...")
        app.captured_toasts.clear()
        await pilot.press("f")
        await asyncio.sleep(0.5)
        if any("Beam" in msg or "peer" in msg.lower() for msg, _ in app.captured_toasts):
            print("  ✅ Beam File triggered successfully!")
        else:
            print("  ❌ Beam File did NOT trigger")
            print(f"     Captured: {app.captured_toasts}")
        
        print("\n[4] Testing WARP CLIPBOARD (C)...")
        app.captured_toasts.clear()
        await pilot.press("c")
        await asyncio.sleep(0.5)
        if any("Warp" in msg or "Clipboard" in msg or "peer" in msg.lower() for msg, _ in app.captured_toasts):
            print("  ✅ Warp Clipboard triggered successfully!")
        else:
            print("  ❌ Warp Clipboard did NOT trigger")
            print(f"     Captured: {app.captured_toasts}")
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total toasts captured throughout test: {len(app.captured_toasts)}")
        

if __name__ == "__main__":
    asyncio.run(test_all_bindings())

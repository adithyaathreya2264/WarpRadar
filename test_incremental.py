"""Incremental test to isolate the failing component."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.binding import Binding

print("[1] Testing basic imports...")

# Test each import separately
try:
    from warpradar.config import config
    print("   ✓ config")
except Exception as e:
    print(f"   ✗ config: {e}")

try:
    from warpradar.discovery.beacon import Beacon
    print("   ✓ beacon")
except Exception as e:
    print(f"   ✗ beacon: {e}")

try:
    from warpradar.discovery.listener import Listener
    print("   ✓ listener")
except Exception as e:
    print(f"   ✗ listener: {e}")

try:
    from warpradar.discovery.registry import PeerRegistry, Peer
    print("   ✓ registry")
except Exception as e:
    print(f"   ✗ registry: {e}")

try:
    from warpradar.transport.server import TransferServer
    print("   ✓ server")
except Exception as e:
    print(f"   ✗ server: {e}")

try:
    from warpradar.transport.client import send_file, push_clipboard
    print("   ✓ client")
except Exception as e:
    print(f"   ✗ client: {e}")

try:
    from warpradar.ui.radar import RadarWidget
    print("   ✓ radar widget")
except Exception as e:
    print(f"   ✗ radar widget: {e}")

try:
    from warpradar.ui.peer_list import PeerListWidget
    print("   ✓ peer_list widget")
except Exception as e:
    print(f"   ✗ peer_list widget: {e}")

try:
    from warpradar.ui.progress import ProgressWidget
    print("   ✓ progress widget")
except Exception as e:
    print(f"   ✗ progress widget: {e}")

try:
    from warpradar.ui.notifications import ToastWidget, TransferRequestModal
    print("   ✓ notifications")
except Exception as e:
    print(f"   ✗ notifications: {e}")

try:
    from warpradar.ui.file_picker import QuickFilePickerModal, FilePickerModal
    print("   ✓ file_picker")
except Exception as e:
    print(f"   ✗ file_picker: {e}")

try:
    from warpradar.utils.system import get_system_info
    print("   ✓ system")
except Exception as e:
    print(f"   ✗ system: {e}")

try:
    from warpradar.utils.clipboard import get_clipboard, set_clipboard
    print("   ✓ clipboard")
except Exception as e:
    print(f"   ✗ clipboard: {e}")

try:
    from warpradar.utils.history import TransferHistory
    print("   ✓ history")
except Exception as e:
    print(f"   ✗ history: {e}")

print("\n[2] Testing widget instantiation...")

# Minimal app class - add components one by one
class TestApp(App):
    CSS_PATH = Path(__file__).parent / "warpradar" / "ui" / "styles.tcss"
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Testing widget creation...")
        yield Footer()
    
    def on_mount(self) -> None:
        print("   ✓ on_mount called!")

print("[3] Creating app instance...")
app = TestApp()
print("   ✓ App created")

print("[4] Running app (press Q to quit)...")
app.run()
print("   ✓ App exited cleanly")

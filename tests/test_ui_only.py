"""Simplified WarpRadar - UI only, no networking for testing."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
from textual.binding import Binding

# Import only UI components
import sys
sys.path.insert(0, str(Path(__file__).parent))

from warpradar.ui.radar import RadarWidget
from warpradar.ui.peer_list import PeerListWidget
from warpradar.ui.progress import ProgressWidget
from warpradar.ui.notifications import ToastWidget
from warpradar.discovery.registry import Peer
from warpradar.utils.system import OperatingSystem


class WarpRadarTestApp(App):
    """Test version - UI only."""
    
    CSS_PATH = Path(__file__).parent / "warpradar" / "ui" / "styles.tcss"
    TITLE = "WarpRadar - UI TEST"
    
    BINDINGS = [
        Binding("t", "add_test_peer", "Add Test Peer", show=True),
        Binding("q", "quit", "Exit", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self._radar = None
        self._peer_list = None
        self._progress = None
        self._toast = None
        self._test_peers = []
    
    def compose(self) -> ComposeResult:
        """Compose the layout."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with Vertical(id="radar-panel"):
                self._radar = RadarWidget(id="radar")
                yield self._radar
            
            with Vertical(id="peer-panel"):
                self._peer_list = PeerListWidget(id="peer-list")
                yield self._peer_list
        
        with Container(id="progress-panel"):
            self._progress = ProgressWidget(id="progress")
            yield self._progress
        
        self._toast = ToastWidget(id="toast")
        yield self._toast
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize after mount."""
        if self._toast:
            self._toast.show_toast("WarpRadar UI Test - Press T to add test peers", "success")
    
    def action_add_test_peer(self) -> None:
        """Add a test peer to the display."""
        import random
        
        # Create fake peer
        peer = Peer(
            hostname=f"TEST-PC-{len(self._test_peers) + 1}",
            ip=f"192.168.1.{100 + len(self._test_peers)}",
            port=5556,
            os=random.choice(list(OperatingSystem)),
            rtt_ms=random.uniform(1, 100),
        )
        
        self._test_peers.append(peer)
        
        # Update displays
        if self._radar:
            self._radar.update_peers(self._test_peers)
        
        if self._peer_list:
            self._peer_list.update_peers(self._test_peers)
        
        if self._toast:
            self._toast.show_toast(f"Added test peer: {peer.hostname}", "info")


if __name__ == "__main__":
    app = WarpRadarTestApp()
    app.run()

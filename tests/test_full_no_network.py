"""Test WarpRadar with widgets but NO networking to isolate issue."""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.reactive import reactive

# Import everything the real app uses
from warpradar.config import config
from warpradar.ui.radar import RadarWidget
from warpradar.ui.peer_list import PeerListWidget
from warpradar.ui.progress import ProgressWidget
from warpradar.ui.notifications import ToastWidget
from warpradar.utils.system import get_system_info


class WarpRadarTestApp(App):
    """Test version with widgets, no networking."""
    
    CSS_PATH = Path(__file__).parent / "warpradar" / "ui" / "styles.tcss"
    TITLE = "WarpRadar - Test Mode"
    
    BINDINGS = [
        Binding("q", "quit", "Exit", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        print("[DEBUG] __init__ starting...")
        
        # UI components
        self._radar: Optional[RadarWidget] = None
        self._peer_list: Optional[PeerListWidget] = None
        self._progress: Optional[ProgressWidget] = None
        self._toast: Optional[ToastWidget] = None
        
        # System info
        self._system_info = get_system_info()
        print(f"[DEBUG] System info: {self._system_info.hostname} ({self._system_info.os})")
        print("[DEBUG] __init__ complete!")
    
    def compose(self) -> ComposeResult:
        print("[DEBUG] compose() starting...")
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
        print("[DEBUG] compose() complete!")
    
    def on_mount(self) -> None:
        print("[DEBUG] on_mount() starting...")
        self.title = f"WarpRadar - {self._system_info.hostname}"
        
        if self._toast:
            self._toast.show_toast(
                f"Test Mode - {self._system_info.os.icon} {self._system_info.hostname}",
                "success",
            )
        print("[DEBUG] on_mount() complete!")


if __name__ == "__main__":
    print("="*50)
    print("Starting WarpRadar Test (No Networking)")
    print("="*50)
    app = WarpRadarTestApp()
    print("[DEBUG] App instance created, running...")
    app.run()
    print("[DEBUG] App exited cleanly!")

"""Peer List Widget - Displays discovered peers with OS icons."""

from typing import List, Optional

from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.console import RenderableType
from rich.table import Table
from rich.box import ROUNDED

from ..discovery.registry import Peer
from ..config import config


class PeerListWidget(Widget):
    """Widget displaying list of discovered peers."""
    
    DEFAULT_CSS = """
    PeerListWidget {
        width: 100%;
        height: 100%;
        min-width: 30;
    }
    """
    
    selected_index: reactive[int] = reactive(0)
    
    class PeerSelected(Message):
        """Message when a peer is selected."""
        def __init__(self, peer: Optional[Peer]) -> None:
            self.peer = peer
            super().__init__()
    
    def __init__(
        self,
        name: str = None,
        id: str = None,
        classes: str = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._peers: List[Peer] = []
    
    def update_peers(self, peers: List[Peer]) -> None:
        """Update the list of peers."""
        self._peers = list(peers)
        # Ensure selected index is valid
        if self._peers:
            self.selected_index = min(self.selected_index, len(self._peers) - 1)
        else:
            self.selected_index = 0
        self.refresh()
        
        # Notify app of current selection
        self._notify_selection()
    
    def select_next(self) -> None:
        """Select next peer."""
        if self._peers:
            self.selected_index = (self.selected_index + 1) % len(self._peers)
            self._notify_selection()
    
    def select_prev(self) -> None:
        """Select previous peer."""
        if self._peers:
            self.selected_index = (self.selected_index - 1) % len(self._peers)
            self._notify_selection()
    
    def get_selected_peer(self) -> Optional[Peer]:
        """Get currently selected peer."""
        if not self._peers:
            return None
        if 0 <= self.selected_index < len(self._peers):
            return self._peers[self.selected_index]
        return None
    
    def _notify_selection(self) -> None:
        """Post selection message."""
        self.post_message(self.PeerSelected(self.get_selected_peer()))
    
    def render(self) -> RenderableType:
        """Render the peer list."""
        primary = config.ui.primary_color
        dim = config.ui.dim_color
        
        # Create table
        table = Table(
            title="[bold]NETWORK SCAN[/bold]",
            title_style=primary,
            box=ROUNDED,
            border_style=dim,
            expand=True,
            show_header=False,
            padding=(0, 1),
        )
        
        table.add_column("Icon", width=2)
        table.add_column("Hostname", ratio=1)
        table.add_column("Status", width=8)
        
        if not self._peers:
            table.add_row("", "[dim]No peers found[/dim]", "")
        else:
            for i, peer in enumerate(self._peers):
                is_selected = i == self.selected_index
                
                # OS icon
                icon = peer.os.icon
                
                # Hostname with selection indicator and port
                display_name = f"{peer.hostname}:{peer.port}"
                if is_selected:
                    hostname = f"[bold {primary}]▶ {display_name}[/bold {primary}]"
                else:
                    hostname = f"  {display_name}"
                
                # Signal strength based on RTT
                if peer.rtt_ms < 10:
                    signal = f"[{primary}]████[/{primary}]"
                elif peer.rtt_ms < 50:
                    signal = f"[{primary}]███░[/{primary}]"
                elif peer.rtt_ms < 100:
                    signal = f"[{primary}]██░░[/{primary}]"
                else:
                    signal = f"[{dim}]█░░░[/{dim}]"
                
                table.add_row(icon, hostname, signal)
        
        # Footer
        footer = Text()
        footer.append(f"\n[{len(self._peers)} peers online]", style=dim)
        
        result = Text()
        from rich.console import Console
        from io import StringIO
        
        console = Console(file=StringIO(), force_terminal=True, width=self.size.width)
        console.print(table)
        result = Text.from_ansi(console.file.getvalue())
        
        return result
    
    def watch_selected_index(self, value: int) -> None:
        """React to selection changes."""
        self.refresh()

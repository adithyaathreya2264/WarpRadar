"""Radar Widget - Animated radar display with sweep and peer blips."""

import math
import time
from typing import List, Optional, Tuple

from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.style import Style
from rich.console import RenderableType

from ..discovery.registry import Peer
from ..config import config


# Unicode characters for radar rendering
RADAR_CHARS = {
    "empty": " ",
    "ring": "·",
    "cross_h": "─",
    "cross_v": "│",
    "center": "◉",
    "blip": "●",
    "blip_selected": "◆",
    "sweep": "░",
    "sweep_bright": "▓",
}


class RadarWidget(Widget):
    """Animated radar display widget."""
    
    DEFAULT_CSS = """
    RadarWidget {
        width: 100%;
        height: 100%;
        min-width: 25;
        min-height: 15;
    }
    """
    
    # Reactive attributes
    sweep_angle = reactive(0.0)
    peers: reactive[List[Peer]] = reactive(list)
    selected_peer_id: reactive[Optional[str]] = reactive(None)
    
    class PeerSelected(Message):
        """Message sent when a peer is selected."""
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
        self._sweep_speed = config.ui.radar_sweep_speed
        self._start_time = time.time()
        self._peer_list: List[Peer] = []
    
    def on_mount(self) -> None:
        """Start the sweep animation."""
        self.set_interval(1 / config.ui.fps, self._update_sweep)
    
    def _update_sweep(self) -> None:
        """Update sweep angle for animation."""
        elapsed = time.time() - self._start_time
        self.sweep_angle = (elapsed / self._sweep_speed) * 360 % 360
    
    def update_peers(self, peers: List[Peer]) -> None:
        """Update the list of peers to display."""
        self._peer_list = peers
        self.refresh()
    
    def select_next_peer(self) -> None:
        """Select the next peer in the list."""
        if not self._peer_list:
            self.selected_peer_id = None
            return
        
        if self.selected_peer_id is None:
            self.selected_peer_id = self._peer_list[0].id
        else:
            ids = [p.id for p in self._peer_list]
            try:
                idx = ids.index(self.selected_peer_id)
                idx = (idx + 1) % len(ids)
                self.selected_peer_id = ids[idx]
            except ValueError:
                self.selected_peer_id = ids[0]
        
        self._notify_selection()
    
    def select_prev_peer(self) -> None:
        """Select the previous peer in the list."""
        if not self._peer_list:
            self.selected_peer_id = None
            return
        
        if self.selected_peer_id is None:
            self.selected_peer_id = self._peer_list[-1].id
        else:
            ids = [p.id for p in self._peer_list]
            try:
                idx = ids.index(self.selected_peer_id)
                idx = (idx - 1) % len(ids)
                self.selected_peer_id = ids[idx]
            except ValueError:
                self.selected_peer_id = ids[-1]
        
        self._notify_selection()
    
    def get_selected_peer(self) -> Optional[Peer]:
        """Get the currently selected peer."""
        if not self.selected_peer_id:
            return None
        for peer in self._peer_list:
            if peer.id == self.selected_peer_id:
                return peer
        return None
    
    def _notify_selection(self) -> None:
        """Post selection message."""
        self.post_message(self.PeerSelected(self.get_selected_peer()))
    
    def render(self) -> RenderableType:
        """Render the radar display."""
        # Get widget size
        width = self.size.width
        height = self.size.height
        
        if width < 5 or height < 5:
            return Text("...")
        
        # Calculate radar dimensions
        radius = min(width // 2 - 2, height - 2)
        center_x = width // 2
        center_y = height // 2
        
        # Create character grid
        grid = [[" " for _ in range(width)] for _ in range(height)]
        styles = [[Style() for _ in range(width)] for _ in range(height)]
        
        primary = config.ui.primary_color
        dim = config.ui.dim_color
        
        # Draw concentric rings
        for ring in range(1, radius + 1, max(1, radius // 3)):
            self._draw_circle(grid, styles, center_x, center_y, ring, dim)
        
        # Draw cross lines
        for x in range(max(0, center_x - radius), min(width, center_x + radius + 1)):
            if 0 <= center_y < height:
                if grid[center_y][x] == " ":
                    grid[center_y][x] = RADAR_CHARS["cross_h"]
                    styles[center_y][x] = Style(color=dim)
        
        for y in range(max(0, center_y - radius), min(height, center_y + radius + 1)):
            if 0 <= center_x < width:
                if grid[y][center_x] == " ":
                    grid[y][center_x] = RADAR_CHARS["cross_v"]
                    styles[y][center_x] = Style(color=dim)
        
        # Draw sweep line
        sweep_rad = math.radians(self.sweep_angle)
        for r in range(1, radius + 1):
            x = center_x + int(r * math.cos(sweep_rad) * 2)  # *2 for aspect ratio
            y = center_y - int(r * math.sin(sweep_rad))
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = RADAR_CHARS["sweep_bright"]
                styles[y][x] = Style(color=primary, bold=True)
            
            # Trail effect
            for trail in range(1, 4):
                trail_angle = sweep_rad - math.radians(trail * 5)
                tx = center_x + int(r * math.cos(trail_angle) * 2)
                ty = center_y - int(r * math.sin(trail_angle))
                if 0 <= tx < width and 0 <= ty < height:
                    if grid[ty][tx] not in [RADAR_CHARS["blip"], RADAR_CHARS["blip_selected"]]:
                        grid[ty][tx] = RADAR_CHARS["sweep"]
                        styles[ty][tx] = Style(color=dim)
        
        # Draw peer blips
        for peer in self._peer_list:
            # Position based on RTT (lower RTT = closer to center)
            # Map RTT 0-100ms to 0.2-1.0 of radius
            distance_factor = min(1.0, max(0.2, 0.2 + (peer.rtt_ms / 100) * 0.8))
            
            # Use peer identity hash for angle (consistent position)
            # Include port so local instances on same IP don't overlap
            angle = hash(peer.id) % 360
            angle_rad = math.radians(angle)
            
            r = int(radius * distance_factor)
            x = center_x + int(r * math.cos(angle_rad) * 2)
            y = center_y - int(r * math.sin(angle_rad))
            
            if 0 <= x < width and 0 <= y < height:
                is_selected = peer.id == self.selected_peer_id
                if is_selected:
                    grid[y][x] = RADAR_CHARS["blip_selected"]
                    styles[y][x] = Style(color=primary, bold=True, blink=True)
                else:
                    grid[y][x] = RADAR_CHARS["blip"]
                    styles[y][x] = Style(color=primary, bold=True)
        
        # Draw center
        if 0 <= center_x < width and 0 <= center_y < height:
            grid[center_y][center_x] = RADAR_CHARS["center"]
            styles[center_y][center_x] = Style(color=primary, bold=True)
        
        # Build Rich Text
        lines = []
        for y, row in enumerate(grid):
            line = Text()
            for x, char in enumerate(row):
                line.append(char, style=styles[y][x])
            lines.append(line)
        
        result = Text()
        for i, line in enumerate(lines):
            result.append_text(line)
            if i < len(lines) - 1:
                result.append("\n")
        
        return result
    
    def _draw_circle(
        self,
        grid: List[List[str]],
        styles: List[List[Style]],
        cx: int,
        cy: int,
        radius: int,
        color: str,
    ) -> None:
        """Draw a circle on the grid."""
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            x = cx + int(radius * math.cos(rad) * 2)  # *2 for aspect ratio
            y = cy - int(radius * math.sin(rad))
            
            if 0 <= x < len(grid[0]) and 0 <= y < len(grid):
                if grid[y][x] == " ":
                    grid[y][x] = RADAR_CHARS["ring"]
                    styles[y][x] = Style(color=color)
    
    def watch_sweep_angle(self, value: float) -> None:
        """React to sweep angle changes."""
        self.refresh()

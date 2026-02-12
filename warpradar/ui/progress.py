"""Progress Widget - Cyberpunk-styled file transfer progress bar."""

from typing import Optional

from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text
from rich.console import RenderableType

from ..transport.streamer import TransferProgress
from ..config import config


def format_bytes(bytes_count: float) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours:.0f}h {mins:.0f}m"


class ProgressWidget(Widget):
    """File transfer progress display."""
    
    DEFAULT_CSS = """
    ProgressWidget {
        width: 100%;
        height: 5;
        padding: 1;
    }
    """
    
    # Bar characters (smooth gradient)
    BAR_FULL = "█"
    BAR_75 = "▓"
    BAR_50 = "▒"
    BAR_25 = "░"
    BAR_EMPTY = "░"
    
    progress: reactive[Optional[TransferProgress]] = reactive(None)
    
    def __init__(
        self,
        name: str = None,
        id: str = None,
        classes: str = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
    
    def update_progress(self, progress: TransferProgress) -> None:
        """Update the progress display."""
        self.progress = progress
        self.refresh()
    
    def clear(self) -> None:
        """Clear the progress display."""
        self.progress = None
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the progress bar."""
        primary = config.ui.primary_color
        dim = config.ui.dim_color
        
        if not self.progress:
            return Text("", style=dim)
        
        p = self.progress
        percent = p.percent
        
        # Create text output
        result = Text()
        
        # Title line
        if p.is_complete:
            result.append("✓ WARP COMPLETE: ", style=f"bold {primary}")
        elif p.is_error:
            result.append("✗ WARP FAILED: ", style="bold red")
        else:
            result.append("⚡ WARPING: ", style=f"bold {primary}")
        
        result.append(p.filename, style="bold white")
        result.append("\n")
        
        # Progress bar
        bar_width = max(20, self.size.width - 10)
        filled = int((percent / 100) * bar_width)
        
        result.append("[")
        
        # Color gradient based on progress
        for i in range(bar_width):
            if i < filled:
                # Gradient from dim to bright
                if percent < 33:
                    color = "#ff5f00"  # Orange/red
                elif percent < 66:
                    color = "#ffff00"  # Yellow
                else:
                    color = primary  # Green
                result.append(self.BAR_FULL, style=f"{color}")
            else:
                result.append(self.BAR_EMPTY, style=dim)
        
        result.append(f"] {percent:.0f}%\n", style=primary)
        
        # Stats line
        if not p.is_complete and not p.is_error:
            speed_str = format_bytes(p.speed_bps) + "/s"
            eta_str = format_time(p.eta_seconds)
            transferred_str = format_bytes(p.transferred_bytes)
            total_str = format_bytes(p.total_bytes)
            
            result.append(f"Speed: {speed_str}", style=primary)
            result.append(" │ ", style=dim)
            result.append(f"ETA: {eta_str}", style=primary)
            result.append(" │ ", style=dim)
            result.append(f"{transferred_str}/{total_str}", style=primary)
        elif p.is_error:
            result.append(f"Error: {p.error_message}", style="red")
        else:
            # Complete
            speed_str = format_bytes(p.speed_bps) + "/s"
            total_str = format_bytes(p.total_bytes)
            result.append(f"Transferred: {total_str} @ {speed_str}", style=primary)
        
        return result
    
    def watch_progress(self, value: Optional[TransferProgress]) -> None:
        """React to progress changes."""
        self.refresh()

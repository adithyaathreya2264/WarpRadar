"""Toast Notifications - Modal popups for incoming transfers."""

from typing import Callable, Optional, Awaitable

from textual.widget import Widget
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button
from textual.reactive import reactive
from textual.app import ComposeResult
from rich.text import Text
from rich.panel import Panel
from rich.console import RenderableType

from ..config import config
from ..utils.format import format_bytes as format_size


class TransferRequestModal(ModalScreen):
    """Modal screen for incoming transfer request."""
    
    CSS = """
    TransferRequestModal {
        align: center middle;
    }
    
    #dialog {
        width: 50;
        height: 12;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    
    #info {
        margin-bottom: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    .btn-accept {
        background: #005f00;
        color: #00ff41;
        text-style: bold;
        min-width: 16;
        margin: 0 2;
    }

    .btn-reject {
        background: #5f0000;
        color: #ff5f00;
        text-style: bold;
        min-width: 16;
        margin: 0 2;
    }
    """
    
    def __init__(
        self,
        filename: str,
        filesize: int,
        sender: str,
    ) -> None:
        super().__init__()
        self.filename = filename
        self.filesize = filesize
        self.sender = sender
        self.accepted = False
    
    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        primary = config.ui.primary_color
        
        with Container(id="dialog"):
            yield Static(" INCOMING TRANSMISSION", id="title")
            yield Static(
                f"From: [bold]{self.sender}[/bold]\n"
                f"File: [bold]{self.filename}[/bold]\n"
                f"Size: [bold]{format_size(self.filesize)}[/bold]",
                id="info",
            )
            with Horizontal(id="buttons"):
                yield Button("[Y] Accept", classes="btn-accept", id="accept")
                yield Button("[N] Reject", classes="btn-reject", id="reject")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.accepted = event.button.id == "accept"
        self.dismiss(self.accepted)
    
    def key_y(self) -> None:
        """Accept with Y key."""
        self.accepted = True
        self.dismiss(True)
    
    def key_n(self) -> None:
        """Reject with N key."""
        self.accepted = False
        self.dismiss(False)
    
    def key_escape(self) -> None:
        """Reject with Escape."""
        self.accepted = False
        self.dismiss(False)


class ToastWidget(Widget):
    """Toast notification display."""
    
    DEFAULT_CSS = """
    ToastWidget {
        dock: bottom;
        width: 100%;
        height: 3;
        background: $surface;
        border-top: solid $primary;
        padding: 0 2;
        layer: above;
    }
    """
    
    message: reactive[str] = reactive("")
    message_type: reactive[str] = reactive("info")  # info, success, warning, error
    
    def __init__(
        self,
        name: str = None,
        id: str = None,
        classes: str = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._visible = False
        self._hide_timer = None
    
    def show_toast(
        self,
        message: str,
        message_type: str = "info",
        duration: float = 3.0,
    ) -> None:
        """Show a toast notification."""
        self.message = message
        self.message_type = message_type
        self._visible = True
        self.refresh()
        
        # Auto-hide after duration
        if self._hide_timer:
            self._hide_timer.stop()
        self._hide_timer = self.set_timer(duration, self._hide)
    
    def _hide(self) -> None:
        """Hide the toast."""
        self._visible = False
        self.message = ""
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the toast."""
        if not self._visible or not self.message:
            return Text("")
        
        # Style based on type
        styles = {
            "info": config.ui.primary_color,
            "success": config.ui.primary_color,
            "warning": config.ui.warning_color,
            "error": "red",
        }
        
        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        
        color = styles.get(self.message_type, config.ui.primary_color)
        icon = icons.get(self.message_type, "•")
        
        text = Text()
        text.append(f"{icon} ", style=f"bold {color}")
        text.append(self.message, style=color)
        
        return text
    
    def watch_message(self, value: str) -> None:
        """React to message changes."""
        self.refresh()

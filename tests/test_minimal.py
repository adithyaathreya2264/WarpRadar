"""Minimal test - TUI only, no networking."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from pathlib import Path


class MinimalApp(App):
    """Minimal test app."""
    
    CSS_PATH = Path(__file__).parent / "warpradar" / "ui" / "styles.tcss"
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("WarpRadar Test - No networking")
        yield Footer()


if __name__ == "__main__":
    app = MinimalApp()
    app.run()

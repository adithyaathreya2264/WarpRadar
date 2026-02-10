"""File Selection Dialog - File picker for sending files."""

from pathlib import Path
from typing import List, Optional

from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, Button, DirectoryTree, Input, Label
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.message import Message


class FilePickerModal(ModalScreen):
    """Modal screen for selecting a file to send."""
    
    CSS = """
    FilePickerModal {
        align: center middle;
    }
    
    #file-dialog {
        width: 80;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #current-path {
        color: $primary;
        margin-bottom: 1;
    }
    
    #file-tree {
        height: 18;
        border: solid $primary;
        margin-bottom: 1;
        overflow-y: auto;
    }
    
    #selected-file {
        color: $warning;
        margin-bottom: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 2;
    }
    """
    
    selected_path: reactive[Optional[Path]] = reactive(None)
    
    def __init__(self, start_path: Path = None) -> None:
        super().__init__()
        self.start_path = start_path or Path.home()
        self._tree: Optional[DirectoryTree] = None
    
    def compose(self) -> ComposeResult:
        """Compose the file picker layout."""
        with Container(id="file-dialog"):
            yield Static("📁 SELECT FILE TO BEAM", id="title")
            yield Static(f"Path: {self.start_path}", id="current-path")
            
            # File tree
            self._tree = DirectoryTree(str(self.start_path), id="file-tree")
            yield self._tree
            
            yield Static("Selected: None", id="selected-file")
            
            with Horizontal(id="buttons"):
                yield Button("Send", variant="success", id="send")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection from tree."""
        self.selected_path = Path(event.path)
        self.query_one("#selected-file", Static).update(
            f"Selected: [bold]{self.selected_path.name}[/bold] ({self._format_size(self.selected_path.stat().st_size)})"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "send":
            if self.selected_path and self.selected_path.is_file():
                self.dismiss(self.selected_path)
            else:
                # Show error - no file selected
                self.query_one("#selected-file", Static).update(
                    "⚠ Please select a file"
                )
        else:
            self.dismiss(None)
    
    def key_escape(self) -> None:
        """Cancel with Escape."""
        self.dismiss(None)
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size as human-readable."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class SimpleFilePickerModal(ModalScreen):
    """Simplified file picker using text input (fallback)."""
    
    CSS = """
    SimpleFilePickerModal {
        align: center middle;
    }
    
    #simple-dialog {
        width: 60;
        height: 12;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #instructions {
        color: $primary;
        margin-bottom: 1;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 2;
    }
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._input: Optional[Input] = None
    
    def compose(self) -> ComposeResult:
        """Compose the simple file picker."""
        with Container(id="simple-dialog"):
            yield Static("📁 ENTER FILE PATH", id="title")
            yield Static(
                "Enter the full path to the file you want to send:",
                id="instructions",
            )
            
            self._input = Input(placeholder="e.g., C:\\Users\\Documents\\file.pdf")
            yield self._input
            
            with Horizontal(id="buttons"):
                yield Button("Send", variant="success", id="send")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        if self._input:
            self._input.focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "send":
            if self._input and self._input.value:
                file_path = Path(self._input.value)
                if file_path.is_file():
                    self.dismiss(file_path)
                else:
                    # Show error
                    self._input.value = ""
                    self._input.placeholder = "⚠ File not found - try again"
            else:
                self._input.placeholder = "⚠ Please enter a file path"
        else:
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        if event.value:
            file_path = Path(event.value)
            if file_path.is_file():
                self.dismiss(file_path)
            else:
                self._input.value = ""
                self._input.placeholder = "⚠ File not found - try again"
    
    def key_escape(self) -> None:
        """Cancel with Escape."""
        self.dismiss(None)


class QuickFilePickerModal(ModalScreen):
    """Quick file picker showing recent/common directories."""
    
    CSS = """
    QuickFilePickerModal {
        align: center middle;
    }
    
    #quick-dialog {
        width: 70;
        height: 20;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .location-button {
        width: 100%;
        margin: 0 0 1 0;
    }
    
    #custom-path {
        margin-top: 1;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 2;
    }
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._selected_dir: Optional[Path] = None
        self._input: Optional[Input] = None
    
    def compose(self) -> ComposeResult:
        """Compose the quick picker."""
        with Container(id="quick-dialog"):
            yield Static("📁 SELECT FILE LOCATION", id="title")
            
            with VerticalScroll():
                # Quick access locations
                yield Button("📂 Desktop", classes="location-button", id="desktop")
                yield Button("📥 Downloads", classes="location-button", id="downloads")
                yield Button("📄 Documents", classes="location-button", id="documents")
                yield Button("🖼️ Pictures", classes="location-button", id="pictures")
                yield Button("🏠 Home", classes="location-button", id="home")
            
            yield Static("Or enter custom path:", id="custom-path")
            self._input = Input(placeholder="Enter file path...")
            yield self._input
            
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_id = event.button.id
        
        if button_id == "cancel":
            self.dismiss(None)
        elif button_id == "desktop":
            self._selected_dir = Path.home() / "Desktop"
            self._open_full_picker()
        elif button_id == "downloads":
            self._selected_dir = Path.home() / "Downloads"
            self._open_full_picker()
        elif button_id == "documents":
            self._selected_dir = Path.home() / "Documents"
            self._open_full_picker()
        elif button_id == "pictures":
            self._selected_dir = Path.home() / "Pictures"
            self._open_full_picker()
        elif button_id == "home":
            self._selected_dir = Path.home()
            self._open_full_picker()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in custom path input."""
        if event.value:
            path = Path(event.value)
            if path.is_file():
                self.dismiss(path)
            elif path.is_dir():
                self._selected_dir = path
                self._open_full_picker()
            else:
                self._input.value = ""
                self._input.placeholder = "⚠ Path not found"
    
    def _open_full_picker(self) -> None:
        """Open the full file picker at selected directory."""
        # Dismiss this modal and signal to open full picker
        self.dismiss(self._selected_dir)
    
    def key_escape(self) -> None:
        """Cancel with Escape."""
        self.dismiss(None)

"""Debug logger that writes to a file for TUI apps."""

import os
from pathlib import Path
from datetime import datetime

# Log file location
LOG_FILE = Path.home() / "warpradar_debug.log"

# TUI mode flag — when True, suppress stdout output to avoid corrupting the Textual terminal rendering.
_TUI_MODE = False


def set_tui_mode(enabled: bool) -> None:
    """Enable or disable TUI mode (suppresses stdout output)."""
    global _TUI_MODE
    _TUI_MODE = enabled


def debug_log(message: str) -> None:
    """Write a debug message to the log file."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {message}\n"
    
    # Only print to stdout when NOT in TUI mode
    if not _TUI_MODE:
        print(line, end="")
    
    # Append to log file
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def clear_log() -> None:
    """Clear the log file."""
    try:
        LOG_FILE.unlink(missing_ok=True)
    except Exception:
        pass

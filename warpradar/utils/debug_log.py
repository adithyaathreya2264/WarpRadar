"""Debug logger that writes to a file for TUI apps."""

import os
from pathlib import Path
from datetime import datetime

# Log file location
LOG_FILE = Path.home() / "warpradar_debug.log"


def debug_log(message: str) -> None:
    """Write a debug message to the log file."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {message}\n"
    
    # Also print to stdout for non-TUI contexts
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

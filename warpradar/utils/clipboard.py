"""Cross-platform clipboard utilities."""

import pyperclip


def get_clipboard() -> str:
    """Get current clipboard content as text."""
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def set_clipboard(text: str) -> bool:
    """Set clipboard content."""
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False

"""Shared formatting utilities — deduplicated from multiple UI modules."""


def format_bytes(bytes_count: float) -> str:
    """Format bytes as human-readable string (e.g. '1.5 MB')."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def format_speed(bps: float) -> str:
    """Format bytes-per-second as human-readable speed string."""
    return format_bytes(bps) + "/s"


def format_duration(seconds: float) -> str:
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

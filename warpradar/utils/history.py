"""Transfer History - Logging and tracking file transfers."""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class TransferRecord:
    """Record of a single file transfer."""
    
    timestamp: str  # ISO format
    direction: str  # "sent" or "received"
    filename: str
    filesize: int
    peer_hostname: str
    peer_ip: str
    success: bool
    duration_seconds: float
    speed_bps: float  # Bytes per second
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "TransferRecord":
        """Create from dictionary."""
        return cls(**data)
    
    def format_size(self) -> str:
        """Format filesize as human-readable."""
        size = self.filesize
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def format_speed(self) -> str:
        """Format speed as human-readable."""
        speed = self.speed_bps
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"
    
    def format_duration(self) -> str:
        """Format duration as human-readable."""
        seconds = self.duration_seconds
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
    
    def __str__(self) -> str:
        """String representation."""
        direction = "→" if self.direction == "sent" else "←"
        status = "✓" if self.success else "✗"
        return (
            f"{status} {direction} {self.filename} "
            f"({self.format_size()}) "
            f"{self.format_speed()} "
            f"{self.peer_hostname}"
        )


class TransferHistory:
    """Manages transfer history log."""
    
    def __init__(self, history_file: Path = None):
        """
        Initialize transfer history.
        
        Args:
            history_file: Path to history JSON file
        """
        if history_file is None:
            history_file = Path.home() / "WarpDownloads" / ".warpradar_history.json"
        
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._records: List[TransferRecord] = []
        self._load()
    
    def _load(self) -> None:
        """Load history from file."""
        if not self.history_file.exists():
            self._records = []
            return
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._records = [
                    TransferRecord.from_dict(record) for record in data
                ]
        except Exception:
            # If file is corrupted, start fresh
            self._records = []
    
    def _save(self) -> None:
        """Save history to file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                data = [record.to_dict() for record in self._records]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            # Silently fail if can't save
            pass
    
    def add_transfer(
        self,
        direction: str,
        filename: str,
        filesize: int,
        peer_hostname: str,
        peer_ip: str,
        success: bool,
        duration_seconds: float,
        speed_bps: float,
        error_message: Optional[str] = None,
    ) -> TransferRecord:
        """
        Add a transfer record.
        
        Args:
            direction: "sent" or "received"
            filename: Name of the file
            filesize: File size in bytes
            peer_hostname: Peer's hostname
            peer_ip: Peer's IP address
            success: Whether transfer succeeded
            duration_seconds: Transfer duration
            speed_bps: Average transfer speed
            error_message: Error message if failed
        
        Returns:
            The created TransferRecord
        """
        record = TransferRecord(
            timestamp=datetime.now().isoformat(),
            direction=direction,
            filename=filename,
            filesize=filesize,
            peer_hostname=peer_hostname,
            peer_ip=peer_ip,
            success=success,
            duration_seconds=duration_seconds,
            speed_bps=speed_bps,
            error_message=error_message,
        )
        
        self._records.append(record)
        self._save()
        
        return record
    
    def get_recent(self, count: int = 10) -> List[TransferRecord]:
        """Get most recent transfers."""
        return self._records[-count:]
    
    def get_all(self) -> List[TransferRecord]:
        """Get all transfer records."""
        return list(self._records)
    
    def get_sent(self) -> List[TransferRecord]:
        """Get all sent transfers."""
        return [r for r in self._records if r.direction == "sent"]
    
    def get_received(self) -> List[TransferRecord]:
        """Get all received transfers."""
        return [r for r in self._records if r.direction == "received"]
    
    def get_successful(self) -> List[TransferRecord]:
        """Get all successful transfers."""
        return [r for r in self._records if r.success]
    
    def get_failed(self) -> List[TransferRecord]:
        """Get all failed transfers."""
        return [r for r in self._records if not r.success]
    
    def clear(self) -> None:
        """Clear all history."""
        self._records = []
        self._save()
    
    @property
    def total_sent_bytes(self) -> int:
        """Total bytes sent."""
        return sum(
            r.filesize for r in self._records
            if r.direction == "sent" and r.success
        )
    
    @property
    def total_received_bytes(self) -> int:
        """Total bytes received."""
        return sum(
            r.filesize for r in self._records
            if r.direction == "received" and r.success
        )
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if not self._records:
            return 100.0
        successful = sum(1 for r in self._records if r.success)
        return (successful / len(self._records)) * 100.0

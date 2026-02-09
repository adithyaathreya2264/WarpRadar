"""File integrity verification using SHA-256 checksums."""

import hashlib
from pathlib import Path
from typing import BinaryIO, Optional


CHUNK_SIZE = 65536  # 64KB chunks for hashing


def compute_checksum(file_path: Path) -> str:
    """
    Compute SHA-256 checksum of a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Hex-encoded SHA-256 hash
    """
    sha256 = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    
    return sha256.hexdigest()


def compute_checksum_streaming(data: bytes) -> str:
    """
    Compute SHA-256 checksum of bytes.
    
    Args:
        data: Bytes to hash
    
    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(data).hexdigest()


class StreamingChecksum:
    """Computes checksum incrementally during streaming."""
    
    def __init__(self):
        """Initialize the streaming checksum calculator."""
        self._hasher = hashlib.sha256()
        self._total_bytes = 0
    
    def update(self, data: bytes) -> None:
        """
        Add more data to the checksum calculation.
        
        Args:
            data: Bytes to add
        """
        self._hasher.update(data)
        self._total_bytes += len(data)
    
    def hexdigest(self) -> str:
        """Get the final hex-encoded checksum."""
        return self._hasher.hexdigest()
    
    @property
    def total_bytes(self) -> int:
        """Total bytes processed."""
        return self._total_bytes
    
    def verify(self, expected: str) -> bool:
        """
        Verify the checksum matches expected value.
        
        Args:
            expected: Expected hex-encoded checksum
        
        Returns:
            True if checksums match
        """
        return self.hexdigest().lower() == expected.lower()

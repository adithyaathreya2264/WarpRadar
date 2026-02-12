"""System utilities for OS detection and hostname."""

import platform
import socket
from enum import Enum
from dataclasses import dataclass


class OperatingSystem(Enum):
    """Supported operating systems."""
    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"  # macOS
    UNKNOWN = "unknown"
    
    @classmethod
    def detect(cls) -> "OperatingSystem":
        """Detect the current operating system."""
        system = platform.system().lower()
        if system == "windows":
            return cls.WINDOWS
        elif system == "linux":
            return cls.LINUX
        elif system == "darwin":
            return cls.DARWIN
        return cls.UNKNOWN
    
    @property
    def icon(self) -> str:
        """Get Unicode icon for this OS."""
        icons = {
            OperatingSystem.WINDOWS: "🪟",
            OperatingSystem.LINUX: "🐧",
            OperatingSystem.DARWIN: "🍎",
            OperatingSystem.UNKNOWN: "❓",
        }
        return icons.get(self, "❓")


@dataclass
class SystemInfo:
    """System information container."""
    hostname: str
    os: OperatingSystem
    local_ip: str
    
    @classmethod
    def gather(cls) -> "SystemInfo":
        """Gather system information."""
        hostname = socket.gethostname()
        os_type = OperatingSystem.detect()
        
        # Get local IP address
        local_ip = cls._get_local_ip()
        
        return cls(hostname=hostname, os=os_type, local_ip=local_ip)
    
    @staticmethod
    def _get_local_ip() -> str:
        """Get the local IP address used for LAN communication."""
        try:
            # Create a socket and connect to an external address
            # This doesn't actually send data, just determines the local interface
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# Singleton instance
_system_info: SystemInfo | None = None


def get_system_info() -> SystemInfo:
    """Get cached system information."""
    global _system_info
    if _system_info is None:
        _system_info = SystemInfo.gather()
    return _system_info

"""WarpRadar Configuration Management."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NetworkConfig:
    """Network-related configuration."""
    
    # UDP Multicast settings
    multicast_group: str = os.getenv("WARPRADAR_MULTICAST_GROUP", "224.0.0.1")
    multicast_port: int = int(os.getenv("WARPRADAR_MULTICAST_PORT", "5555"))
    beacon_interval: float = 2.0  # seconds
    peer_timeout: float = 10.0  # seconds before peer is considered offline
    
    # TCP settings
    tcp_port: int = int(os.getenv("WARPRADAR_TCP_PORT", "5556"))
    chunk_size: int = 4096  # 4KB chunks for file transfer
    max_parallel_connections: int = 4


@dataclass
class UIConfig:
    """UI-related configuration."""
    
    # Colors (Neon Green theme)
    primary_color: str = "#00ff41"
    background_color: str = "#0d0d0d"
    dim_color: str = "#005f00"
    accent_color: str = "#00ff41"
    warning_color: str = "#ff5f00"
    
    # Radar settings
    radar_sweep_speed: float = 3.0  # seconds per revolution
    radar_size: int = 21  # character width/height
    
    # Animation
    fps: int = 30


@dataclass
class Config:
    """Main configuration container."""
    
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Paths
    download_dir: Path = field(default_factory=lambda: Path.home() / "WarpDownloads")
    drop_zone_dir: Optional[Path] = None  # Black Hole feature
    
    # Identity
    hostname: Optional[str] = None
    
    # Features
    stealth_mode: bool = False
    
    def __post_init__(self):
        """Initialize derived values."""
        if self.hostname is None:
            import socket
            self.hostname = socket.gethostname()
        
        # Ensure download directory exists
        self.download_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()

"""Peer Registry - Tracks discovered peers with TTL management."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
from ..utils.system import OperatingSystem


@dataclass
class Peer:
    """Represents a discovered network peer."""
    
    hostname: str
    ip: str
    port: int
    os: OperatingSystem
    last_seen: float = field(default_factory=time.time)
    rtt_ms: float = 0.0  # Round-trip time for distance calculation
    
    @property
    def id(self) -> str:
        """Unique identifier for this peer."""
        return f"{self.ip}:{self.port}"
    
    @property
    def age(self) -> float:
        """Seconds since last seen."""
        return time.time() - self.last_seen
    
    def update(self, rtt_ms: float = 0.0) -> None:
        """Update last seen time and RTT."""
        self.last_seen = time.time()
        self.rtt_ms = rtt_ms
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Peer):
            return False
        return self.id == other.id


class PeerRegistry:
    """Thread-safe registry of discovered peers with automatic expiration."""
    
    def __init__(
        self,
        timeout: float = 10.0,
        on_peer_added: Optional[Callable[[Peer], None]] = None,
        on_peer_removed: Optional[Callable[[Peer], None]] = None,
        on_peer_updated: Optional[Callable[[Peer], None]] = None,
    ):
        """
        Initialize the peer registry.
        
        Args:
            timeout: Seconds after which a peer is considered offline
            on_peer_added: Callback when a new peer is discovered
            on_peer_removed: Callback when a peer goes offline
            on_peer_updated: Callback when a peer's info is updated
        """
        self._peers: Dict[str, Peer] = {}
        self._lock = asyncio.Lock()
        self._timeout = timeout
        self._on_peer_added = on_peer_added
        self._on_peer_removed = on_peer_removed
        self._on_peer_updated = on_peer_updated
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self) -> None:
        """Periodically remove expired peers."""
        while True:
            await asyncio.sleep(1.0)
            await self._cleanup_expired()
    
    async def _cleanup_expired(self) -> None:
        """Remove peers that haven't been seen recently."""
        async with self._lock:
            expired = [
                peer_id for peer_id, peer in self._peers.items()
                if peer.age > self._timeout
            ]
            for peer_id in expired:
                peer = self._peers.pop(peer_id)
                if self._on_peer_removed:
                    self._on_peer_removed(peer)
    
    async def update_peer(
        self,
        hostname: str,
        ip: str,
        port: int,
        os: OperatingSystem,
        rtt_ms: float = 0.0,
    ) -> Peer:
        """
        Add or update a peer in the registry.
        
        Returns:
            The added or updated Peer object
        """
        peer_id = f"{ip}:{port}"
        
        async with self._lock:
            if peer_id in self._peers:
                # Update existing peer
                peer = self._peers[peer_id]
                peer.hostname = hostname
                peer.os = os
                peer.update(rtt_ms)
                if self._on_peer_updated:
                    self._on_peer_updated(peer)
            else:
                # Add new peer
                peer = Peer(
                    hostname=hostname,
                    ip=ip,
                    port=port,
                    os=os,
                    rtt_ms=rtt_ms,
                )
                self._peers[peer_id] = peer
                if self._on_peer_added:
                    self._on_peer_added(peer)
            
            return peer
    
    async def remove_peer(self, ip: str, port: int) -> Optional[Peer]:
        """Remove a peer from the registry."""
        peer_id = f"{ip}:{port}"
        
        async with self._lock:
            if peer_id in self._peers:
                peer = self._peers.pop(peer_id)
                if self._on_peer_removed:
                    self._on_peer_removed(peer)
                return peer
        return None
    
    async def get_peer(self, ip: str, port: int) -> Optional[Peer]:
        """Get a peer by IP and port."""
        peer_id = f"{ip}:{port}"
        async with self._lock:
            return self._peers.get(peer_id)
    
    async def get_all_peers(self) -> list[Peer]:
        """Get all active peers."""
        async with self._lock:
            return list(self._peers.values())
    
    @property
    def peer_count(self) -> int:
        """Number of active peers."""
        return len(self._peers)

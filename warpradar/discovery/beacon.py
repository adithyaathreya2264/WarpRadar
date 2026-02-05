"""Beacon - UDP Multicast heartbeat broadcaster."""

import asyncio
import socket
import struct
import time
from typing import Optional

from ..config import config
from ..utils.system import get_system_info, OperatingSystem


# Packet format:
# | Magic (4B) | Version (1B) | MsgType (1B) | OS (1B) | Port (2B) | Hostname (32B) |
# Total: 41 bytes
MAGIC = b"WARP"
PROTOCOL_VERSION = 1
MSG_TYPE_HEARTBEAT = 0x01
MSG_TYPE_GOODBYE = 0x02
HOSTNAME_MAX_LEN = 32
PACKET_FORMAT = "!4sBBBH32s"  # Network byte order (big-endian)
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)


def _os_to_byte(os: OperatingSystem) -> int:
    """Convert OperatingSystem enum to byte value."""
    mapping = {
        OperatingSystem.WINDOWS: 0x01,
        OperatingSystem.LINUX: 0x02,
        OperatingSystem.DARWIN: 0x03,
        OperatingSystem.UNKNOWN: 0x00,
    }
    return mapping.get(os, 0x00)


def _byte_to_os(byte: int) -> OperatingSystem:
    """Convert byte value to OperatingSystem enum."""
    mapping = {
        0x01: OperatingSystem.WINDOWS,
        0x02: OperatingSystem.LINUX,
        0x03: OperatingSystem.DARWIN,
    }
    return mapping.get(byte, OperatingSystem.UNKNOWN)


def create_heartbeat_packet(
    hostname: str,
    os: OperatingSystem,
    tcp_port: int,
) -> bytes:
    """Create a heartbeat packet for broadcasting."""
    # Encode and pad/truncate hostname
    hostname_bytes = hostname.encode("utf-8")[:HOSTNAME_MAX_LEN]
    hostname_padded = hostname_bytes.ljust(HOSTNAME_MAX_LEN, b"\x00")
    
    return struct.pack(
        PACKET_FORMAT,
        MAGIC,
        PROTOCOL_VERSION,
        MSG_TYPE_HEARTBEAT,
        _os_to_byte(os),
        tcp_port,
        hostname_padded,
    )


def create_goodbye_packet(
    hostname: str,
    os: OperatingSystem,
    tcp_port: int,
) -> bytes:
    """Create a goodbye packet for graceful shutdown."""
    hostname_bytes = hostname.encode("utf-8")[:HOSTNAME_MAX_LEN]
    hostname_padded = hostname_bytes.ljust(HOSTNAME_MAX_LEN, b"\x00")
    
    return struct.pack(
        PACKET_FORMAT,
        MAGIC,
        PROTOCOL_VERSION,
        MSG_TYPE_GOODBYE,
        _os_to_byte(os),
        tcp_port,
        hostname_padded,
    )


def parse_packet(data: bytes) -> Optional[dict]:
    """
    Parse a received packet.
    
    Returns:
        Dictionary with hostname, os, port, msg_type or None if invalid
    """
    if len(data) < PACKET_SIZE:
        return None
    
    try:
        magic, version, msg_type, os_byte, port, hostname_bytes = struct.unpack(
            PACKET_FORMAT, data[:PACKET_SIZE]
        )
        
        if magic != MAGIC:
            return None
        
        if version != PROTOCOL_VERSION:
            return None
        
        # Decode and strip null bytes from hostname
        hostname = hostname_bytes.rstrip(b"\x00").decode("utf-8", errors="replace")
        
        return {
            "hostname": hostname,
            "os": _byte_to_os(os_byte),
            "port": port,
            "msg_type": msg_type,
        }
    except (struct.error, UnicodeDecodeError):
        return None


class Beacon:
    """UDP Multicast beacon broadcaster."""
    
    def __init__(
        self,
        multicast_group: str = None,
        multicast_port: int = None,
        tcp_port: int = None,
        interval: float = None,
    ):
        """
        Initialize the beacon.
        
        Args:
            multicast_group: Multicast IP address
            multicast_port: Multicast port
            tcp_port: Local TCP port for file transfers
            interval: Broadcast interval in seconds
        """
        self._multicast_group = multicast_group or config.network.multicast_group
        self._multicast_port = multicast_port or config.network.multicast_port
        self._tcp_port = tcp_port or config.network.tcp_port
        self._interval = interval or config.network.beacon_interval
        
        self._socket: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._enabled = True  # Can be disabled for stealth mode
        
        # System info
        self._system_info = get_system_info()
    
    async def start(self) -> None:
        """Start the beacon broadcaster."""
        if self._running:
            return
        
        self._running = True
        self._create_socket()
        self._task = asyncio.create_task(self._broadcast_loop())
    
    async def stop(self) -> None:
        """Stop the beacon and send goodbye packet."""
        if not self._running:
            return
        
        self._running = False
        
        # Send goodbye packet
        if self._enabled and self._socket:
            goodbye = create_goodbye_packet(
                self._system_info.hostname,
                self._system_info.os,
                self._tcp_port,
            )
            try:
                self._socket.sendto(
                    goodbye,
                    (self._multicast_group, self._multicast_port),
                )
            except Exception:
                pass
        
        # Cancel the broadcast task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Close socket
        if self._socket:
            self._socket.close()
            self._socket = None
    
    def enable(self) -> None:
        """Enable broadcasting (exit stealth mode)."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable broadcasting (enter stealth mode)."""
        self._enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """Whether broadcasting is enabled."""
        return self._enabled
    
    def _create_socket(self) -> None:
        """Create the UDP multicast socket."""
        self._socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )
        
        # Set TTL for multicast
        self._socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            2,  # Allow multicast to pass through one router
        )
        
        # Allow reuse of address
        self._socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )
    
    async def _broadcast_loop(self) -> None:
        """Main broadcast loop."""
        while self._running:
            if self._enabled:
                await self._send_heartbeat()
            await asyncio.sleep(self._interval)
    
    async def _send_heartbeat(self) -> None:
        """Send a single heartbeat packet."""
        if not self._socket:
            return
        
        packet = create_heartbeat_packet(
            self._system_info.hostname,
            self._system_info.os,
            self._tcp_port,
        )
        
        try:
            # Run blocking socket operation in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._socket.sendto,
                packet,
                (self._multicast_group, self._multicast_port),
            )
        except Exception:
            # Silently ignore send errors
            pass

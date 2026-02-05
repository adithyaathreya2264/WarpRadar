"""Listener - UDP Multicast listener for peer discovery."""

import asyncio
import socket
import struct
import time
from typing import Callable, Optional

from ..config import config
from ..utils.system import get_system_info
from .beacon import parse_packet, MSG_TYPE_HEARTBEAT, MSG_TYPE_GOODBYE
from .registry import PeerRegistry, Peer


class Listener:
    """UDP Multicast listener for discovering peers."""
    
    def __init__(
        self,
        registry: PeerRegistry,
        multicast_group: str = None,
        multicast_port: int = None,
    ):
        """
        Initialize the listener.
        
        Args:
            registry: Peer registry to update with discoveries
            multicast_group: Multicast IP address
            multicast_port: Multicast port
        """
        self._registry = registry
        self._multicast_group = multicast_group or config.network.multicast_group
        self._multicast_port = multicast_port or config.network.multicast_port
        
        self._socket: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        # Our own identity (to filter out our own broadcasts)
        self._system_info = get_system_info()
    
    async def start(self) -> None:
        """Start listening for peer broadcasts."""
        if self._running:
            return
        
        self._running = True
        self._create_socket()
        self._task = asyncio.create_task(self._listen_loop())
    
    async def stop(self) -> None:
        """Stop the listener."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._socket:
            self._socket.close()
            self._socket = None
    
    def _create_socket(self) -> None:
        """Create and configure the multicast listener socket."""
        self._socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )
        
        # Allow reuse of address
        self._socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )
        
        # Bind to the multicast port
        self._socket.bind(("", self._multicast_port))
        
        # Join the multicast group
        mreq = struct.pack(
            "4sl",
            socket.inet_aton(self._multicast_group),
            socket.INADDR_ANY,
        )
        self._socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq,
        )
        
        # Set non-blocking
        self._socket.setblocking(False)
    
    async def _listen_loop(self) -> None:
        """Main listening loop."""
        loop = asyncio.get_event_loop()
        
        while self._running:
            try:
                # Wait for data with timeout
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, self._receive_packet),
                    timeout=1.0,
                )
                
                if data:
                    receive_time = time.time()
                    await self._handle_packet(data, addr, receive_time)
                    
            except asyncio.TimeoutError:
                # No data received, continue loop
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                # Log errors but continue
                await asyncio.sleep(0.1)
    
    def _receive_packet(self) -> tuple[bytes, tuple[str, int]]:
        """Receive a packet (blocking, run in executor)."""
        try:
            return self._socket.recvfrom(1024)
        except BlockingIOError:
            return None, None
        except Exception:
            return None, None
    
    async def _handle_packet(
        self,
        data: bytes,
        addr: tuple[str, int],
        receive_time: float,
    ) -> None:
        """Process a received packet."""
        if not data:
            return
        
        parsed = parse_packet(data)
        if not parsed:
            return
        
        sender_ip = addr[0]
        
        # Filter out our own broadcasts
        if self._is_self(sender_ip, parsed["port"]):
            return
        
        msg_type = parsed["msg_type"]
        
        if msg_type == MSG_TYPE_HEARTBEAT:
            # Update or add peer
            await self._registry.update_peer(
                hostname=parsed["hostname"],
                ip=sender_ip,
                port=parsed["port"],
                os=parsed["os"],
                rtt_ms=0.0,  # Could calculate RTT if we had send timestamp
            )
        elif msg_type == MSG_TYPE_GOODBYE:
            # Remove peer
            await self._registry.remove_peer(sender_ip, parsed["port"])
    
    def _is_self(self, ip: str, port: int) -> bool:
        """Check if the packet is from ourselves."""
        # Check if IP matches our local IP and port matches our TCP port
        return (
            ip == self._system_info.local_ip
            and port == config.network.tcp_port
        )

"""TCP Handshake - Connection establishment with encryption setup."""

import asyncio
from typing import Optional, Tuple, Callable, Awaitable
from dataclasses import dataclass

from .protocol import (
    MessageHeader, MessageType, HEADER_SIZE,
    HandshakeRequest, HandshakeAck, HandshakeNak,
)
from ..security.crypto import (
    generate_keypair, compute_shared_secret, derive_session_key,
    public_key_to_bytes, bytes_to_public_key, SessionCrypto, KeyPair,
)
from ..security.integrity import compute_checksum
from ..utils.debug_log import debug_log
from pathlib import Path


@dataclass
class TransferSession:
    """Active file transfer session."""
    peer_ip: str
    peer_port: int
    filename: str
    filesize: int
    checksum: str
    crypto: SessionCrypto
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    is_sender: bool


async def send_message(
    writer: asyncio.StreamWriter,
    msg_type: MessageType,
    payload: bytes,
) -> None:
    """Send a protocol message."""
    header = MessageHeader(msg_type=msg_type, payload_length=len(payload))
    writer.write(header.pack() + payload)
    await writer.drain()


async def receive_message(
    reader: asyncio.StreamReader,
    timeout: float = 120.0,
) -> Tuple[Optional[MessageType], Optional[bytes]]:
    """Receive a protocol message."""
    try:
        # Read header
        header_data = await asyncio.wait_for(
            reader.readexactly(HEADER_SIZE),
            timeout=timeout,
        )
        
        header = MessageHeader.unpack(header_data)
        if not header:
            return None, None
        
        # Read payload
        if header.payload_length > 0:
            payload = await asyncio.wait_for(
                reader.readexactly(header.payload_length),
                timeout=timeout,
            )
        else:
            payload = b""
        
        return header.msg_type, payload
    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
        return None, None


async def initiate_file_transfer(
    peer_ip: str,
    peer_port: int,
    file_path: Path,
) -> Optional[TransferSession]:
    """
    Initiate a file transfer to a peer.
    
    Args:
        peer_ip: Peer's IP address
        peer_port: Peer's TCP port
        file_path: Path to file to send
    
    Returns:
        TransferSession if handshake successful, None otherwise
    """
    try:
        # Connect to peer
        debug_log(f"[HANDSHAKE] Attempting connection to {peer_ip}:{peer_port}...")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port),
            timeout=120.0,
        )
        debug_log(f"[HANDSHAKE] Connected successfully!")
        
        # Generate our DH keypair
        keypair = generate_keypair()
        
        # Compute file checksum
        checksum = compute_checksum(file_path)
        debug_log(f"[HANDSHAKE] Checksum computed, sending request...")
        
        # Create handshake request
        request = HandshakeRequest(
            filename=file_path.name,
            filesize=file_path.stat().st_size,
            checksum=checksum,
            public_key=public_key_to_bytes(keypair.public_key),
        )
        
        # Send handshake request
        await send_message(writer, MessageType.HANDSHAKE_REQ, request.pack())
        debug_log(f"[HANDSHAKE] Request sent, waiting for response...")
        
        # Wait for response
        msg_type, payload = await receive_message(reader)
        debug_log(f"[HANDSHAKE] Got response: msg_type={msg_type}, payload_len={len(payload) if payload else 0}")
        
        if msg_type == MessageType.HANDSHAKE_ACK:
            debug_log(f"[HANDSHAKE] Received ACK, parsing...")
            # Parse ACK
            ack = HandshakeAck.unpack(payload)
            if not ack:
                debug_log(f"[HANDSHAKE] Failed to parse ACK payload!")
                writer.close()
                await writer.wait_closed()
                return None
            
            # Compute shared secret and session key
            their_public_key = bytes_to_public_key(ack.public_key)
            shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
            session_key = derive_session_key(shared_secret)
            debug_log(f"[HANDSHAKE] Session key derived, transfer ready!")
            
            return TransferSession(
                peer_ip=peer_ip,
                peer_port=peer_port,
                filename=file_path.name,
                filesize=file_path.stat().st_size,
                checksum=checksum,
                crypto=SessionCrypto(session_key),
                reader=reader,
                writer=writer,
                is_sender=True,
            )
        
        elif msg_type == MessageType.HANDSHAKE_NAK:
            nak = HandshakeNak.unpack(payload)
            debug_log(f"[HANDSHAKE] Received NAK - transfer REJECTED! Reason: {nak.reason if nak else 'unknown'}")
            # Transfer rejected
            writer.close()
            await writer.wait_closed()
            return None
        
        else:
            debug_log(f"[HANDSHAKE] Unexpected response type: {msg_type}")
            writer.close()
            await writer.wait_closed()
            return None
            
    except Exception as e:
        debug_log(f"[HANDSHAKE ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def handle_incoming_transfer(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    accept_callback: Callable[[str, int, str], Awaitable[bool]],
) -> Optional[TransferSession]:
    """
    Handle an incoming file transfer request.
    
    Args:
        reader: Stream reader
        writer: Stream writer
        accept_callback: Async function(filename, filesize, hostname) -> bool
    
    Returns:
        TransferSession if accepted, None otherwise
    """
    try:
        # Receive handshake request
        msg_type, payload = await receive_message(reader)
        
        if msg_type != MessageType.HANDSHAKE_REQ:
            return None
        
        request = HandshakeRequest.unpack(payload)
        if not request:
            return None
        
        # Get peer info
        peer_addr = writer.get_extra_info("peername")
        peer_ip = peer_addr[0] if peer_addr else "unknown"
        
        # Ask for user acceptance
        accepted = await accept_callback(request.filename, request.filesize, peer_ip)
        
        if not accepted:
            # Send rejection
            nak = HandshakeNak(reason="User rejected transfer")
            await send_message(writer, MessageType.HANDSHAKE_NAK, nak.pack())
            writer.close()
            await writer.wait_closed()
            return None
        
        # Generate our DH keypair
        keypair = generate_keypair()
        
        # Send ACK with our public key
        ack = HandshakeAck(public_key=public_key_to_bytes(keypair.public_key))
        await send_message(writer, MessageType.HANDSHAKE_ACK, ack.pack())
        
        # Compute shared secret and session key
        their_public_key = bytes_to_public_key(request.public_key)
        shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
        session_key = derive_session_key(shared_secret)
        
        return TransferSession(
            peer_ip=peer_ip,
            peer_port=peer_addr[1] if peer_addr else 0,
            filename=request.filename,
            filesize=request.filesize,
            checksum=request.checksum,
            crypto=SessionCrypto(session_key),
            reader=reader,
            writer=writer,
            is_sender=False,
        )
        
    except Exception:
        return None

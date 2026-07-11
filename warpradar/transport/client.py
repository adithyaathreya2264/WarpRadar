"""TCP Client - Initiates file transfers, clipboard pushes, and chat messages."""

import asyncio
import os
from pathlib import Path
from typing import Callable, Optional, Awaitable

from .protocol import MessageType, ChatMessage
from .handshake import (
    TransferSession, initiate_file_transfer,
    send_message, receive_message,
)
from .streamer import stream_file_send, TransferProgress
from ..security.crypto import (
    generate_keypair, compute_shared_secret, derive_session_key,
    public_key_to_bytes, bytes_to_public_key, SessionCrypto,
)
from ..utils.debug_log import debug_log


async def send_file(
    peer_ip: str,
    peer_port: int,
    file_path: Path,
    progress_callback: Optional[Callable[[TransferProgress], Awaitable[None]]] = None,
) -> bool:
    """
    Send a file to a peer.
    
    Args:
        peer_ip: Peer's IP address
        peer_port: Peer's TCP port
        file_path: Path to file to send
        progress_callback: Optional progress callback
    
    Returns:
        True if transfer successful
    """
    debug_log(f"[CLIENT] Starting file transfer to {peer_ip}:{peer_port}")
    debug_log(f"[CLIENT] File: {file_path} ({file_path.stat().st_size} bytes)")
    
    # Initiate handshake
    session = await initiate_file_transfer(peer_ip, peer_port, file_path)
    
    if not session:
        debug_log("[CLIENT] Handshake failed - no session returned")
        return False
    
    debug_log("[CLIENT] Handshake successful, starting file stream...")
    
    try:
        # Stream the file
        success = await stream_file_send(
            session=session,
            file_path=file_path,
            progress_callback=progress_callback,
        )
        debug_log(f"[CLIENT] Stream complete, success={success}")
        return success
    except Exception as e:
        debug_log(f"[CLIENT ERROR] Stream failed: {type(e).__name__}: {e}")
        return False
    finally:
        # Close connection
        try:
            session.writer.close()
            await session.writer.wait_closed()
        except Exception:
            pass


async def push_clipboard(
    peer_ip: str,
    peer_port: int,
    text: str,
) -> bool:
    """
    Push clipboard content to a peer with proper DH key exchange.
    
    Protocol:
        1. Client sends CLIPBOARD_PUSH with DH public key (256 bytes)
        2. Server responds with CLIPBOARD_ACK containing its DH public key
        3. Both sides derive shared session key
        4. Client sends CLIPBOARD_DATA with AES-256-GCM encrypted text
    
    Args:
        peer_ip: Peer's IP address
        peer_port: Peer's TCP port
        text: Text content to push
    
    Returns:
        True if push successful
    """
    try:
        # Connect to peer
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port),
            timeout=10.0,
        )
        
        # Step 1: Generate our DH keypair + random salt, send both
        keypair = generate_keypair()
        salt = os.urandom(16)
        await send_message(
            writer,
            MessageType.CLIPBOARD_PUSH,
            public_key_to_bytes(keypair.public_key) + salt,
        )
        
        # Step 2: Wait for server's public key in ACK
        msg_type, response = await receive_message(reader, timeout=10.0)
        if msg_type != MessageType.CLIPBOARD_ACK or not response or len(response) < 256:
            debug_log("[CLIENT] Clipboard DH exchange failed - bad ACK")
            writer.close()
            await writer.wait_closed()
            return False
        
        their_public_key = bytes_to_public_key(response[:256])
        
        # Step 3: Derive shared session key using the same salt
        shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
        session_key = derive_session_key(shared_secret, salt)
        crypto = SessionCrypto(session_key)
        
        # Step 4: Encrypt and send clipboard content
        text_bytes = text.encode("utf-8")
        encrypted = crypto.encrypt(text_bytes)
        
        await send_message(
            writer,
            MessageType.CLIPBOARD_DATA,
            encrypted,
        )
        
        writer.close()
        await writer.wait_closed()
        return True
        
    except Exception as e:
        debug_log(f"[CLIENT] Clipboard push failed: {type(e).__name__}: {e}")
        return False


async def send_chat_message(
    peer_ip: str,
    peer_port: int,
    sender_hostname: str,
    text: str,
) -> bool:
    """
    Send an encrypted chat message to a peer with DH key exchange.
    
    Protocol:
        1. Client sends MESSAGE_PUSH with DH public key (256 bytes)
        2. Server responds with MESSAGE_ACK containing its DH public key
        3. Both sides derive shared session key
        4. Client sends MESSAGE_DATA with AES-256-GCM encrypted ChatMessage
    
    Args:
        peer_ip: Peer's IP address
        peer_port: Peer's TCP port
        sender_hostname: Our hostname (shown to receiver)
        text: Message text

    Returns:
        True if message delivered successfully
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port),
            timeout=10.0,
        )
        
        # Step 1: Generate DH keypair + random salt, send both
        keypair = generate_keypair()
        salt = os.urandom(16)
        await send_message(
            writer,
            MessageType.MESSAGE_PUSH,
            public_key_to_bytes(keypair.public_key) + salt,
        )
        
        # Step 2: Wait for server's DH public key in ACK
        msg_type, response = await receive_message(reader, timeout=10.0)
        if msg_type != MessageType.MESSAGE_ACK or not response or len(response) < 256:
            debug_log("[CLIENT] Chat DH exchange failed - bad ACK")
            writer.close()
            await writer.wait_closed()
            return False
        
        their_public_key = bytes_to_public_key(response[:256])
        
        # Step 3: Derive shared session key using the same salt
        shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
        session_key = derive_session_key(shared_secret, salt)
        crypto = SessionCrypto(session_key)
        
        # Step 4: Encrypt the ChatMessage and send
        msg = ChatMessage(sender=sender_hostname, text=text)
        encrypted = crypto.encrypt(msg.pack())
        
        await send_message(writer, MessageType.MESSAGE_DATA, encrypted)

        writer.close()
        await writer.wait_closed()
        return True
    except Exception as e:
        debug_log(f"[CLIENT] Chat message failed: {type(e).__name__}: {e}")
        return False

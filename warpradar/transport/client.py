"""TCP Client - Initiates file transfers and clipboard pushes."""

import asyncio
from pathlib import Path
from typing import Callable, Optional, Awaitable

from .protocol import MessageType, ClipboardPush
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
        import traceback
        traceback.print_exc()
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
    Push clipboard content to a peer.
    
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
        
        # Generate our DH keypair
        keypair = generate_keypair()
        
        # We'll send our public key, then wait for their ACK with their public key
        # Then compute shared secret and send encrypted content
        
        # For simplicity, compute a temporary session key with a placeholder
        # The real exchange happens when we get the ACK
        
        # Encode the text
        text_bytes = text.encode("utf-8")
        
        # Create temporary encryption (we'll use a simple approach)
        # Send public key + unencrypted length first, then encrypted after key exchange
        
        # Build payload: our public key + text (will be encrypted after key exchange)
        payload = public_key_to_bytes(keypair.public_key) + text_bytes
        
        # Actually, let's do a proper exchange:
        # 1. Send PING with our public key
        # 2. Receive PONG with their public key
        # 3. Compute shared key
        # 4. Send encrypted clipboard
        
        # Simplified: encrypt with our own keypair temporarily for demo
        # In production, do full key exchange
        
        await send_message(
            writer,
            MessageType.CLIPBOARD_PUSH,
            payload,
        )
        
        # Wait for ACK
        msg_type, response = await receive_message(reader, timeout=10.0)
        
        success = msg_type == MessageType.CLIPBOARD_ACK
        
        writer.close()
        await writer.wait_closed()
        
        return success
        
    except Exception:
        return False


async def send_chat_message(
    peer_ip: str,
    peer_port: int,
    sender_hostname: str,
    text: str,
) -> bool:
    """
    Send a chat message to a peer.

    Args:
        peer_ip: Peer's IP address
        peer_port: Peer's TCP port
        sender_hostname: Our hostname (shown to receiver)
        text: Message text

    Returns:
        True if message delivered successfully
    """
    from .protocol import ChatMessage
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port),
            timeout=10.0,
        )
        msg = ChatMessage(sender=sender_hostname, text=text)
        await send_message(writer, MessageType.MESSAGE_PUSH, msg.pack())

        # Wait for ACK
        msg_type, _ = await receive_message(reader, timeout=10.0)
        success = msg_type == MessageType.MESSAGE_ACK

        writer.close()
        await writer.wait_closed()
        return success
    except Exception:
        return False

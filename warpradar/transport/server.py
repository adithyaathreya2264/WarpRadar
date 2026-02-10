"""TCP Server - Listens for incoming file transfer and clipboard requests."""

import asyncio
from typing import Callable, Optional, Awaitable
from pathlib import Path

from .protocol import MessageType, ClipboardPush
from .handshake import (
    TransferSession, handle_incoming_transfer,
    send_message, receive_message,
)
from .streamer import stream_file_receive, TransferProgress
from ..security.crypto import (
    generate_keypair, compute_shared_secret, derive_session_key,
    public_key_to_bytes, bytes_to_public_key, SessionCrypto,
)
from ..config import config


class TransferServer:
    """TCP server for receiving file transfers and clipboard data."""
    
    def __init__(
        self,
        port: int = None,
        download_dir: Path = None,
        on_transfer_request: Optional[Callable[[str, int, str], Awaitable[bool]]] = None,
        on_transfer_progress: Optional[Callable[[TransferProgress], Awaitable[None]]] = None,
        on_transfer_complete: Optional[Callable[[Path], Awaitable[None]]] = None,
        on_clipboard_received: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Initialize the transfer server.
        
        Args:
            port: TCP port to listen on
            download_dir: Directory to save received files
            on_transfer_request: Callback(filename, size, peer_ip) -> accept?
            on_transfer_progress: Callback for progress updates
            on_transfer_complete: Callback when transfer completes
            on_clipboard_received: Callback when clipboard data received
        """
        self._port = port or config.network.tcp_port
        self._download_dir = download_dir or config.download_dir
        self._on_transfer_request = on_transfer_request
        self._on_transfer_progress = on_transfer_progress
        self._on_transfer_complete = on_transfer_complete
        self._on_clipboard_received = on_clipboard_received
        
        self._server: Optional[asyncio.Server] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the TCP server."""
        if self._running:
            return
        
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self._port,
        )
    
    async def stop(self) -> None:
        """Stop the TCP server."""
        if not self._running:
            return
        
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
    
    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port
    
    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming connection."""
        try:
            # Peek at the first message to determine type
            msg_type, payload = await receive_message(reader, timeout=30.0)
            
            if msg_type == MessageType.HANDSHAKE_REQ:
                # File transfer request - need to reprocess with handshake
                await self._handle_file_transfer(reader, writer, msg_type, payload)
            
            elif msg_type == MessageType.CLIPBOARD_PUSH:
                await self._handle_clipboard(reader, writer, payload)
            
            elif msg_type == MessageType.PING:
                # Respond with pong
                await send_message(writer, MessageType.PONG, b"")
            
        except Exception as e:
            print(f"[SERVER ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Only close if not a file transfer (file transfer manages its own cleanup)
            if msg_type != MessageType.HANDSHAKE_REQ:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
    
    async def _handle_file_transfer(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        msg_type: MessageType,
        payload: bytes,
    ) -> None:
        """Handle incoming file transfer."""
        from .protocol import HandshakeRequest, HandshakeAck, HandshakeNak
        from ..utils.debug_log import debug_log
        
        debug_log(f"[SERVER] Handling file transfer request...")
        
        # Parse the request we already received
        request = HandshakeRequest.unpack(payload)
        if not request:
            debug_log(f"[SERVER] Failed to parse handshake request!")
            return
        
        debug_log(f"[SERVER] Request: {request.filename} ({request.filesize} bytes)")
        
        peer_addr = writer.get_extra_info("peername")
        peer_ip = peer_addr[0] if peer_addr else "unknown"
        
        # Default accept callback
        async def default_accept(filename: str, size: int, ip: str) -> bool:
            return True
        
        accept_callback = self._on_transfer_request or default_accept
        
        # Ask for user acceptance
        debug_log(f"[SERVER] Calling accept callback...")
        try:
            accepted = await accept_callback(request.filename, request.filesize, peer_ip)
            debug_log(f"[SERVER] Accept callback returned: {accepted}")
        except Exception as e:
            debug_log(f"[SERVER] Accept callback EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            accepted = False
        
        if not accepted:
            debug_log(f"[SERVER] Sending NAK...")
            nak = HandshakeNak(reason="User rejected transfer")
            await send_message(writer, MessageType.HANDSHAKE_NAK, nak.pack())
            return
        
        # Generate our DH keypair
        keypair = generate_keypair()
        
        # Send ACK with our public key
        ack = HandshakeAck(public_key=public_key_to_bytes(keypair.public_key))
        await send_message(writer, MessageType.HANDSHAKE_ACK, ack.pack())
        
        # Compute shared secret and session key
        their_public_key = bytes_to_public_key(request.public_key)
        shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
        session_key = derive_session_key(shared_secret)
        
        # Create session
        session = TransferSession(
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
        
        # Receive the file
        try:
            print(f"[SERVER] Starting file receive: {request.filename}")
            saved_path = await stream_file_receive(
                session=session,
                output_dir=self._download_dir,
                progress_callback=self._on_transfer_progress,
            )
            
            if saved_path:
                print(f"[SERVER] File saved to: {saved_path}")
                if self._on_transfer_complete:
                    await self._on_transfer_complete(saved_path)
            else:
                print(f"[SERVER] File receive failed!")
        except Exception as e:
            print(f"[SERVER TRANSFER ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Close connection after transfer
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    async def _handle_clipboard(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        payload: bytes,
    ) -> None:
        """Handle incoming clipboard push."""
        # For clipboard, we need a simpler key exchange
        # The payload contains DH public key + encrypted content
        if len(payload) < 256:
            return
        
        their_public_key_bytes = payload[:256]
        encrypted_content = payload[256:]
        
        # Generate our keypair and compute shared secret
        keypair = generate_keypair()
        their_public_key = bytes_to_public_key(their_public_key_bytes)
        shared_secret = compute_shared_secret(keypair.private_key, their_public_key)
        session_key = derive_session_key(shared_secret)
        
        # Send our public key as ACK
        await send_message(
            writer,
            MessageType.CLIPBOARD_ACK,
            public_key_to_bytes(keypair.public_key),
        )
        
        # Decrypt the clipboard content
        crypto = SessionCrypto(session_key)
        try:
            decrypted = crypto.decrypt(encrypted_content)
            clipboard_text = decrypted.decode("utf-8")
            
            if self._on_clipboard_received:
                await self._on_clipboard_received(clipboard_text)
        except Exception:
            pass

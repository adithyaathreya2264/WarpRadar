"""File Streamer - High-performance encrypted file streaming."""

import asyncio
from pathlib import Path
from typing import Callable, Optional, Awaitable
from dataclasses import dataclass

from .protocol import (
    MessageType, DataChunk, DataComplete,
)
from .handshake import TransferSession, send_message, receive_message
from ..security.integrity import StreamingChecksum
from ..config import config


@dataclass
class TransferProgress:
    """Transfer progress information."""
    filename: str
    total_bytes: int
    transferred_bytes: int
    speed_bps: float  # Bytes per second
    eta_seconds: float
    is_complete: bool
    is_error: bool
    error_message: str = ""
    
    @property
    def percent(self) -> float:
        """Completion percentage."""
        if self.total_bytes == 0:
            return 100.0
        return (self.transferred_bytes / self.total_bytes) * 100.0


async def stream_file_send(
    session: TransferSession,
    file_path: Path,
    progress_callback: Optional[Callable[[TransferProgress], Awaitable[None]]] = None,
    chunk_size: int = None,
) -> bool:
    """
    Stream a file to a peer with encryption.
    
    Args:
        session: Active transfer session
        file_path: Path to file to send
        progress_callback: Optional async callback for progress updates
        chunk_size: Bytes per chunk (default from config)
    
    Returns:
        True if transfer successful
    """
    if chunk_size is None:
        chunk_size = config.network.chunk_size
    
    total_bytes = file_path.stat().st_size
    transferred = 0
    sequence = 0
    checksum = StreamingChecksum()
    
    import time
    start_time = time.time()
    last_progress_time = start_time
    
    try:
        with open(file_path, "rb") as f:
            while True:
                # Read chunk
                data = f.read(chunk_size)
                if not data:
                    break
                
                # Update checksum
                checksum.update(data)
                
                # Encrypt chunk
                encrypted = session.crypto.encrypt(data)
                
                # Send chunk
                chunk = DataChunk(sequence=sequence, data=encrypted)
                await send_message(
                    session.writer,
                    MessageType.DATA_CHUNK,
                    chunk.pack(),
                )
                
                sequence += 1
                transferred += len(data)
                
                # Progress update
                current_time = time.time()
                if progress_callback and (current_time - last_progress_time >= 0.1):
                    elapsed = current_time - start_time
                    speed = transferred / elapsed if elapsed > 0 else 0
                    remaining = total_bytes - transferred
                    eta = remaining / speed if speed > 0 else 0
                    
                    progress = TransferProgress(
                        filename=file_path.name,
                        total_bytes=total_bytes,
                        transferred_bytes=transferred,
                        speed_bps=speed,
                        eta_seconds=eta,
                        is_complete=False,
                        is_error=False,
                    )
                    await progress_callback(progress)
                    last_progress_time = current_time
                
                # Yield to event loop
                await asyncio.sleep(0)
        
        # Send completion message
        complete = DataComplete(
            total_chunks=sequence,
            final_checksum=checksum.hexdigest(),
        )
        await send_message(
            session.writer,
            MessageType.DATA_COMPLETE,
            complete.pack(),
        )
        
        # Final progress update
        if progress_callback:
            elapsed = time.time() - start_time
            speed = transferred / elapsed if elapsed > 0 else 0
            
            progress = TransferProgress(
                filename=file_path.name,
                total_bytes=total_bytes,
                transferred_bytes=transferred,
                speed_bps=speed,
                eta_seconds=0,
                is_complete=True,
                is_error=False,
            )
            await progress_callback(progress)
        
        return True
        
    except Exception as e:
        if progress_callback:
            progress = TransferProgress(
                filename=file_path.name,
                total_bytes=total_bytes,
                transferred_bytes=transferred,
                speed_bps=0,
                eta_seconds=0,
                is_complete=False,
                is_error=True,
                error_message=str(e),
            )
            await progress_callback(progress)
        return False


async def stream_file_receive(
    session: TransferSession,
    output_dir: Path,
    progress_callback: Optional[Callable[[TransferProgress], Awaitable[None]]] = None,
) -> Optional[Path]:
    """
    Receive a streamed file with decryption.
    
    Args:
        session: Active transfer session
        output_dir: Directory to save file
        progress_callback: Optional async callback for progress updates
    
    Returns:
        Path to saved file, or None if failed
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / session.filename
    
    # Handle duplicate filenames
    counter = 1
    stem = output_path.stem
    suffix = output_path.suffix
    while output_path.exists():
        output_path = output_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    total_bytes = session.filesize
    received = 0
    checksum = StreamingChecksum()
    expected_sequence = 0
    
    import time
    start_time = time.time()
    last_progress_time = start_time
    
    try:
        with open(output_path, "wb") as f:
            while True:
                msg_type, payload = await receive_message(session.reader, timeout=60.0)
                
                if msg_type == MessageType.DATA_CHUNK:
                    chunk = DataChunk.unpack(payload)
                    if not chunk:
                        raise ValueError("Invalid chunk data")
                    
                    # Verify sequence
                    if chunk.sequence != expected_sequence:
                        raise ValueError(f"Sequence mismatch: expected {expected_sequence}, got {chunk.sequence}")
                    
                    # Decrypt
                    decrypted = session.crypto.decrypt(chunk.data)
                    
                    # Write and update checksum
                    f.write(decrypted)
                    checksum.update(decrypted)
                    
                    received += len(decrypted)
                    expected_sequence += 1
                    
                    # Progress update
                    current_time = time.time()
                    if progress_callback and (current_time - last_progress_time >= 0.1):
                        elapsed = current_time - start_time
                        speed = received / elapsed if elapsed > 0 else 0
                        remaining = total_bytes - received
                        eta = remaining / speed if speed > 0 else 0
                        
                        progress = TransferProgress(
                            filename=session.filename,
                            total_bytes=total_bytes,
                            transferred_bytes=received,
                            speed_bps=speed,
                            eta_seconds=eta,
                            is_complete=False,
                            is_error=False,
                        )
                        await progress_callback(progress)
                        last_progress_time = current_time
                
                elif msg_type == MessageType.DATA_COMPLETE:
                    complete = DataComplete.unpack(payload)
                    if not complete:
                        raise ValueError("Invalid completion data")
                    
                    # Verify checksum
                    if not checksum.verify(complete.final_checksum):
                        raise ValueError("Checksum mismatch - file corrupted")
                    
                    break
                
                elif msg_type == MessageType.DATA_CANCEL:
                    raise ValueError("Transfer cancelled by sender")
                
                else:
                    raise ValueError(f"Unexpected message type: {msg_type}")
        
        # Final progress update
        if progress_callback:
            elapsed = time.time() - start_time
            speed = received / elapsed if elapsed > 0 else 0
            
            progress = TransferProgress(
                filename=session.filename,
                total_bytes=total_bytes,
                transferred_bytes=received,
                speed_bps=speed,
                eta_seconds=0,
                is_complete=True,
                is_error=False,
            )
            await progress_callback(progress)
        
        return output_path
        
    except Exception as e:
        # Clean up partial file
        if output_path.exists():
            output_path.unlink()
        
        if progress_callback:
            progress = TransferProgress(
                filename=session.filename,
                total_bytes=total_bytes,
                transferred_bytes=received,
                speed_bps=0,
                eta_seconds=0,
                is_complete=False,
                is_error=True,
                error_message=str(e),
            )
            await progress_callback(progress)
        
        return None

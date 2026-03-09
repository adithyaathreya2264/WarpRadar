"""Binary Protocol Definitions for TCP communication."""

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class MessageType(IntEnum):
    """Message types for the WarpRadar protocol."""
    
    # Handshake messages
    HANDSHAKE_REQ = 0x01  # Request to send file
    HANDSHAKE_ACK = 0x02  # Accept file transfer
    HANDSHAKE_NAK = 0x03  # Reject file transfer
    
    # Data transfer messages
    DATA_CHUNK = 0x10     # File data chunk
    DATA_COMPLETE = 0x11  # Transfer complete
    DATA_CANCEL = 0x12    # Cancel transfer
    
    # Clipboard messages
    CLIPBOARD_PUSH = 0x20  # Push clipboard content
    CLIPBOARD_ACK = 0x21   # Clipboard received
    
    # Utility messages
    PING = 0x30           # Ping peer
    PONG = 0x31           # Pong response
    
    # Chat messages
    MESSAGE_PUSH = 0x40   # Send a chat message
    MESSAGE_ACK  = 0x41   # Chat message received


# Header format: | Magic (4B) | Version (1B) | MsgType (1B) | Length (4B) |
# Total: 10 bytes
HEADER_FORMAT = "!4sBBI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAGIC = b"WARP"
PROTOCOL_VERSION = 1


@dataclass
class MessageHeader:
    """Protocol message header."""
    msg_type: MessageType
    payload_length: int
    
    def pack(self) -> bytes:
        """Pack header into bytes."""
        return struct.pack(
            HEADER_FORMAT,
            MAGIC,
            PROTOCOL_VERSION,
            self.msg_type,
            self.payload_length,
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["MessageHeader"]:
        """Unpack header from bytes."""
        if len(data) < HEADER_SIZE:
            return None
        
        try:
            magic, version, msg_type, length = struct.unpack(
                HEADER_FORMAT, data[:HEADER_SIZE]
            )
            
            if magic != MAGIC:
                return None
            
            if version != PROTOCOL_VERSION:
                return None
            
            return cls(
                msg_type=MessageType(msg_type),
                payload_length=length,
            )
        except (struct.error, ValueError):
            return None


@dataclass
class HandshakeRequest:
    """File transfer handshake request."""
    filename: str
    filesize: int
    checksum: str  # SHA-256 hex
    public_key: bytes  # DH public key (256 bytes)
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        filename_bytes = self.filename.encode("utf-8")[:255]
        checksum_bytes = self.checksum.encode("ascii")[:64]
        
        # Format: filename_len (1B) + filename + filesize (8B) + checksum (64B) + pubkey (256B)
        return struct.pack(
            f"!B{len(filename_bytes)}sQ64s256s",
            len(filename_bytes),
            filename_bytes,
            self.filesize,
            checksum_bytes.ljust(64, b"\x00"),
            self.public_key,
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["HandshakeRequest"]:
        """Unpack from payload bytes."""
        try:
            filename_len = data[0]
            offset = 1
            
            filename = data[offset:offset + filename_len].decode("utf-8")
            offset += filename_len
            
            filesize = struct.unpack("!Q", data[offset:offset + 8])[0]
            offset += 8
            
            checksum = data[offset:offset + 64].rstrip(b"\x00").decode("ascii")
            offset += 64
            
            public_key = data[offset:offset + 256]
            
            return cls(
                filename=filename,
                filesize=filesize,
                checksum=checksum,
                public_key=public_key,
            )
        except (struct.error, UnicodeDecodeError, IndexError):
            return None


@dataclass
class HandshakeAck:
    """File transfer handshake acknowledgment."""
    public_key: bytes  # DH public key (256 bytes)
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        return self.public_key
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["HandshakeAck"]:
        """Unpack from payload bytes."""
        if len(data) < 256:
            return None
        return cls(public_key=data[:256])


@dataclass
class HandshakeNak:
    """File transfer handshake rejection."""
    reason: str
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        reason_bytes = self.reason.encode("utf-8")[:255]
        return struct.pack(f"!B{len(reason_bytes)}s", len(reason_bytes), reason_bytes)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["HandshakeNak"]:
        """Unpack from payload bytes."""
        try:
            reason_len = data[0]
            reason = data[1:1 + reason_len].decode("utf-8")
            return cls(reason=reason)
        except (IndexError, UnicodeDecodeError):
            return None


@dataclass
class DataChunk:
    """File data chunk (encrypted)."""
    sequence: int
    data: bytes  # Encrypted chunk data
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        return struct.pack(f"!I{len(self.data)}s", self.sequence, self.data)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["DataChunk"]:
        """Unpack from payload bytes."""
        try:
            sequence = struct.unpack("!I", data[:4])[0]
            chunk_data = data[4:]
            return cls(sequence=sequence, data=chunk_data)
        except struct.error:
            return None


@dataclass 
class DataComplete:
    """Transfer completion message."""
    total_chunks: int
    final_checksum: str
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        checksum_bytes = self.final_checksum.encode("ascii")[:64]
        return struct.pack(f"!I64s", self.total_chunks, checksum_bytes.ljust(64, b"\x00"))
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["DataComplete"]:
        """Unpack from payload bytes."""
        try:
            total_chunks = struct.unpack("!I", data[:4])[0]
            checksum = data[4:68].rstrip(b"\x00").decode("ascii")
            return cls(total_chunks=total_chunks, final_checksum=checksum)
        except (struct.error, UnicodeDecodeError):
            return None


@dataclass
class ClipboardPush:
    """Push clipboard content to peer."""
    content: bytes  # Encrypted clipboard text
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        return self.content
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["ClipboardPush"]:
        """Unpack from payload bytes."""
        return cls(content=data)


@dataclass
class ChatMessage:
    """A chat message sent between peers."""
    sender: str   # Sender hostname
    text: str     # Message text
    
    def pack(self) -> bytes:
        """Pack into payload bytes."""
        sender_bytes = self.sender.encode("utf-8")[:64]
        text_bytes = self.text.encode("utf-8")[:1024]
        return struct.pack(
            f"!B{len(sender_bytes)}sH{len(text_bytes)}s",
            len(sender_bytes),
            sender_bytes,
            len(text_bytes),
            text_bytes,
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional["ChatMessage"]:
        """Unpack from payload bytes."""
        try:
            sender_len = data[0]
            offset = 1
            sender = data[offset:offset + sender_len].decode("utf-8")
            offset += sender_len
            text_len = struct.unpack("!H", data[offset:offset + 2])[0]
            offset += 2
            text = data[offset:offset + text_len].decode("utf-8")
            return cls(sender=sender, text=text)
        except (IndexError, struct.error, UnicodeDecodeError):
            return None

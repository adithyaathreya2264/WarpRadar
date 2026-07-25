"""Tests for binary protocol message pack/unpack roundtrips."""

import os
from warpradar.transport.protocol import (
    MessageHeader, MessageType,
    HandshakeRequest, HandshakeAck, HandshakeNak,
    DataChunk, DataComplete, ClipboardPush, ChatMessage,
)


class TestMessageHeader:
    def test_pack_unpack_roundtrip(self):
        hdr = MessageHeader(msg_type=MessageType.HANDSHAKE_REQ, payload_length=42)
        packed = hdr.pack()
        restored = MessageHeader.unpack(packed)
        assert restored is not None
        assert restored.msg_type == MessageType.HANDSHAKE_REQ
        assert restored.payload_length == 42

    def test_invalid_magic(self):
        hdr = MessageHeader(msg_type=MessageType.PING, payload_length=0)
        data = bytearray(hdr.pack())
        data[0:4] = b"FAKE"
        assert MessageHeader.unpack(bytes(data)) is None

    def test_short_data(self):
        assert MessageHeader.unpack(b"") is None
        assert MessageHeader.unpack(b"WARP") is None


class TestHandshakeRequest:
    def test_pack_unpack_roundtrip(self):
        pubkey = os.urandom(256)
        salt = os.urandom(16)
        req = HandshakeRequest(
            filename="test.txt",
            filesize=1024,
            checksum="a" * 64,
            public_key=pubkey,
            salt=salt,
        )
        packed = req.pack()
        restored = HandshakeRequest.unpack(packed)
        assert restored is not None
        assert restored.filename == "test.txt"
        assert restored.filesize == 1024
        assert restored.checksum == "a" * 64
        assert restored.public_key == pubkey
        assert restored.salt == salt

    def test_unicode_filename(self):
        req = HandshakeRequest(
            filename="日本語.pdf",
            filesize=999,
            checksum="b" * 64,
            public_key=os.urandom(256),
            salt=os.urandom(16),
        )
        restored = HandshakeRequest.unpack(req.pack())
        assert restored.filename == "日本語.pdf"


class TestHandshakeAck:
    def test_pack_unpack_roundtrip(self):
        pubkey = os.urandom(256)
        ack = HandshakeAck(public_key=pubkey)
        restored = HandshakeAck.unpack(ack.pack())
        assert restored is not None
        assert restored.public_key == pubkey

    def test_short_payload(self):
        assert HandshakeAck.unpack(b"short") is None


class TestHandshakeNak:
    def test_pack_unpack_roundtrip(self):
        nak = HandshakeNak(reason="User rejected")
        restored = HandshakeNak.unpack(nak.pack())
        assert restored is not None
        assert restored.reason == "User rejected"


class TestDataChunk:
    def test_pack_unpack_roundtrip(self):
        data = os.urandom(8192)
        chunk = DataChunk(sequence=42, data=data)
        restored = DataChunk.unpack(chunk.pack())
        assert restored is not None
        assert restored.sequence == 42
        assert restored.data == data


class TestDataComplete:
    def test_pack_unpack_roundtrip(self):
        dc = DataComplete(total_chunks=100, final_checksum="c" * 64)
        restored = DataComplete.unpack(dc.pack())
        assert restored is not None
        assert restored.total_chunks == 100
        assert restored.final_checksum == "c" * 64


class TestChatMessage:
    def test_pack_unpack_roundtrip(self):
        msg = ChatMessage(sender="alice-laptop", text="Hello, world!")
        restored = ChatMessage.unpack(msg.pack())
        assert restored is not None
        assert restored.sender == "alice-laptop"
        assert restored.text == "Hello, world!"

    def test_unicode_text(self):
        msg = ChatMessage(sender="host", text="日本語テスト")
        restored = ChatMessage.unpack(msg.pack())
        assert restored.text == "日本語テスト"

    def test_empty_text(self):
        msg = ChatMessage(sender="host", text="")
        restored = ChatMessage.unpack(msg.pack())
        assert restored is not None
        assert restored.text == ""

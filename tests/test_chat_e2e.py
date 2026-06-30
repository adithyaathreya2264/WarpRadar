"""End-to-end tests for the encrypted chat message pipeline.

These tests stand up a real TransferServer on localhost and drive
the client-side `send_chat_message()` against it to verify the full
DH-handshake → AES-encrypt → send → receive → decrypt → callback
pipeline works correctly.
"""

import asyncio
import pytest

from warpradar.transport.server import TransferServer
from warpradar.transport.client import send_chat_message


@pytest.fixture
async def chat_server():
    """Start a TransferServer on an ephemeral port and yield it.

    The fixture patches the server port to 0 so the OS picks a free
    port, then reads back the actual port from the underlying
    asyncio.Server object.
    """
    received_messages: list[tuple[str, str]] = []

    async def on_message(sender: str, text: str) -> None:
        received_messages.append((sender, text))

    server = TransferServer(
        port=0,  # let OS assign a free port
        on_message_received=on_message,
    )
    await server.start()

    # Read the actual port the OS assigned
    actual_port = server._server.sockets[0].getsockname()[1]
    server._port = actual_port

    # Attach the received list so tests can inspect it
    server.received_messages = received_messages

    yield server

    await server.stop()


class TestChatEndToEnd:
    """Verify the full client → server encrypted chat flow."""

    @pytest.mark.asyncio
    async def test_message_arrives_at_server(self, chat_server):
        """A single chat message should be delivered to the server callback."""
        port = chat_server._port

        success = await send_chat_message(
            peer_ip="127.0.0.1",
            peer_port=port,
            sender_hostname="Alice",
            text="Hello from Alice!",
        )

        # Give the server a moment to run the callback
        await asyncio.sleep(0.3)

        assert success is True, "send_chat_message should return True"
        assert len(chat_server.received_messages) == 1
        sender, text = chat_server.received_messages[0]
        assert sender == "Alice"
        assert text == "Hello from Alice!"

    @pytest.mark.asyncio
    async def test_multiple_messages_all_arrive(self, chat_server):
        """Several sequential messages should each be delivered."""
        port = chat_server._port
        messages = [
            ("Alice", "Message 1"),
            ("Bob", "Message 2"),
            ("Charlie", "Message 3"),
        ]

        for hostname, text in messages:
            ok = await send_chat_message(
                peer_ip="127.0.0.1",
                peer_port=port,
                sender_hostname=hostname,
                text=text,
            )
            assert ok is True

        await asyncio.sleep(0.5)

        assert len(chat_server.received_messages) == 3
        for i, (expected_sender, expected_text) in enumerate(messages):
            sender, text = chat_server.received_messages[i]
            assert sender == expected_sender
            assert text == expected_text

    @pytest.mark.asyncio
    async def test_empty_text_still_delivers(self, chat_server):
        """An empty string body should still round-trip without crashing."""
        port = chat_server._port

        ok = await send_chat_message(
            peer_ip="127.0.0.1",
            peer_port=port,
            sender_hostname="Dave",
            text="",
        )
        await asyncio.sleep(0.3)

        assert ok is True
        assert len(chat_server.received_messages) == 1
        sender, text = chat_server.received_messages[0]
        assert sender == "Dave"
        assert text == ""

    @pytest.mark.asyncio
    async def test_unicode_message(self, chat_server):
        """Unicode characters (emoji, CJK, etc.) should survive the round-trip."""
        port = chat_server._port

        body = "こんにちは 🚀 WarpRadar"
        ok = await send_chat_message(
            peer_ip="127.0.0.1",
            peer_port=port,
            sender_hostname="Emi",
            text=body,
        )
        await asyncio.sleep(0.3)

        assert ok is True
        assert chat_server.received_messages[0] == ("Emi", body)

    @pytest.mark.asyncio
    async def test_no_callback_registered(self):
        """Server with no on_message_received should NOT crash when chat arrives."""
        server = TransferServer(
            port=0,
            on_message_received=None,   # no callback
        )
        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            ok = await send_chat_message(
                peer_ip="127.0.0.1",
                peer_port=port,
                sender_hostname="Ghost",
                text="this should not crash",
            )
            await asyncio.sleep(0.3)
            assert ok is True  # client still succeeds
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_wrong_port_returns_false(self):
        """Connecting to a port with nothing listening should return False."""
        ok = await send_chat_message(
            peer_ip="127.0.0.1",
            peer_port=19999,  # nothing here
            sender_hostname="Nobody",
            text="fail",
        )
        assert ok is False

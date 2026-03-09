"""Chat Widget - Retro-futuristic LAN messaging panel."""

from datetime import datetime
from dataclasses import dataclass, field
from typing import List

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static, Input
from textual.widget import Widget
from textual.containers import Vertical, ScrollableContainer
from textual.reactive import reactive
from textual import on


@dataclass
class ChatEntry:
    """A single chat message entry."""
    sender: str
    text: str
    timestamp: str
    is_self: bool


class ChatWidget(Widget):
    """
    Retro-futuristic LAN chat panel.
    Displays scrolling message history and an input field.
    """

    DEFAULT_CSS = """
    ChatWidget {
        layout: vertical;
        border: solid #005f00;
        border-title-color: #00ff41;
        border-title-style: bold;
        height: 100%;
    }

    #chat-log {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
        background: #0a0a0a;
    }

    .chat-empty {
        color: #005f00;
        text-align: center;
        margin-top: 2;
    }

    .chat-msg-self {
        color: #00d4ff;
        margin-bottom: 0;
    }

    .chat-msg-peer {
        color: #00ff41;
        margin-bottom: 0;
    }

    .chat-msg-time {
        color: #004400;
    }

    #chat-input {
        dock: bottom;
        height: 3;
        border-top: solid #005f00;
        background: #111;
        color: #00ff41;
        padding: 0 1;
    }

    #chat-input:focus {
        border-top: solid #00ff41;
    }
    """

    class MessageSend(Message):
        """Emitted when the user submits a message."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._entries: List[ChatEntry] = []

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="chat-log"):
            yield Static(
                "◈ No messages yet. Select a peer and press M to chat. ◈",
                id="chat-empty",
                classes="chat-empty",
            )
        yield Input(
            placeholder="Type a message and press Enter...",
            id="chat-input",
        )

    def add_message(self, sender: str, text: str, is_self: bool = False) -> None:
        """Add a message to the chat log."""
        ts = datetime.now().strftime("%H:%M")
        entry = ChatEntry(sender=sender, text=text, timestamp=ts, is_self=is_self)
        self._entries.append(entry)
        self._render_message(entry)

    def _render_message(self, entry: ChatEntry) -> None:
        """Append a rendered message to the scroll log."""
        log = self.query_one("#chat-log", ScrollableContainer)

        # Remove placeholder the first time
        try:
            placeholder = self.query_one("#chat-empty")
            placeholder.remove()
        except Exception:
            pass

        arrow = "▶" if entry.is_self else "◀"
        css_class = "chat-msg-self" if entry.is_self else "chat-msg-peer"
        label = f"[dim]{entry.timestamp}[/dim] {entry.sender} {arrow}  {entry.text}"

        msg_widget = Static(label, classes=css_class, markup=True)
        log.mount(msg_widget)
        log.scroll_end(animate=False)

    @on(Input.Submitted, "#chat-input")
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in the input box."""
        text = event.value.strip()
        if text:
            self.post_message(self.MessageSend(text))
            event.input.clear()

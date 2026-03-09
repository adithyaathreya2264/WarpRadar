"""WarpRadar Main Application - Orchestrates all components."""

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

from .config import config
from .discovery.beacon import Beacon
from .discovery.listener import Listener
from .discovery.registry import PeerRegistry, Peer
from .transport.server import TransferServer
from .transport.client import send_file, push_clipboard, send_chat_message
from .transport.streamer import TransferProgress
from .ui.radar import RadarWidget
from .ui.peer_list import PeerListWidget
from .ui.progress import ProgressWidget
from .ui.notifications import ToastWidget, TransferRequestModal
from .ui.file_picker import QuickFilePickerModal, FilePickerModal
from .ui.chat import ChatWidget
from .utils.system import get_system_info
from .utils.clipboard import get_clipboard, set_clipboard
from .utils.history import TransferHistory
from .utils.blackhole import BlackHole


class WarpRadarApp(App):
    """Main WarpRadar TUI application."""
    
    CSS_PATH = Path(__file__).parent / "ui" / "styles.tcss"
    
    TITLE = "WarpRadar - Decentralized File Sharing"
    
    BINDINGS = [
        Binding("f", "send_file", "Beam File", show=True),
        Binding("m", "send_message", "Send Message", show=True),
        Binding("c", "warp_clipboard", "Warp Clipboard", show=True),
        Binding("s", "toggle_stealth", "Stealth Mode", show=True),
        Binding("b", "toggle_blackhole", "Black Hole", show=True),
        Binding("up", "select_prev", "Previous", show=False),
        Binding("k", "select_prev", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("j", "select_next", "Next", show=False),
        Binding("q", "quit", "Exit", show=True),
    ]
    
    # Reactive attributes
    stealth_mode: reactive[bool] = reactive(False)
    peer_count: reactive[int] = reactive(0)
    current_transfer: reactive[Optional[TransferProgress]] = reactive(None)
    
    def __init__(self):
        super().__init__()
        
        # Networking components
        self._peer_registry: Optional[PeerRegistry] = None
        self._beacon: Optional[Beacon] = None
        self._listener: Optional[Listener] = None
        self._server: Optional[TransferServer] = None
        
        # UI components
        self._radar: Optional[RadarWidget] = None
        self._peer_list: Optional[PeerListWidget] = None
        self._progress: Optional[ProgressWidget] = None
        self._toast: Optional[ToastWidget] = None
        self._status: Optional[Static] = None
        self._chat: Optional[ChatWidget] = None
        
        # Selected peer
        self._selected_peer: Optional[Peer] = None
        
        # System info
        self._system_info = get_system_info()
        
        # Transfer history
        self._history = TransferHistory()
        
        # Black hole (auto-share)
        self._blackhole: Optional[BlackHole] = None
        self._blackhole_enabled = False
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with Vertical(id="radar-panel"):
                self._radar = RadarWidget(id="radar")
                yield self._radar
            
            with Vertical(id="peer-panel"):
                self._peer_list = PeerListWidget(id="peer-list")
                yield self._peer_list
            
            with Vertical(id="chat-panel"):
                self._chat = ChatWidget(id="chat")
                self._chat.border_title = "◈ COMMS CHANNEL"
                yield self._chat
        
        with Container(id="progress-panel"):
            self._progress = ProgressWidget(id="progress")
            yield self._progress
        
   
        
        # Yield toast last so it appears on top
        self._toast = ToastWidget(id="toast")
        yield self._toast
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize UI when app starts."""
        # Update title with hostname
        self.title = f"WarpRadar - {self._system_info.hostname}"
        
        # Show initial toast
        self._show_toast(
            f"WarpRadar starting - {self._system_info.os.icon} {self._system_info.hostname}",
            "info",
        )
        
        # Defer network startup to give Textual time to fully initialize
        self.set_timer(0.5, self._start_networking)
    
    async def _start_networking(self) -> None:
        """Start all networking components (called after delay)."""
        try:
            # Initialize peer registry
            self._peer_registry = PeerRegistry(
                timeout=config.network.peer_timeout,
                on_peer_added=self._on_peer_added,
                on_peer_removed=self._on_peer_removed,
                on_peer_updated=self._on_peer_updated,
            )
            await self._peer_registry.start()
            
            # Start beacon
            self._beacon = Beacon()
            await self._beacon.start()
            
            # Start listener
            self._listener = Listener(registry=self._peer_registry)
            await self._listener.start()
            
            # Start TCP server
            self._server = TransferServer(
                on_transfer_request=self._handle_transfer_request,
                on_transfer_progress=self._handle_transfer_progress,
                on_transfer_complete=self._handle_transfer_complete,
                on_clipboard_received=self._handle_clipboard_received,
                on_message_received=self._handle_message_received,
            )
            await self._server.start()
            
            # Initialize Black Hole
            self._blackhole = BlackHole(
                on_new_file=self._handle_blackhole_file
            )
            
            self._show_toast(
                f"WarpRadar online (Port {config.network.tcp_port}) - scanning for peers...",
                "success",
            )
        except Exception as e:
            self._show_toast(f"Network error: {e}", "error")
    
    async def on_unmount(self) -> None:
        """Clean up when app exits."""
        # Workers will be automatically cancelled by Textual
        # Just clean up resources
        if self._server:
            await self._server.stop()
        
        if self._listener:
            await self._listener.stop()
        
        if self._beacon:
            await self._beacon.stop()
        
        if self._peer_registry:
            await self._peer_registry.stop()
            
        if self._blackhole:
            self._blackhole.stop()
    
    def _on_peer_added(self, peer: Peer) -> None:
        """Handle new peer discovered."""
        self._update_peer_displays()
        self._show_toast(f"Peer discovered: {peer.hostname}", "info")
    
    def _on_peer_removed(self, peer: Peer) -> None:
        """Handle peer going offline."""
        self._update_peer_displays()
        self._show_toast(f"Peer offline: {peer.hostname}", "warning")
    
    def _on_peer_updated(self, peer: Peer) -> None:
        """Handle peer info update."""
        self._update_peer_displays()
    
    def on_peer_selected(self, message: PeerListWidget.PeerSelected) -> None:
        """Handle peer selection."""
        self._selected_peer = message.peer
        if message.peer:
            self._show_toast(f"Locked on: {message.peer.hostname}", "info")
    
    def _update_peer_displays(self) -> None:
        """Update UI with current peer list."""
        if not self._peer_registry:
            return
        
        # Get peers (run in sync context)
        async def get_peers():
            return await self._peer_registry.get_all_peers()
        
        # Schedule coroutine
        asyncio.create_task(self._async_update_peers())
    
    async def _async_update_peers(self) -> None:
        """Async helper to update peer displays."""
        if not self._peer_registry:
            return
        
        peers = await self._peer_registry.get_all_peers()
        
        if self._radar:
            self._radar.update_peers(peers)
        
        if self._peer_list:
            self._peer_list.update_peers(peers)
        
        self.peer_count = len(peers)
    
    async def _handle_transfer_request(
        self,
        filename: str,
        filesize: int,
        sender_ip: str,
    ) -> bool:
        """Handle incoming transfer request - show modal."""
        import asyncio
        
        # Find sender hostname
        sender_name = sender_ip
        if self._peer_registry:
            peers = await self._peer_registry.get_all_peers()
            for peer in peers:
                if peer.ip == sender_ip:
                    sender_name = peer.hostname
                    break
        
        # Create a Future to wait for user response
        loop = asyncio.get_event_loop()
        response_future: asyncio.Future[bool] = loop.create_future()
        
        def on_modal_dismiss(accepted: bool) -> None:
            """Called when modal is dismissed."""
            if not response_future.done():
                response_future.set_result(accepted if accepted is not None else False)
        
        # Push the modal directly (we're in the same event loop as the app)
        modal = TransferRequestModal(filename, filesize, sender_name)
        self.push_screen(modal, callback=on_modal_dismiss)
        
        # Wait for user response (with timeout)
        try:
            return await asyncio.wait_for(response_future, timeout=120.0)
        except asyncio.TimeoutError:
            # Dismiss modal if still open
            if modal in self.screen_stack:
                self.pop_screen()
            return False
    
    async def _handle_transfer_progress(self, progress: TransferProgress) -> None:
        """Handle transfer progress update."""
        if self._progress:
            self._progress.update_progress(progress)
    
    async def _handle_transfer_complete(self, file_path: Path) -> None:
        """Handle transfer completion."""
        self._show_toast(f"Received: {file_path.name}", "success")
        
        # Log to history (using last progress info)
        if self._progress and self._progress.progress:
            p = self._progress.progress
            # Find peer info from last transfer
            peer_hostname = "unknown"
            peer_ip = "unknown"
            # You could track this in a transfer state variable
            
            self._history.add_transfer(
                direction="received",
                filename=p.filename,
                filesize=p.total_bytes,
                peer_hostname=peer_hostname,
                peer_ip=peer_ip,
                success=True,
                duration_seconds=p.total_bytes / p.speed_bps if p.speed_bps > 0 else 0,
                speed_bps=p.speed_bps,
            )
        
        # Clear progress after a delay
        await asyncio.sleep(2)
        if self._progress:
            self._progress.clear()
    
    async def _handle_clipboard_received(self, text: str) -> None:
        """Handle clipboard data received."""
        set_clipboard(text)
        self._show_toast(f"Clipboard received ({len(text)} chars)", "success")
    
    def on_chat_widget_message_send(self, event: ChatWidget.MessageSend) -> None:
        """Route chat input to the background send worker."""
        self._send_message_worker(event.text)
    
    def _show_toast(self, message: str, msg_type: str = "info") -> None:
        """Show a toast notification."""
        if self._toast:
            self._toast.show_toast(message, msg_type)
    
    def action_select_next(self) -> None:
        """Select next peer."""
        if self._peer_list:
            self._peer_list.select_next()
            self._selected_peer = self._peer_list.get_selected_peer()
    
    def action_select_prev(self) -> None:
        """Select previous peer."""
        if self._peer_list:
            self._peer_list.select_prev()
            self._selected_peer = self._peer_list.get_selected_peer()
    
    @work
    async def action_send_file(self) -> None:
        """Send a file to selected peer."""
        self._show_toast("Beam File triggered...", "info")
        if not self._selected_peer:
            self._show_toast("No peer selected", "warning")
            return
        
        # Step 1: Show quick file picker
        quick_picker = QuickFilePickerModal()
        result = await self.push_screen_wait(quick_picker)
        
        if result is None:
            # User cancelled
            return
        
        file_path: Optional[Path] = None
        
        if isinstance(result, Path):
            if result.is_file():
                # User entered a file path directly
                file_path = result
            elif result.is_dir():
                # User selected a directory - show full picker
                full_picker = FilePickerModal(start_path=result)
                file_path = await self.push_screen_wait(full_picker)
        
        if not file_path or not file_path.is_file():
            self._show_toast("No file selected", "warning")
            return
        
        # Step 2: Send the file
        self._show_toast(
            f"Beaming {file_path.name} to {self._selected_peer.hostname}...",
            "info"
        )
        
        # Debug: show connection details
        self._show_toast(
            f"Connecting to {self._selected_peer.ip}:{self._selected_peer.port}...",
            "info"
        )
        
        try:
            success = await send_file(
                peer_ip=self._selected_peer.ip,
                peer_port=self._selected_peer.port,
                file_path=file_path,
                progress_callback=self._handle_transfer_progress,
            )
            
            if success:
                self._show_toast(f"Successfully beamed {file_path.name}", "success")
                
                # Log successful transfer
                filesize = file_path.stat().st_size
                # Calculate duration and speed from last progress
                if self._progress and self._progress.progress:
                    p = self._progress.progress
                    duration = p.total_bytes / p.speed_bps if p.speed_bps > 0 else 0
                    speed = p.speed_bps
                else:
                    duration = 0
                    speed = 0
                
                self._history.add_transfer(
                    direction="sent",
                    filename=file_path.name,
                    filesize=filesize,
                    peer_hostname=self._selected_peer.hostname,
                    peer_ip=self._selected_peer.ip,
                    success=True,
                    duration_seconds=duration,
                    speed_bps=speed,
                )
            else:
                self._show_toast(f"Failed to beam {file_path.name}", "error")
                
                # Log failed transfer
                self._history.add_transfer(
                    direction="sent",
                    filename=file_path.name,
                    filesize=file_path.stat().st_size,
                    peer_hostname=self._selected_peer.hostname,
                    peer_ip=self._selected_peer.ip,
                    success=False,
                    duration_seconds=0,
                    speed_bps=0,
                    error_message="Transfer failed",
                )
        except Exception as e:
            self._show_toast(f"Transfer error: {str(e)}", "error")
            
            # Log error
            self._history.add_transfer(
                direction="sent",
                filename=file_path.name,
                filesize=file_path.stat().st_size if file_path.exists() else 0,
                peer_hostname=self._selected_peer.hostname,
                peer_ip=self._selected_peer.ip,
                success=False,
                duration_seconds=0,
                speed_bps=0,
                error_message=str(e),
            )
    
    @work
    async def action_warp_clipboard(self) -> None:
        """Warp clipboard to selected peer."""
        self._show_toast("Warp Clipboard triggered...", "info")
        if not self._selected_peer:
            self._show_toast("No peer selected", "warning")
            return
        
        # Get clipboard content
        text = get_clipboard()
        if not text:
            self._show_toast("Clipboard is empty", "warning")
            return
        
        # Send to peer
        self._show_toast(
            f"Warping clipboard to {self._selected_peer.hostname}...",
            "info"
        )
        
        success = await push_clipboard(
            peer_ip=self._selected_peer.ip,
            peer_port=self._selected_peer.port,
            text=text,
        )
        
        if success:
            self._show_toast("Clipboard warped successfully", "success")
        else:
            self._show_toast("Failed to warp clipboard", "error")
    
    def action_send_message(self) -> None:
        """Focus the chat input box so the user can type a message."""
        if not self._selected_peer:
            self._show_toast("No peer selected", "warning")
            return
        if self._chat:
            try:
                input_box = self._chat.query_one("#chat-input")
                input_box.focus()
            except Exception:
                pass

    @work
    async def _send_message_worker(self, text: str) -> None:
        """Send a chat message in a background worker."""
        if not self._selected_peer:
            return
        peer = self._selected_peer
        hostname = self._system_info.hostname

        # Show immediately in own chat as sent
        if self._chat:
            self._chat.add_message(hostname, text, is_self=True)

        success = await send_chat_message(
            peer_ip=peer.ip,
            peer_port=peer.port,
            sender_hostname=hostname,
            text=text,
        )
        if not success:
            self._show_toast("Message failed to send", "error")

    async def _handle_message_received(self, sender: str, text: str) -> None:
        """Handle an incoming chat message from another peer."""
        # Display in chat log
        if self._chat:
            self._chat.add_message(sender, text, is_self=False)
        self._show_toast(f"◀ {sender}: {text[:40]}", "info")

        # Auto-select the sender as the active peer so the user can reply
        # immediately without having to navigate the peer list
        if not self._selected_peer and self._peer_registry:
            peers = await self._peer_registry.get_all_peers()
            for peer in peers:
                if peer.hostname == sender:
                    self._selected_peer = peer
                    if self._peer_list:
                        self._peer_list.select_peer(peer)
                    self._show_toast(f"Auto-selected {sender} for reply", "info")
                    break



    async def _handle_blackhole_file(self, file_path: Path) -> None:
        """Handle new file in Black Hole directory."""
        if not self._blackhole_enabled or not self._selected_peer:
            return
            
        self._show_toast(f"Black Hole: Beaming {file_path.name}...", "info")
        
        try:
            success = await send_file(
                peer_ip=self._selected_peer.ip,
                peer_port=self._selected_peer.port,
                file_path=file_path,
                progress_callback=self._handle_transfer_progress,
            )
            
            if success:
                self._show_toast(f"Black Hole: Sent {file_path.name}", "success")
                # Log usage
                self._history.add_transfer(
                    direction="sent",
                    filename=file_path.name,
                    filesize=file_path.stat().st_size,
                    peer_hostname=self._selected_peer.hostname,
                    peer_ip=self._selected_peer.ip,
                    success=True,
                    duration_seconds=0,
                    speed_bps=0,
                )
        except Exception:
            pass
    
    def action_toggle_blackhole(self) -> None:
        """Toggle Black Hole mode."""
        self._show_toast("Black Hole toggle triggered...", "info")
        if not self._blackhole:
            return
            
        self._blackhole_enabled = not self._blackhole_enabled
        
        if self._blackhole_enabled:
            self._blackhole.start()
            self._show_toast("Black Hole ACTIVE - Drop files in ~/WarpBlackHole", "warning")
        else:
            self._blackhole.stop()
            self._show_toast("Black Hole DISABLED", "info")
            
    def action_toggle_stealth(self) -> None:
        """Toggle stealth mode."""
        self._show_toast("Stealth toggle triggered...", "info")
        self.stealth_mode = not self.stealth_mode
        
        if self._beacon:
            if self.stealth_mode:
                self._beacon.disable()
                self._show_toast("Stealth mode enabled - you are invisible", "info")
            else:
                self._beacon.enable()
                self._show_toast("Stealth mode disabled - you are visible", "info")
    
    def watch_stealth_mode(self, value: bool) -> None:
        """React to stealth mode changes."""
        # Update status display
        pass
    
    def watch_peer_count(self, value: int) -> None:
        """React to peer count changes."""
        # Could update a status widget
        pass

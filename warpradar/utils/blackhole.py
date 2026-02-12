"""Black Hole - Auto-sharing directory watcher."""

import asyncio
import os
from pathlib import Path
from typing import Callable, Optional, Set, Awaitable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..config import config


class BlackHoleHandler(FileSystemEventHandler):
    """Handles file system events for the Black Hole directory."""
    
    def __init__(
        self,
        callback: Callable[[Path], Awaitable[None]],
        loop: asyncio.AbstractEventLoop,
    ):
        self._callback = callback
        self._loop = loop
    
    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            # Schedule callback in the event loop
            path = Path(event.src_path)
            asyncio.run_coroutine_threadsafe(
                self._callback(path),
                self._loop,
            )


class BlackHole:
    """Watches a directory and auto-shares new files."""
    
    def __init__(
        self,
        path: Path = None,
        on_new_file: Optional[Callable[[Path], Awaitable[None]]] = None,
    ):
        self._path = path or (Path.home() / "WarpBlackHole")
        self._on_new_file = on_new_file
        self._observer: Optional[Observer] = None
        self._handler: Optional[BlackHoleHandler] = None
        self._running = False
        
        # Create directory if needed
        self._path.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start watching the directory."""
        if self._running:
            return
        
        self._running = True
        
        # watchdog requires scheduling in a thread, but we need to call back into asyncio
        loop = asyncio.get_event_loop()
        self._handler = BlackHoleHandler(self._handle_file, loop)
        
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._path), recursive=False)
        self._observer.start()
    
    def stop(self) -> None:
        """Stop watching."""
        if not self._running:
            return
        
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
    
    async def _handle_file(self, path: Path) -> None:
        """Handle a new file detected in the black hole."""
        # Wait a moment for file write to complete
        await asyncio.sleep(1.0)
        
        if self._on_new_file:
            await self._on_new_file(path)

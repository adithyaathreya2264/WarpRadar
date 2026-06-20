"""Test file transfer between two simulated instances."""

import asyncio
import tempfile
from pathlib import Path

# Import WarpRadar modules
from warpradar.transport.client import send_file
from warpradar.transport.server import TransferServer
from warpradar.transport.streamer import TransferProgress
from warpradar.config import config


async def test_transfer():
    """Test file transfer."""
    print("=" * 60)
    print("FILE TRANSFER TEST")
    print("=" * 60)
    
    # Create a test file
    test_file = Path(tempfile.gettempdir()) / "warpradar_test_file.txt"
    test_file.write_text("Hello from WarpRadar! This is a test file.")
    print(f"\n[1] Created test file: {test_file}")
    print(f"    Size: {test_file.stat().st_size} bytes")
    
    received_file = None
    
    async def on_transfer_request(filename: str, filesize: int, sender_ip: str) -> bool:
        print(f"\n[SERVER] Transfer request: {filename} ({filesize} bytes) from {sender_ip}")
        return True  # Always accept
    
    async def on_transfer_progress(progress: TransferProgress) -> None:
        print(f"[PROGRESS] {progress.percent:.1f}% - {progress.transferred_bytes}/{progress.total_bytes}")
    
    async def on_transfer_complete(file_path: Path) -> None:
        nonlocal received_file
        received_file = file_path
        print(f"\n[SERVER] Transfer complete! Saved to: {file_path}")
    
    async def on_clipboard_received(text: str) -> None:
        print(f"[SERVER] Clipboard received: {text[:50]}...")
    
    # Start server
    print(f"\n[2] Starting server on port {config.network.tcp_port}...")
    server = TransferServer(
        on_transfer_request=on_transfer_request,
        on_transfer_progress=on_transfer_progress,
        on_transfer_complete=on_transfer_complete,
        on_clipboard_received=on_clipboard_received,
    )
    await server.start()
    print(f"    Server started on port {config.network.tcp_port}")
    
    # Wait for server to be ready
    await asyncio.sleep(0.5)
    
    # Send file
    print(f"\n[3] Sending file to 127.0.0.1:{config.network.tcp_port}...")
    
    success = await send_file(
        peer_ip="127.0.0.1",
        peer_port=config.network.tcp_port,
        file_path=test_file,
        progress_callback=on_transfer_progress,
    )
    
    print(f"\n[4] Transfer result: {'SUCCESS' if success else 'FAILED'}")
    
    if received_file and received_file.exists():
        content = received_file.read_text()
        print(f"    Received content: {content}")
    
    # Cleanup
    await server.stop()
    test_file.unlink()
    
    print("\n" + "=" * 60)
    print(f"TEST RESULT: {'PASSED' if success else 'FAILED'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_transfer())

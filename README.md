# WarpRadar

**Decentralized Terminal File Sharing & LAN Messaging**

WarpRadar is a retro-futuristic TUI for secure local network communication — share files, beam clipboards, and chat in real-time, all encrypted, zero configuration required.

---

## Features

### Passive Peer Discovery
- Zero-config discovery via UDP Multicast — no IPs to configure
- Peers appear as animated blips on a live radar display
- Real-time RTT-based signal strength visualization

### LAN Chat
- Real-time encrypted messaging between any two WarpRadar peers
- Scrollable chat history with color-coded sent/received messages
- Auto-selects the sender so you can reply instantly

### Encrypted File Transfer
- Beam any file to a selected peer with a single keypress
- Streaming transfer (low memory usage for large files)
- SHA-256 integrity verification + AES-256-GCM encryption

### Clipboard Warp
- Copy on one machine, paste on another in under a second
- Fully encrypted in transit

### Security
- Diffie-Hellman (2048-bit) ephemeral key exchange per session
- AES-256-GCM authenticated encryption
- SHA-256 file integrity verification

### Cyberpunk TUI
- Animated radar with sweeping scan line
- Neon green cyberpunk theme
- Real-time progress bars with speed & ETA
- Toast notifications and modal dialogs

---

## Quick Start

### Installation

```bash
# Clone and enter directory
git clone https://github.com/adithyaathreya2264/WarpRadar
cd WarpRadar

# Create and activate virtual environment (Windows)
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running WarpRadar

```bash
# Terminal 1 (default port 5556)
python -m warpradar

# Terminal 2 (different port for same-machine testing)
$env:WARPRADAR_TCP_PORT=5557
python -m warpradar
```

### First-Time Usage

1. **Launch** — Start WarpRadar on one or more devices on the same LAN
2. **Discover** — Peers appear automatically as blips on the radar
3. **Select** — Use `↑`/`↓` arrow keys to highlight a peer
4. **Act** — Press `F` to beam a file, `M` to chat, `C` to warp clipboard

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `F` | Beam File to selected peer |
| `M` | Open chat input to send a message |
| `C` | Warp Clipboard to selected peer |
| `S` | Toggle Stealth Mode (invisible to others) |
| `B` | Toggle Black Hole (auto-share watch folder) |
| `↑` / `K` | Select previous peer |
| `↓` / `J` | Select next peer |
| `Q` | Quit |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              Layer 1: Discovery                  │
│  UDP Multicast (224.0.0.1:5555)                 │
│  • Beacon: Broadcasts heartbeat every 2s        │
│  • Listener: Discovers peers passively          │
│  • Registry: Manages active peers (TTL=10s)     │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│              Layer 2: Transport                  │
│  TCP Sockets (default port 5556)                │
│  • Handshake: DH key exchange                   │
│  • Streamer: 4KB chunks with encryption         │
│  • Chat: MESSAGE_PUSH / MESSAGE_ACK protocol    │
│  • Server: Accepts transfers, messages & clips  │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│              Layer 3: Security                   │
│  • Diffie-Hellman: 2048-bit ephemeral keys      │
│  • AES-256-GCM: Per-session encryption          │
│  • SHA-256: File integrity verification         │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│              Layer 4: Interface                  │
│  Textual TUI Framework                          │
│  • Radar: Animated sweep with peer blips        │
│  • Peer List: OS icons & signal strength        │
│  • Chat Panel: Scrollable real-time messages    │
│  • Progress: Live transfer stats                │
│  • Notifications: Modal dialogs & toasts        │
└──────────────────────────────────────────────────┘
```

---

## Project Structure

```
WarpRadar/
├── warpradar/
│   ├── discovery/          # UDP Multicast layer
│   │   ├── beacon.py       # Heartbeat broadcaster
│   │   ├── listener.py     # Peer discovery
│   │   └── registry.py     # Peer management
│   ├── transport/          # TCP transfer layer
│   │   ├── protocol.py     # Binary message protocol
│   │   ├── handshake.py    # DH key exchange + session setup
│   │   ├── streamer.py     # Encrypted file streaming
│   │   ├── server.py       # Incoming connection handler
│   │   └── client.py       # File, clipboard & chat sender
│   ├── security/           # Encryption layer
│   │   ├── crypto.py       # DH + AES-256-GCM
│   │   └── integrity.py    # SHA-256 checksums
│   ├── ui/                 # TUI components
│   │   ├── radar.py        # Animated radar widget
│   │   ├── peer_list.py    # Peer list panel
│   │   ├── chat.py         # Real-time chat panel
│   │   ├── progress.py     # Transfer progress bar
│   │   ├── notifications.py # Modals & toasts
│   │   └── styles.tcss     # Textual CSS theme
│   ├── utils/              # Utilities
│   │   ├── system.py       # OS detection
│   │   ├── clipboard.py    # Cross-platform clipboard
│   │   ├── history.py      # Transfer history
│   │   └── blackhole.py    # Auto-share watch folder
│   ├── app.py              # Main application orchestrator
│   ├── config.py           # Configuration
│   └── __main__.py         # Entry point with CLI args
├── requirements.txt
└── README.md
```

---

## Configuration

Override defaults via environment variables before launching:

| Variable | Default | Description |
|----------|---------|-------------|
| `WARPRADAR_TCP_PORT` | `5556` | TCP port for incoming transfers |
| `WARPRADAR_MULTICAST_PORT` | `5555` | UDP multicast port for discovery |

Or edit `warpradar/config.py` directly:

```python
multicast_group = "224.0.0.1"
multicast_port  = 5555
tcp_port        = 5556       # overridden by env var
chunk_size      = 4096       # bytes per transfer chunk
primary_color   = "#00ff41"  # neon green
```

---

## Troubleshooting

### Peers Not Appearing
- Ensure UDP port 5555 is not blocked by your firewall
- Verify both devices are on the same subnet
- Some routers block multicast — check router settings

### Transfer or Message Fails
- Ensure both instances are running the **same version**
- Check available disk space in `~/WarpDownloads`
- Verify TCP port (5556/5557) is not blocked

---

## License

MIT License
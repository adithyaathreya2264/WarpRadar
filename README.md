# WarpRadar 

**Decentralized Terminal File Sharing with Zero-Config Discovery**

A retro-futuristic TUI application that transforms local network file sharing into an immersive cyberpunk experience. Drop the manual IP configuration and watch your peers appear as glowing blips on an animated radar display.

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

## Features

### **Passive Discovery**
- Zero-config peer discovery via UDP Multicast
- Peers appear automatically on startup - no IP addresses to remember
- Real-time RTT-based distance visualization on radar

### **Military-Grade Security**
- End-to-end encryption with Diffie-Hellman key exchange
- AES-256-GCM authenticated encryption per session
- SHA-256 integrity verification for every transfer

### **Cyberpunk TUI**
- Animated radar with sweeping scan line (Sin/Cos rendering)
- Neon green color scheme with smooth animations
- Real-time transfer progress with speed & ETA
- Toast notifications for network events

### **Zero-Friction Workflow**
- **Warp Clipboard**: Copy on one device, paste on another (Press `C`)
- **Beam Files**: Select peer and send files instantly (Press `F`)
- **Stealth Mode**: Go invisible while still discovering others (Press `S`)

### **Advanced Features**
- Streaming transfers (low memory usage for large files)
- Automatic peer expiration (TTL-based)
- Cross-platform: Windows, Linux, macOS

## Quick Start

### Installation

```bash
# Clone the repository
cd e:\Personal_Projects\WrapRader

# Activate virtual environment (Windows)
.\.venv\Scripts\activate

# Verify dependencies are installed
pip list | findstr textual
```

### Running WarpRadar

```bash
# Start the application
#In Terminal 1: Activate Environment first and then:
python -m warpradar

#In Terminal 2: Activate environment first and then:
$env:WARPRADAR_TCP_PORT=5557
python -m warpradar
```

### First-Time Usage

1. **Launch** - Open WarpRadar on multiple devices on the same network
2. **Discover** - Peers appear automatically as blips on your radar
3. **Select** - Use arrow keys (↑/↓) to select a peer
4. **Warp** - Press `C` to send clipboard or `F` to beam a file

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Layer 1: Discovery                 │
│  UDP Multicast (224.0.0.1:5555)                │
│  • Beacon: Broadcasts heartbeat every 2s       │
│  • Listener: Discovers peers passively         │
│  • Registry: Manages active peers (TTL=10s)    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              Layer 2: Transport                 │
│  TCP Sockets (Port 5556)                       │
│  • Handshake: DH key exchange                  │
│  • Streamer: 4KB chunks with encryption        │
│  • Server: Accepts incoming transfers          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              Layer 3: Security                  │
│  E2E Encryption                                │
│  • Diffie-Hellman: 2048-bit ephemeral keys     │
│  • AES-256-GCM: Session-based encryption       │
│  • SHA-256: File integrity verification        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              Layer 4: Interface                 │
│  Textual TUI Framework                         │
│  • Radar: Animated scan with peer blips       │
│  • Peer List: OS icons & signal strength       │
│  • Progress: Real-time transfer stats          │
│  • Notifications: Modal dialogs & toasts       │
└─────────────────────────────────────────────────┘
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `F` | Beam File to selected peer |
| `C` | Warp Clipboard to selected peer |
| `S` | Toggle Stealth Mode |
| `↑/K` | Select previous peer |
| `↓/J` | Select next peer |
| `Q` | Quit application |

## Configuration

Settings are managed in `warpradar/config.py`:

```python
# Network settings
multicast_group = "224.0.0.1"
multicast_port = 5555
tcp_port = 5556
chunk_size = 4096  # 4KB chunks

# UI settings
primary_color = "#00ff41"  # Neon green
radar_sweep_speed = 3.0    # seconds per revolution
fps = 30                   # Animation frame rate
```

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
│   │   ├── handshake.py    # Connection establishment
│   │   ├── streamer.py     # File streaming
│   │   ├── server.py       # TCP listener
│   │   └── client.py       # Transfer initiator
│   ├── security/           # Encryption layer
│   │   ├── crypto.py       # DH + AES-GCM
│   │   └── integrity.py    # SHA-256 checksums
│   ├── ui/                 # TUI components
│   │   ├── radar.py        # Animated radar widget
│   │   ├── peer_list.py    # Peer list panel
│   │   ├── progress.py     # Progress bar
│   │   ├── notifications.py # Modals & toasts
│   │   └── styles.tcss     # Textual CSS
│   ├── utils/              # Utilities
│   │   ├── system.py       # OS detection
│   │   └── clipboard.py    # Cross-platform clipboard
│   ├── app.py              # Main application
│   ├── config.py           # Configuration
│   └── __main__.py         # Entry point
├── requirements.txt
└── README.md
```

## Testing

### Local Testing (Single Machine)

```bash
# Terminal 1
python -m warpradar

# Terminal 2 (different port)
python -m warpradar --port 5557
```

> **Note**: On the same machine, you'll need to modify the code to allow different ports for testing.

### Network Testing

1. Install WarpRadar on 2+ devices on the same LAN
2. Launch simultaneously
3. Observe peer discovery on the radar
4. Test file transfers and clipboard warp

## Troubleshooting

### Peers Not Appearing

- **Firewall**: Ensure UDP port 5555 and TCP port 5556 are open
- **Network**: Verify devices are on the same subnet
- **Multicast**: Some routers block multicast traffic - check router settings

### Transfer Fails

- **Encryption**: Ensure both peers have identical WarpRadar versions
- **Disk Space**: Check available space in `~/WarpDownloads`
- **Permissions**: Verify write permissions to download directory

## Roadmap

- **File Selection Dialog** - Native file picker integration
- **Transfer History** - Persistent log of all transfers
- **Black Hole Directory** - Auto-share designated folder
- **Parallel Transfers** - Multi-connection for large files
- **Remote Commands** - Optional SSH-like shell access (trusted networks only)

## License

MIT License - See LICENSE file for details
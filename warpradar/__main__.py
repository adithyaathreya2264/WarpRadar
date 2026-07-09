"""WarpRadar entry point."""

import sys
import os
import argparse
import traceback


def main():
    """Launch WarpRadar application."""
    parser = argparse.ArgumentParser(
        description="WarpRadar - Decentralized P2P File Sharing"
    )
    parser.add_argument(
        "--tcp-port", "-t",
        type=int,
        default=None,
        help="TCP port for file transfers (default: 5556)"
    )
    parser.add_argument(
        "--udp-port", "-u",
        type=int,
        default=None,
        help="UDP port for peer discovery (default: 5555)"
    )
    
    args = parser.parse_args()
    
    # Set environment variables BEFORE importing any warpradar modules.
    # The config module reads env vars at import time via os.getenv() defaults.
    if args.tcp_port:
        os.environ["WARPRADAR_TCP_PORT"] = str(args.tcp_port)
    if args.udp_port:
        os.environ["WARPRADAR_MULTICAST_PORT"] = str(args.udp_port)
    
    # Now import after env vars are set
    from warpradar.app import WarpRadarApp
    
    try:
        app = WarpRadarApp()
        app.run()
    except Exception as e:
        print("\n" + "="*60)
        print("WARPRADAR STARTUP ERROR")
        print("="*60)
        print(f"\nError: {e}\n")
        print("Full traceback:")
        traceback.print_exc()
        print("\n" + "="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()

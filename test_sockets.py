"""Test socket binding permissions on Windows."""

import socket
import struct

print("Testing WarpRadar socket requirements...\n")

# Test 1: UDP Multicast binding
print("1. Testing UDP Multicast (port 5555)...")
try:
    sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_udp.bind(("", 5555))
    
    # Try joining multicast group
    mreq = struct.pack("4sl", socket.inet_aton("224.0.0.1"), socket.INADDR_ANY)
    sock_udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    print("   ✓ UDP Multicast: SUCCESS")
    sock_udp.close()
except Exception as e:
    print(f"   ✗ UDP Multicast: FAILED - {e}")

# Test 2: TCP Server binding
print("\n2. Testing TCP Server (port 5556)...")
try:
    sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_tcp.bind(("0.0.0.0", 5556))
    sock_tcp.listen(5)
    print("   ✓ TCP Server: SUCCESS")
    sock_tcp.close()
except Exception as e:
    print(f"   ✗ TCP Server: FAILED - {e}")

# Test 3: Check if ports are in use
print("\n3. Checking for port conflicts...")
import subprocess
try:
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    lines = result.stdout.split('\n')
    port_5555 = [l for l in lines if ':5555' in l]
    port_5556 = [l for l in lines if ':5556' in l]
    
    if port_5555:
        print(f"   ⚠ Port 5555 in use:")
        for line in port_5555[:3]:
            print(f"     {line.strip()}")
    else:
        print("   ✓ Port 5555: Available")
    
    if port_5556:
        print(f"   ⚠ Port 5556 in use:")
        for line in port_5556[:3]:
            print(f"     {line.strip()}")
    else:
        print("   ✓ Port 5556: Available")
        
except Exception as e:
    print(f"   ⚠ Could not check ports: {e}")

print("\n" + "="*50)
print("SUMMARY:")
print("="*50)
print("If all tests passed, the socket issue is elsewhere.")
print("If tests failed, WarpRadar cannot bind to required ports.")
print("\nTo fix port conflicts:")
print("1. Find process ID (PID) from netstat output")
print("2. Kill process: taskkill /PID <pid> /F")
print("3. Or use different ports in config.py")

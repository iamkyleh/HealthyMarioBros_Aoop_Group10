#!/usr/bin/env python3
"""Simple test to verify server connection and message exchange"""
import socket
import time
from game.net import send_json, recv_json

HOST = "127.0.0.1"  # Use localhost for local testing
PORT = 5000

print("=" * 50)
print("Connection Test")
print("=" * 50)
print(f"Connecting to {HOST}:{PORT}...")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.settimeout(10.0)
    
    s.connect((HOST, PORT))
    print("✓ Connected!")
    
    print("Sending role: P")
    send_json(s, {"role": "P"})
    print("✓ Role sent!")
    
    print("Waiting for welcome message (10 seconds)...")
    s.settimeout(10.0)
    msg = recv_json(s, timeout=10.0)
    
    if msg:
        print("✓ Welcome message received!")
        print(f"  Message keys: {list(msg.keys())}")
        if "welcome" in msg:
            print(f"  Welcome: {msg['welcome']}")
        if "player_name" in msg:
            print(f"  Player name: {msg['player_name']}")
        if "platform" in msg:
            print(f"  Platform data: {len(msg['platform'].get('brick', []))} bricks")
    else:
        print("✗ No welcome message received!")
        print("  This means the server is not sending the welcome message.")
        print("  Check the server window for errors.")
    
    s.close()
    print("=" * 50)
    
except ConnectionRefusedError:
    print("✗ Connection refused!")
    print("  Make sure the server is running.")
    print("  Check that server.py shows: 'Server listening on 0.0.0.0:5000'")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()


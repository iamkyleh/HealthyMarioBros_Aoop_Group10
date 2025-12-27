#!/usr/bin/env python3
"""
Quick start script for playing against AI Mario
"""

import os
import sys
import subprocess
import time

def main():
    print("🤖 AI Mario PvP Fighter - Quick Start")
    print("=" * 40)

    # Check if AI model exists
    model_path = "mario_pvp_ai.zip"
    if not os.path.exists(model_path):
        print("❌ No trained AI model found!")
        print("Training AI first...")
        subprocess.run([sys.executable, "train_ai.py", "train"])
        print("✅ AI training completed!")

    print("\n🚀 Starting game servers...")
    print("1. Server will start first")
    print("2. Then start the client")
    print("3. Select 'pvp_arena' from the world menu to fight AI")
    print("4. AI will join automatically as your opponent!")
    print("\nControls:")
    print("- WASD/Arrow keys: Move")
    print("- Space/W: Jump")
    print("- X/Left Click: Attack")
    print("- UP/DOWN arrows: Navigate world menu")
    print("- ENTER: Confirm world selection")

    # Start server
    print("\nStarting server...")
    server_process = subprocess.Popen([sys.executable, "server.py"])

    # Wait a moment for server to start
    time.sleep(2)

    # Start client
    print("Starting client...")
    client_process = subprocess.Popen([sys.executable, "client.py"])

    try:
        # Wait for processes
        server_process.wait()
        client_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_process.terminate()
        client_process.terminate()

if __name__ == "__main__":
    main()
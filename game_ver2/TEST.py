import threading
import time
import socket
from server import Server, HOST, PORT
from client import GameClient, _camera_available, JumpDetector, PoseCamera
from game.net import send_json, recv_json

def run_server_auto_start():
    """Run server with automatic world selection"""
    # Create server instance
    server = Server.__new__(Server)
    
    # Initialize server manually
    import threading as th
    import os
    import glob
    import addpath
    
    # Socket tracking
    server.player_sockets = []
    server.observer_sockets = []
    server.player_inputs = {}
    server.player_names = {}
    server.player_to_socket = {}
    server.observer_names = {}
    
    # World selection state
    world_dir = addpath.world_path("")
    world_files = glob.glob(os.path.join(world_dir, "world*.json"))
    worlds = []
    for wf in sorted(world_files):
        basename = os.path.basename(wf)
        if basename.startswith("world") and basename.endswith(".json"):
            world_name = basename[:-5]
            worlds.append(world_name)
    server.available_worlds = worlds if worlds else ["world1"]
    server.selected_world_index = 0
    server.world_selection_confirmed = False
    
    # Initialize game
    from server import Game
    server.game = Game(server.available_worlds[0] if server.available_worlds else "world1")
    server.available_names = ["MushroomRetainer", "Mario", "Luigi"]
    server.running = True
    server.game_started = False
    
    # Initialize network
    server._Server__init_network()
    
    # Start accepting players in background
    server.player_accept_thread = th.Thread(target=server._Server__accept_players, daemon=True)
    server.player_accept_thread.start()
    
    # Wait for world selection (will be handled by client)
    print("Waiting for world selection...")
    while not server.game_started and server.running:
        time.sleep(0.1)
    
    if server.game_started:
        server._Server__start_game_loop()
    
    return server

def run_client():
    """Run client that automatically connects as a player"""
    # Store original method
    original_init = GameClient._init_networking
    
    # Override _init_networking to skip user input
    def auto_init_networking(self):
        """Modified init_networking that auto-connects as player"""
        self.role = "P"  # Automatically set as player
        
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.s.settimeout(10.0)
            
            # Use localhost for client connection (0.0.0.0 is only for server binding)
            CLIENT_HOST = '127.0.0.1'
            print(f"Connecting to server on {CLIENT_HOST}:{PORT}...")
            self.s.connect((CLIENT_HOST, PORT))
            print("Connected! Sending role...")
            
            # Send role to server immediately after connecting
            send_json(self.s, {"role": self.role})
            print(f"Role '{self.role}' sent to server. Waiting for welcome message...")

            # Welcome packet with platform data
            msg = None
            for attempt in range(3):
                msg = recv_json(self.s, timeout=5.0)
                if msg:
                    break
                print(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(0.1)
            
            if msg and "welcome" in msg:
                if "platform" in msg:
                    self.platforms = msg["platform"]
                if "flag" in msg:
                    self.flags = msg["flag"]
                if "flag_final" in msg:
                    self.flag_final = msg["flag_final"]
                if "player_name" in msg:
                    self.name = msg["player_name"]
                if "role" in msg:
                    self.role = msg["role"]
                if "world_selection" in msg:
                    ws = msg["world_selection"]
                    self.available_worlds = ws.get("available_worlds", [])
                    self.selected_world_index = ws.get("selected_index", 0)
                    self.world_selection_confirmed = ws.get("confirmed", False)
                    if self.world_selection_confirmed:
                        self.world_selection_mode = False
                role_name = "player" if self.role == "P" else "observer"
                print(f"Connected as {role_name}" + (f" ({self.name})" if self.name else ""))
            else:
                print(f"Failed to receive welcome message. Received: {msg}")
                self.running = False
                return
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False
            return
        
        # Initialize camera if role is player
        if self.role == "P":
            self.pose_jump_detected = False
            if _camera_available:
                self.jump_detector = JumpDetector()
                self.pose_camera = PoseCamera()
                
                # Start camera thread for jump detection
                self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
                self.camera_thread.start()
            else:
                # Ensure attributes exist even without camera support
                self.jump_detector = JumpDetector()
                self.pose_camera = PoseCamera()
            
            # Auto-confirm world selection after a short delay
            def auto_confirm_world():
                time.sleep(1.0)  # Wait 1 second
                if self.world_selection_mode and self.role == "P":
                    try:
                        send_json(self.s, {"world_selection": {"confirm": True}})
                        print("Auto-confirmed world selection")
                    except Exception as e:
                        print(f"Error auto-confirming world: {e}")
            
            auto_confirm_thread = threading.Thread(target=auto_confirm_world, daemon=True)
            auto_confirm_thread.start()
        
        # Now switch to non-blocking mode for game loop
        self.s.settimeout(0.01)
    
    # Replace the method temporarily
    GameClient._init_networking = auto_init_networking
    
    try:
        # Create and run client
        client = GameClient()
        client.run()
    finally:
        # Restore original method
        GameClient._init_networking = original_init

def main():
    """Main function to run both server and client"""
    print("="*60)
    print("TEST MODE: Auto-starting server and client")
    print("="*60)
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=run_server_auto_start, daemon=True)
    server_thread.start()
    
    # Give server time to initialize
    time.sleep(1)
    
    # Run client in main thread (blocking)
    try:
        run_client()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

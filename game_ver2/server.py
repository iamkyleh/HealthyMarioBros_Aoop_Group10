import socket
import json
import threading
import time
import pygame

# Add parent directory to path to import game_ver1 modules if needed
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from net import send_json, recv_json
from player import *
from enemy import *
from props import *
import addpath

HOST = '0.0.0.0'
PORT = 5000

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

START_TIME = time.time()*1000
def now():
    return time.time()*1000

enemy_classes = {
    "Goomba": Goomba,
    "KoopaTroopa": KoopaTroopa,
}

class Game:
    def __init__(self):
        self.respawn_point = (80, 400)
        self.filename = "world1"
        self.platforms, self.flags, self.flag_final, self.coins, self.enemies = [], [], None, [], []
        self._load_level(self.filename)
        self.players = []
        self.score = 0
        self.won = False
        self.camera_x = 0
        
    def _load_level(self, filename):
        with open(addpath.world_path(f"{filename}.json")) as f:
            data = json.load(f)
            
            # Load platforms
            for p in data["Platforms"]:
                self.platforms.append(pygame.Rect(p["x"], p["y"], p["w"], p["h"]))
            
            # Load flags
            if "Flags" in data:
                for f in data["Flags"]:
                    self.flags.append(Flag(f["x"], f["y"]))
            
            # Load final flag
            if "Flag_final" in data:
                self.flag_final = Flag_final(data["Flag_final"]["x"], data["Flag_final"]["y"])
            
            # Load coins
            if "Coins" in data:
                for c in data["Coins"]:
                    self.coins.append(Coin(c["x"], c["y"]))
            
            # Load enemies
            for e in data["Enemies"]:
                cls = enemy_classes[e["type"]]
                enemy = cls(e["x"], e["y"])
                self.enemies.append(enemy)
    
    def add_player(self, name):
        """Add a new player to the game"""
        player = Player(name, self.respawn_point)
        self.players.append(player)
        return player
    
    def update_camera(self):
        """Update camera position based on players"""
        if not self.players:
            return
        mid = 0
        alive_count = 0
        for player in self.players:
            if player.is_alive:
                mid += player.x
                alive_count += 1
        if alive_count > 0:
            mid //= alive_count
            self.camera_x = int(mid) - SCREEN_WIDTH // 2
            if self.camera_x < 0:
                self.camera_x = 0
    
    def handle_collisions_and_rules(self):
        """Handle all game rules and collisions"""
        if self.won:
            return

        for player in self.players:
            if not player.is_alive:
                continue
            mrect = player.rect
            
            # Coins
            for c in self.coins:
                if not c.collected and mrect.colliderect(c.rect):
                    c.collected = True
                    self.score += 100
            
            # Goombas
            for e in self.enemies:
                if not e.is_alive:
                    continue
                if mrect.colliderect(e.rect):
                    if player.vel_y > 0 and (mrect.bottom - e.rect.top) < 20:
                        # Kill enemy
                        if e.take_damage(his_status=player.status):
                            self.score += e.points
                        player.vel_y = -8
                    else:
                        # Kill player
                        player.take_damage(his_status=e.status, respawn_point=self.respawn_point)
            
            # Player-to-player collisions
            for p in self.players:
                # Skip self-collision
                if p == player or not p.is_alive:
                    continue
                # Use the player's collision handling method
                player.handle_player_collision(p, self.respawn_point)

            # Flags
            for f in self.flags:
                if not f.is_checkpoint and mrect.colliderect(f.rect):
                    f.update(player.name)
                    self.respawn_point = (f.x, f.y)
            
            # Final flag
            if self.flag_final and mrect.colliderect(self.flag_final.rect):
                self.won = True
                self.flag_final.update(player.name)

            # Fell off world
            if player.y > 800:
                player.take_damage(from_faction='W', respawn_point=self.respawn_point)
    
    def update(self, player_inputs):
        """Update game state. player_inputs is a dict mapping player names to input dicts"""
        if self.won:
            return
        
        # Update players
        for player in self.players:
            if player.name in player_inputs:
                inp = player_inputs[player.name]
                player.update(self.platforms, inp)
        
        # Update enemies
        for e in self.enemies:
            e.update(self.platforms)
        
        # Update coins
        for c in self.coins:
            c.update()
        
        # Handle collisions
        self.handle_collisions_and_rules()
        
        # Update camera
        self.update_camera()
        
        # Score to lives conversion
        if self.score / 1000 >= 1:
            for p in self.players:
                p.lives += self.score // 1000
            self.score = self.score % 1000
    
    def get_state_dict(self):
        """Get current game state as a dict matching format.txt"""
        # Note: platform data is sent once in init, not in every update
        
        # Build entity data
        entities = {}
        for player in self.players:
            if player.is_alive:
                entities[player.name] = {
                    "x": float(player.x - self.camera_x),
                    "y": float(player.y),
                    "dir": player.direction
                }
        
        # Handle enemies - format.txt shows multiple, so we'll use a list approach
        # But since JSON doesn't allow duplicate keys, we'll send them as goomba_0, goomba_1, etc.
        # Or we can send as a list in a different structure. Let's use indexed keys for now.
        for i, enemy in enumerate(self.enemies):
            if enemy.is_alive:
                entities[f"{enemy.name}_{i}"] = {
                    "x": float(enemy.x - self.camera_x),
                    "y": float(enemy.y),
                    "dir": enemy.direction
                }
        
        # Build prop data
        coins_data = []
        for c in self.coins:
            if not c.collected:
                coins_data.append({
                    "x": float(c.x - self.camera_x),
                    "y": float(c.y),
                    "rotate": c.rotation
                })
        
        # Only send flag names/status, not positions (positions sent in init)
        flags_data = []
        for f in self.flags:
            flags_data.append({
                "name": f.touched_by if f.touched_by else ""
            })
        
        flag_final_data = None
        if self.flag_final:
            flag_final_data = {
                "name": self.flag_final.touched_by if self.flag_final.touched_by else ""
            }
        
        # Build status
        player_lives_data = {}
        for p in self.players:
            player_lives_data[f"{p.name}"] = p.lives
        
        return {
            "status": 1,
            "player_lives": player_lives_data,
            "score": self.score,
            "entity": entities,
            "prop": {
                "coin": coins_data,
                "flag": flags_data,
                "flag_final": flag_final_data
            },
            "camera_x": self.camera_x
        }
    
    def get_init_dict(self):
        """Get initial state dict for format.txt"""
        brick_platforms = []
        pipe_platforms = []
        for p in self.platforms:
            if p.width == 60 and p.height == 60:
                pipe_platforms.append({"x": p.left, "y": p.top, "w": p.width, "h": p.height})
            else:
                brick_platforms.append({"x": p.left, "y": p.top, "w": p.width, "h": p.height})
        
        # Include flag positions in initial data
        flags_data = []
        for f in self.flags:
            flags_data.append({
                "x": float(f.x),
                "y": float(f.y)
            })
        
        flag_final_data = None
        if self.flag_final:
            flag_final_data = {
                "x": float(self.flag_final.x),
                "y": float(self.flag_final.y)
            }
        
        return {
            "welcome": "Welcome to HealthyMarioBros",
            "platform": {
                "brick": brick_platforms,
                "pipe": pipe_platforms
            },
            "flag": flags_data,
            "flag_final": flag_final_data
        }


class Server:
    def __init__(self):
        # Socket tracking
        self.player_sockets = []
        self.observer_sockets = []

        # Player name / input mappings
        self.player_inputs = {}  # Maps player name to latest input dict
        self.player_names = {}   # Maps socket -> player-name
        self.player_to_socket = {}  # Maps player-name -> socket

        # Observer bookkeeping (for logging / cleanup)
        self.observer_names = {}  # Maps observer socket -> label

        self.game = Game()
        self.available_names = ["MushroomRetainer", "Mario", "Luigi"]
        self.running = True
        self.game_started = False
        self.__init_network()
        # Start accepting players in background while waiting for 'start'
        self.player_accept_thread = threading.Thread(target=self.__accept_players, daemon=True)
        self.player_accept_thread.start()
        
        self.__wait_for_start()
        if self.game_started:
            self.__start_game_loop()
    
    def __init_network(self):
        """Initialize network socket"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server.bind((HOST, PORT))
        self.server.listen()
        print(f"Server listening on {HOST}:{PORT}")
    
    def __accept_players(self):
        """Accept players in main thread until start command"""
        print("Waiting for players to connect...")
        self.server.settimeout(1.0)  # Check for start command every second
        player_count = 0
        
        while not self.game_started and self.running:
            try:
                # Try to accept new client
                conn, addr = self.server.accept()
                print(f"Client connected from {addr}")
                
                # Set socket options for low latency
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(5.0)  # 5 second timeout for role assignment
                
                # Small delay to ensure connection is fully established
                import time
                time.sleep(0.05)  # 50ms delay
                
                # Wait for client to send their role
                try:
                    role_msg = recv_json(conn, timeout=5.0)
                    if not role_msg or "role" not in role_msg:
                        print(f"Invalid role message from {addr}, disconnecting")
                        conn.close()
                        continue
                    
                    role_input = role_msg["role"]
                    # Convert to single letter: "P" for player, "O" for observer
                    if role_input == "P":
                        pass
                    elif role_input == "O":
                        print(f"Observer detected, passing to observer handler...")
                        self.__handle_observer_connection(conn, addr)
                        continue
                    else:
                        print(f"Invalid role '{role_input}' from {addr}, disconnecting")
                        conn.close()
                        continue                        
                    
                    # Only process players here
                    print(f"Player from {addr} registered")

                    # Assign name and add to game
                    if player_count < len(self.available_names):
                        player_name = self.available_names[player_count]
                        self.game.add_player(player_name)
                        self.player_to_socket[player_name] = conn
                        self.player_names[conn] = player_name
                        self.player_sockets.append(conn)
                        player_count += 1
                        print(f"  Assigned name: {player_name}")
                    else:
                        print(f"  Maximum players reached, disconnecting")
                        conn.close()
                        continue
                    
                    # Send welcome message
                    init_dict = self.game.get_init_dict()
                    welcome_msg = {
                        "welcome": "Welcome to HealthyMarioBros",
                        "role": role_input,
                        "platform": init_dict["platform"],
                        "player_name": player_name
                    }
                    # Include flag positions if available
                    if "flag" in init_dict:
                        welcome_msg["flag"] = init_dict["flag"]
                    if "flag_final" in init_dict:
                        welcome_msg["flag_final"] = init_dict["flag_final"]
                    
                    send_json(conn, welcome_msg)
                    print(f"Welcome message sent to player {player_name}")
                    
                    # Reset timeout for game loop
                    conn.settimeout(None)
                    
                except Exception as e:
                    print(f"Error processing player from {addr}: {e}")
                    conn.close()
                    
            except socket.timeout:
                # Timeout is expected - check for start command
                pass
            except Exception as e:
                print(f"Error accepting player: {e}")
        
        print(f"Game starting with {len(self.player_sockets)} players")
        # Reset server socket timeout for accepting new clients
        self.server.settimeout(None)
    
    def __handle_observer_connection(self, conn, addr):
        """Handle observer connection in observer thread"""
        def handle():
            try:
                self.observer_sockets.append(conn)
                observer_label = f"observer_{len(self.observer_sockets)}"
                self.observer_names[conn] = observer_label
                conn.settimeout(None)
                
                # Send welcome message
                init_dict = self.game.get_init_dict()
                welcome_msg = {
                    "welcome": "Welcome to HealthyMarioBros",
                    "role": "O",
                    "platform": init_dict["platform"]
                }
                # Include flag positions if available
                if "flag" in init_dict:
                    welcome_msg["flag"] = init_dict["flag"]
                if "flag_final" in init_dict:
                    welcome_msg["flag_final"] = init_dict["flag_final"]
                send_json(conn, welcome_msg)
                
                # Start handler thread
                thread = threading.Thread(
                    target=self.__handle_client,
                    args=(conn, observer_label, "O"),
                    daemon=True
                )
                thread.start()
                print(f"Observer {observer_label} connected and ready")
            except Exception as e:
                print(f"Error handling observer from {addr}: {e}")
                if conn in self.observer_sockets:
                    self.observer_sockets.remove(conn)
                if conn in self.observer_names:
                    del self.observer_names[conn]
                conn.close()
        
        # Run in a separate thread
        observer_thread = threading.Thread(target=handle, daemon=True)
        observer_thread.start()
    
    def __accept_new_clients(self):
        """Accept new clients as observers after game has started"""
        while self.running:
            try:
                conn, addr = self.server.accept()
                print(f"New client connected from {addr} (as observer)")
                
                # Set socket options
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(5.0)
                
                import time
                time.sleep(0.05)
                
                # Wait for role message
                role_msg = recv_json(conn, timeout=5.0)
                role_input = role_msg.get("role", "").upper() if role_msg else ""
                if role_msg and (role_input == "O" or role_input == "OBSERVER"):
                    self.__handle_observer_connection(conn, addr)
                else:
                    print(f"Invalid role from {addr}, disconnecting")
                    conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting new client: {e}")
                break
    
    def __wait_for_start(self):
        """Wait for 'start' command from user input"""
        print("\n" + "="*50)
        print("Waiting for 'start' command to begin the game...")
        print("Type 'start' and press Enter to begin")
        print("="*50)
        while not self.game_started:
            try:
                command = input().strip().lower()
                if command == "start":
                    self.game_started = True
                    print("Game starting!")
                    break
                elif command == "status":
                    players = len(self.player_sockets)
                    observers = len(self.observer_sockets)
                    print(f"Current status: {players} players, {observers} observers")
                else:
                    print(f"Unknown command: '{command}'. Type 'start' to begin or 'status' to check connections.")
            except (EOFError, KeyboardInterrupt):
                print("\nShutting down server...")
                self.running = False
                break
    
    def __remove_client(self, sock, player_name=None):
        """Remove a disconnected client from all lists"""
        try:
            if sock in self.player_sockets:
                self.player_sockets.remove(sock)
            if sock in self.observer_sockets:
                self.observer_sockets.remove(sock)
            
            # Determine player name if not provided
            if player_name is None:
                player_name = self.player_names.get(sock)
            
            if player_name:
                # Clean up player bookkeeping
                if player_name in self.player_to_socket:
                    del self.player_to_socket[player_name]
                if player_name in self.player_inputs:
                    del self.player_inputs[player_name]
                self.game.players = [p for p in self.game.players if p.name != player_name]
                if sock in self.player_names:
                    del self.player_names[sock]
                print(f"Player {player_name} disconnected and removed")
            else:
                # Observer cleanup
                observer_label = self.observer_names.get(sock, "observer")
                if sock in self.observer_names:
                    del self.observer_names[sock]
                print(f"Observer {observer_label} disconnected and removed")
            
            sock.close()
        except Exception as e:
            print(f"Error removing client: {e}")
    
    def __handle_client(self, sock, client_name, role):
        """Handle input from a single client (player or observer)"""
        # Set socket to non-blocking with timeout for this thread
        sock.settimeout(1.0)  # 1 second timeout - allows client to send at its own pace
        
        while self.running and self.game_started:
            try:
                # Use a longer timeout for server-side receiving
                data = recv_json(sock, timeout=1.0)
                if data is None:
                    # Timeout - no data received, but connection might still be alive
                    # This is normal when client isn't sending input
                    continue
                if data and role == "P":
                    # Only process input from players
                    # Store input for this player (data should be {"move": int, "jump": bool, "attack": bool})
                    self.player_inputs[client_name] = data
                # Observers don't send input, so we ignore their messages
            except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
                # Connection error - remove client
                err_code = getattr(e, 'winerror', getattr(e, 'errno', None))
                if err_code in (10053, 10054, 10057, 10058):  # Connection aborted/closed errors
                    print(f"Connection closed by {client_name}: {e}")
                else:
                    print(f"Error receiving from {client_name}: {e}")
                self.__remove_client(sock, client_name if role == "P" else None)
                break
            except Exception as e:
                # Other errors - log but don't necessarily disconnect
                print(f"Unexpected error from {client_name}: {e}")
                # Continue running unless it's a critical error
    
    def __start_game_loop(self):
        """Start game update loop and client handlers"""
        # Start client handler threads for all currently connected clients
        for sock in list(self.player_sockets):
            player_name = self.player_names.get(sock, f"player_{id(sock)}")
            thread = threading.Thread(
                target=self.__handle_client,
                args=(sock, player_name, "P"),
                daemon=True
            )
            thread.start()

        for sock in list(self.observer_sockets):
            observer_label = self.observer_names.get(sock, f"observer_{id(sock)}")
            thread = threading.Thread(
                target=self.__handle_client,
                args=(sock, observer_label, "O"),
                daemon=True
            )
            thread.start()
        
        # Start a thread to accept new clients (as observers) even after game starts
        accept_thread = threading.Thread(target=self.__accept_new_clients, daemon=True)
        accept_thread.start()
        
        # Game loop
        clock = time.time()
        while self.running:
            # Collect inputs
            player_inputs = {}
            for player_name, sock in self.player_to_socket.items():
                if player_name in self.player_inputs:
                    # Client may send {"mario": {...}} or just {...}
                    inp = self.player_inputs[player_name]
                    if isinstance(inp, dict) and player_name in inp:
                        # Extract from nested format
                        player_inputs[player_name] = inp[player_name]
                    elif isinstance(inp, dict) and "move" in inp:
                        # Direct format
                        player_inputs[player_name] = inp
            
            # Update game
            self.game.update(player_inputs)
            
            # Send state to all clients (players and observers)
            state = self.game.get_state_dict()
            disconnected_clients = []
            for sock in self.player_sockets + self.observer_sockets:
                try:
                    send_json(sock, state)
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    # Find which client this socket belongs to
                    client_name = self.player_names.get(sock) or self.observer_names.get(sock)
                    if client_name:
                        disconnected_clients.append((sock, client_name if sock in self.player_sockets else None))
                    else:
                        # Observer or unknown client
                        disconnected_clients.append((sock, None))
            
            # Remove disconnected clients
            for sock, player_name in disconnected_clients:
                self.__remove_client(sock, player_name)
            
            # Frame rate control (60 FPS)
            elapsed = time.time() - clock
            sleep_time = max(0, (1.0/60.0) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            clock = time.time()
    
    def shutdown(self):
        """Shutdown server"""
        self.running = False
        for sock in self.player_sockets + self.observer_sockets:
            try:
                sock.close()
            except:
                pass
        self.server.close()


if __name__ == "__main__":
    server = None
    try:
        server = Server()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        if server:
            server.shutdown()

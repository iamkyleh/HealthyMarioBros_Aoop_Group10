import socket
import json
import threading
import time
import pygame

# Add parent directory to path to import game_ver1 modules if needed
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from net import send_json, recv_json
from player import Player
from enemy import Goomba
from props import Coin, Flag, Flag_final
import addpath

HOST = '127.0.0.1'
PORT = 5000

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

class Game:
    def __init__(self):
        self.respawn_point = (80, 400)
        self.filename = "world1"
        self.platforms, self.flags, self.flag_final, self.coins, self.enemies = self._load_level(self.filename)
        self.players = []
        self.score = 0
        self.won = False
        self.camera_x = 0
        
    def _load_level(self, filename):
        with open(addpath.world_path(f"{filename}.json")) as f:
            data = json.load(f)
            platforms = []
            flags = []
            coins = []
            enemies = []
            
            # Load platforms
            for p in data["Platforms"]:
                platforms.append(pygame.Rect(p["x"], p["y"], p["w"], p["h"]))
            
            # Load flags
            if "Flags" in data:
                for f in data["Flags"]:
                    flags.append(Flag(f["x"], f["y"]))
            
            # Load final flag
            if "Flag_final" in data:
                flag_final = Flag_final(data["Flag_final"]["x"], data["Flag_final"]["y"])
            else:
                flag_final = None
            
            # Load coins
            if "Coins" in data:
                for c in data["Coins"]:
                    coins.append(Coin(c["x"], c["y"]))
            
            # Load enemies
            if "Goombas" in data:
                for e in data["Goombas"]:
                    enemies.append(Goomba(e["x"], e["y"]))
            
            return platforms, flags, flag_final, coins, enemies
    
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
                        if e.take_damage(from_faction=player.faction):
                            self.score += e.points
                        player.vel_y = -8
                    else:
                        # Kill player
                        player.take_damage(from_faction=e.faction, respawn_point=self.respawn_point)
            
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
                entities[player.name.lower()] = {
                    "x": int(player.x - self.camera_x),
                    "y": int(player.y),
                    "dir": player.direction
                }
        
        # Handle goombas - format.txt shows multiple, so we'll use a list approach
        # But since JSON doesn't allow duplicate keys, we'll send them as goomba_0, goomba_1, etc.
        # Or we can send as a list in a different structure. Let's use indexed keys for now.
        goomba_list = []
        for e in self.enemies:
            if e.is_alive:
                goomba_list.append({
                    "x": int(e.x - self.camera_x),
                    "y": int(e.y),
                    "dir": e.direction
                })
        
        # Add goombas to entities (using indexed keys to handle multiple)
        for i, goomba in enumerate(goomba_list):
            entities[f"goomba_{i}"] = goomba
        
        # Build prop data
        coins_data = []
        for c in self.coins:
            if not c.collected:
                coins_data.append({
                    "x": int(c.x - self.camera_x),
                    "y": int(c.y),
                    "rotate": c.rotation
                })
        
        flags_data = []
        for f in self.flags:
            flags_data.append({
                "x": int(f.x - self.camera_x),
                "y": int(f.y),
                "name": f.touched_by if f.touched_by else ""
            })
        
        flag_final_data = None
        if self.flag_final:
            flag_final_data = {
                "x": int(self.flag_final.x - self.camera_x),
                "y": int(self.flag_final.y),
                "name": self.flag_final.touched_by if self.flag_final.touched_by else ""
            }
        
        # Build status
        mario_lives = 0
        luigi_lives = 0
        for player in self.players:
            if player.name == "Mario":
                mario_lives = player.lives
            elif player.name == "Luigi":
                luigi_lives = player.lives
        
        return {
            "status": {
                "mario_lives": mario_lives,
                "luigi_lives": luigi_lives,
                "score": self.score
            },
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
        
        return {
            "welcome": "Welcome to HealthyMarioBros",
            "platform": {
                "brick": brick_platforms,
                "pipe": pipe_platforms
            }
        }


class Server:
    def __init__(self):
        self.clients = []
        self.client_inputs = {}  # Maps client socket to input dict
        self.playerNum = int(input("Enter number of players: "))
        self.game = Game()
        self.available_names = ["Mario", "Luigi", "Player3", "Player4"]
        self.name_to_socket = {}  # Maps player name to socket
        self.running = True
        self.__init_network()
        self.__start_game_loop()
    
    def __init_network(self):
        """Initialize network and accept clients"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Enable TCP_NODELAY to reduce latency (disable Nagle's algorithm)
        self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server.bind((HOST, PORT))
        self.server.listen()
        print(f"Server listening on {HOST}:{PORT}")
        
        # Accept clients
        for i in range(self.playerNum):
            conn, addr = self.server.accept()
            print(f"Client {i+1} connected from {addr}")
            self.clients.append(conn)
            
            # Assign player name
            if i < len(self.available_names):
                player_name = self.available_names[i]
                player = self.game.add_player(player_name)
                self.name_to_socket[player_name] = conn
                
                # Set socket options for low latency
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(None)  # Blocking mode for server
                
                # Small delay to ensure connection is fully established
                import time
                time.sleep(0.05)  # 50ms delay
                
                # Send welcome message with player name and platform data
                try:
                    welcome_msg = {
                        "welcome": "Welcome to HealthyMarioBros",
                        "player_name": player_name,
                        "platform": self.game.get_init_dict()["platform"]
                    }
                    print(f"Sending welcome message to {player_name}...")
                    send_json(conn, welcome_msg)
                    print(f"Welcome message sent to {player_name}")
                except Exception as e:
                    print(f"Error sending welcome message to {player_name}: {e}")
                    # Remove client if we can't send welcome
                    self.clients.remove(conn)
                    del self.name_to_socket[player_name]
                    self.game.players = [p for p in self.game.players if p.name != player_name]
                    conn.close()
                    raise
        
        print(f"All {self.playerNum} clients connected. Starting game...")
    
    def __remove_client(self, sock, player_name):
        """Remove a disconnected client from all lists"""
        try:
            if sock in self.clients:
                self.clients.remove(sock)
            if player_name in self.name_to_socket:
                del self.name_to_socket[player_name]
            if player_name in self.client_inputs:
                del self.client_inputs[player_name]
            # Remove player from game
            self.game.players = [p for p in self.game.players if p.name != player_name]
            print(f"Client {player_name} disconnected and removed")
            sock.close()
        except Exception as e:
            print(f"Error removing client {player_name}: {e}")
    
    def __handle_client(self, sock, player_name):
        """Handle input from a single client"""
        # Set socket to non-blocking with timeout for this thread
        sock.settimeout(1.0)  # 1 second timeout - allows client to send at its own pace
        
        while self.running:
            try:
                # Use a longer timeout for server-side receiving
                data = recv_json(sock, timeout=1.0)
                if data is None:
                    # Timeout - no data received, but connection might still be alive
                    # This is normal when client isn't sending input
                    continue
                if data:
                    # Store input for this player (data should be {"move": int, "jump": bool, "attack": bool})
                    self.client_inputs[player_name] = data
            except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
                # Connection error - remove client
                err_code = getattr(e, 'winerror', getattr(e, 'errno', None))
                if err_code in (10053, 10054, 10057, 10058):  # Connection aborted/closed errors
                    print(f"Connection closed by {player_name}: {e}")
                else:
                    print(f"Error receiving from {player_name}: {e}")
                self.__remove_client(sock, player_name)
                break
            except Exception as e:
                # Other errors - log but don't necessarily disconnect
                print(f"Unexpected error from {player_name}: {e}")
                # Continue running unless it's a critical error
    
    def __start_game_loop(self):
        """Start game update loop and client handlers"""
        # Start client handler threads
        for player_name, sock in self.name_to_socket.items():
            thread = threading.Thread(target=self.__handle_client, args=(sock, player_name), daemon=True)
            thread.start()
        
        # Game loop
        clock = time.time()
        while self.running:
            # Collect inputs
            player_inputs = {}
            for player_name, sock in self.name_to_socket.items():
                if player_name in self.client_inputs:
                    # Client may send {"mario": {...}} or just {...}
                    inp = self.client_inputs[player_name]
                    if isinstance(inp, dict) and player_name.lower() in inp:
                        # Extract from nested format
                        player_inputs[player_name] = inp[player_name.lower()]
                    elif isinstance(inp, dict) and "move" in inp:
                        # Direct format
                        player_inputs[player_name] = inp
            
            # Update game
            self.game.update(player_inputs)
            
            # Send state to all clients
            state = self.game.get_state_dict()
            disconnected_clients = []
            for sock in self.clients:
                try:
                    send_json(sock, state)
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    # Find which player this socket belongs to
                    player_name = None
                    for name, s in self.name_to_socket.items():
                        if s == sock:
                            player_name = name
                            break
                    if player_name:
                        disconnected_clients.append((sock, player_name))
            
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
        for sock in self.clients:
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

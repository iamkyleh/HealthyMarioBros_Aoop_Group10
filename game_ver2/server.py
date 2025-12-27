import socket
import json
import threading
import time
import pygame
import os
import glob

# Add parent directory to path to import game_ver1 modules if needed
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.net import send_json, recv_json
from game.player import *
from game.enemy import *
from game.props import *
from game.weapon import FireFlower, FireballProjectile
from game.game_core import GAME as BaseGAME, GameAdventure, GamePVP, GamePVE
import addpath

HOST = '0.0.0.0'
PORT = 5000

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

START_TIME = time.time()*1000
def now():
    return time.time()*1000

# Idle timeout (seconds) for no player connections at server start
IDLE_TIMEOUT = 60

enemy_classes = {
    "Goomba": Goomba,
    "KoopaTroopa": KoopaTroopa,
}

# Game implementation moved to `game.game_core`. Use imported classes here.
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

        # World selection state
        # Two-level world selection: categories -> worlds in folder
        # Categories map to subfolders under worlds/: world_advanture, world_PVP, world_PVE
        self.world_categories = ["Advanture", "PVP", "PVE"]
        self.world_folder_map = {"Advanture": "world_advanture", "PVP": "world_PVP", "PVE": "world_PVE"}
        self.available_worlds = self.__get_available_worlds()
        self.selected_category_index = 0
        self.selected_world_index = 0  # Start with first world in selected category
        self.world_selection_confirmed = False
        self.pvp_mode = False  # PVP mode toggle
        
        # Initialize game with default world (will be reloaded when confirmed)
        # Prefer Adventure default: worlds/world_advanture/world1.json if present
        adv_folder = self.world_folder_map.get("Advanture", "world_advanture")
        preferred = f"{adv_folder}/world1"
        try:
            if os.path.exists(addpath.world_path(f"{preferred}.json")):
                default_world = preferred
            else:
                # Pick first available world from first category if exists
                default_world = "world1"
                try:
                    first_cat = list(self.available_worlds.keys())[0]
                    if self.available_worlds.get(first_cat):
                        default_world = self.available_worlds[first_cat][0]
                except Exception:
                    pass
        except Exception:
            default_world = "world1"
        # Instantiate a mode-specific game class. Default to Adventure mode.
        self.game = GameAdventure(default_world, pvp_mode=False)
        self.available_names = ["Mario", "Luigi", "MushroomRetainer"]
        self.running = True
        self.game_started = False
        self.__init_network()
        # Start accepting players in background while waiting for world selection
        self.player_accept_thread = threading.Thread(target=self.__accept_players, daemon=True)
        self.player_accept_thread.start()
        
        # Start world selection loop instead of waiting for start command
        try:
            self.__world_selection_loop()
            # Only start game loop if world selection was confirmed
            if self.game_started:
                self.__start_game_loop()
            else:
                print("World selection was not confirmed, server shutting down")
                self.running = False
        except Exception as e:
            print(f"Error in world selection or game start: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
    
    def __get_available_worlds(self):
        """Get list of available world files"""
        worlds_by_cat = {}
        root = addpath.world_path("")
        for cat in self.world_categories:
            folder = self.world_folder_map.get(cat)
            worlds_by_cat[cat] = []
            if not folder:
                continue
            folder_path = addpath.world_path(folder)
            try:
                files = glob.glob(os.path.join(folder_path, "*.json"))
                for wf in sorted(files):
                    basename = os.path.basename(wf)
                    if basename.endswith('.json'):
                        worlds_by_cat[cat].append(basename[:-5])
            except Exception:
                # Missing folder -> empty list
                pass
        return worlds_by_cat
    
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
        server_start_time = time.time()
        
        while not self.game_started and self.running:
            try:
                # Try to accept new client
                conn, addr = self.server.accept()
                print(f"Client connected from {addr}")
                
                # Set socket options for low latency
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(5.0)  # 5 second timeout for role assignment
                
                # Small delay to ensure connection is fully established
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
                        self.game.add_player(player_name, pvp_mode=self.pvp_mode)
                        self.player_to_socket[player_name] = conn
                        self.player_names[conn] = player_name
                        self.player_sockets.append(conn)
                        player_count += 1
                        print(f"  Assigned name: {player_name}")
                        # update last connection time
                        server_start_time = time.time()
                    else:
                        print(f"  Maximum players reached, disconnecting")
                        conn.close()
                        continue
                    
                    # Send welcome message with world selection state
                    init_dict = self.game.get_init_dict()
                    welcome_msg = {
                        "welcome": "Welcome to HealthyMarioBros",
                        "role": role_input,
                        "platform": init_dict["platform"],
                        "player_name": player_name,
                        "world_selection": {
                            "categories": list(self.available_worlds.keys()),
                            "worlds": self.available_worlds,
                            "selected_category_index": self.selected_category_index,
                            "selected_world_index": self.selected_world_index,
                            "confirmed": self.world_selection_confirmed,
                            "pvp_mode": self.pvp_mode
                        }
                    }
                    # Include flag positions if available
                    if "flag" in init_dict:
                        welcome_msg["flag"] = init_dict["flag"]
                    if "flag_final" in init_dict:
                        welcome_msg["flag_final"] = init_dict["flag_final"]
                    
                    send_json(conn, welcome_msg)
                    print(f"Welcome message sent to player {player_name}")
                    
                    # Start handler thread for world selection input
                    thread = threading.Thread(
                        target=self.__handle_world_selection_input,
                        args=(conn, player_name),
                        daemon=True
                    )
                    thread.start()
                    
                    # Reset timeout for game loop
                    conn.settimeout(None)
                    
                except Exception as e:
                    print(f"Error processing player from {addr}: {e}")
                    conn.close()
                    
            except socket.timeout:
                # Timeout is expected - check for start command
                # If no players have connected within idle timeout, shut down
                if player_count == 0 and (time.time() - server_start_time) > IDLE_TIMEOUT:
                    print(f"No players connected within {IDLE_TIMEOUT}s, shutting down server.")
                    self.shutdown()
                    break
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
                
                # Send welcome message with world selection state
                init_dict = self.game.get_init_dict()
                welcome_msg = {
                    "welcome": "Welcome to HealthyMarioBros",
                    "role": "O",
                    "platform": init_dict["platform"],
                    "world_selection": {
                        "categories": list(self.available_worlds.keys()),
                        "worlds": self.available_worlds,
                        "selected_category_index": self.selected_category_index,
                        "selected_world_index": self.selected_world_index,
                        "confirmed": self.world_selection_confirmed
                    }
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
    
    def __handle_world_selection_input(self, sock, player_name):
        """Handle world selection input from a player"""
        sock.settimeout(1.0)
        
        while not self.game_started and self.running:
            try:
                data = recv_json(sock, timeout=1.0)
                if data is None:
                    continue
                
                # Check for world selection input
                if isinstance(data, dict):
                    # Handle world selection navigation
                    if "world_selection" in data:
                        ws_input = data["world_selection"]
                        # 'toggle_pvp' removed: PVP is determined by selected category
                        if "move" in ws_input:
                            # Up/down navigation. Client should send level: "category" or "world"
                            level = ws_input.get("level", "category")
                            if level == "category":
                                cats = list(self.available_worlds.keys())
                                if not cats:
                                    continue
                                if ws_input["move"] == -1:
                                    self.selected_category_index = (self.selected_category_index - 1) % len(cats)
                                elif ws_input["move"] == 1:
                                    self.selected_category_index = (self.selected_category_index + 1) % len(cats)
                                # reset world index when category changes
                                self.selected_world_index = 0
                                self.__broadcast_world_selection_update()
                            else:
                                # world level
                                cats = list(self.available_worlds.keys())
                                if not cats:
                                    continue
                                sel_cat = cats[self.selected_category_index]
                                worlds = self.available_worlds.get(sel_cat, [])
                                if not worlds:
                                    continue
                                if ws_input["move"] == -1:
                                    self.selected_world_index = (self.selected_world_index - 1) % len(worlds)
                                elif ws_input["move"] == 1:
                                    self.selected_world_index = (self.selected_world_index + 1) % len(worlds)
                                self.__broadcast_world_selection_update()
                        elif "confirm" in ws_input and ws_input["confirm"]:
                            # Confirm world selection and start game
                            cats = list(self.available_worlds.keys())
                            if not cats:
                                continue
                            sel_cat = cats[self.selected_category_index]
                            worlds = self.available_worlds.get(sel_cat, [])
                            if not worlds:
                                continue
                            selected_world = worlds[self.selected_world_index]
                            print(f"Player {player_name} confirmed world selection: {sel_cat}/{selected_world}")
                            try:
                                # Update game PVP mode and reload level
                                self.game.pvp_mode = self.pvp_mode
                                # Update all existing players' factions based on PVP mode
                                for i, p in enumerate(self.game.players):
                                    if self.pvp_mode:
                                        p.faction = f"p{i + 1}"
                                    else:
                                        p.faction = 'P'
                                # Try to load the world first (world files are inside category folders)
                                folder = self.world_folder_map.get(sel_cat, "")
                                filename = selected_world
                                # If world file is in a subfolder, construct path accordingly by reloading with folder/filename
                                # Our Game._load_level uses addpath.world_path which expects name relative to worlds dir
                                # So pass folder/filename (without .json)
                                composed_name = f"{folder}/{filename}" if folder else filename
                                self.game.reload_level(composed_name)
                                # Only mark as confirmed if loading succeeded
                                self.world_selection_confirmed = True
                                self.__broadcast_world_selection_update()
                                # Start game after a short delay
                                time.sleep(0.5)
                                self.game_started = True
                                print(f"Game starting with world: {selected_world}, PVP mode: {self.pvp_mode}")
                                break
                            except Exception as e:
                                print(f"Error loading world {selected_world}: {e}")
                                import traceback
                                traceback.print_exc()
                                # Send error message back to client
                                error_msg = {
                                    "world_selection": {
                                        "categories": list(self.available_worlds.keys()),
                                        "worlds": self.available_worlds,
                                        "selected_category_index": self.selected_category_index,
                                        "selected_world_index": self.selected_world_index,
                                        "confirmed": False,
                                        "error": f"Failed to load world: {e}"
                                    }
                                }
                                try:
                                    send_json(sock, error_msg)
                                except:
                                    pass
                                # Don't break, allow retry
                                continue
            except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
                print(f"Error receiving world selection input from {player_name}: {e}")
                break
            except Exception as e:
                if self.running:
                    print(f"Unexpected error in world selection handler: {e}")
    
    def __broadcast_world_selection_update(self):
        """Broadcast world selection state to all clients"""
        update_msg = {
            "world_selection": {
                "categories": list(self.available_worlds.keys()),
                "worlds": self.available_worlds,
                "selected_category_index": self.selected_category_index,
                "selected_world_index": self.selected_world_index,
                "confirmed": self.world_selection_confirmed,
                "pvp_mode": self.pvp_mode
            }
        }
        
        # If confirmed, also send updated platform data
        if self.world_selection_confirmed:
            init_dict = self.game.get_init_dict()
            update_msg["platform"] = init_dict["platform"]
            if "flag" in init_dict:
                update_msg["flag"] = init_dict["flag"]
            if "flag_final" in init_dict:
                update_msg["flag_final"] = init_dict["flag_final"]
        
        # Send to all connected clients
        disconnected = []
        for sock in self.player_sockets + self.observer_sockets:
            try:
                send_json(sock, update_msg)
            except Exception as e:
                print(f"Error broadcasting world selection update: {e}")
                disconnected.append(sock)
        
        # Remove disconnected clients
        for sock in disconnected:
            self.__remove_client(sock)
    
    def __world_selection_loop(self):
        """World selection loop - wait for players to select world"""
        print("\n" + "="*50)
        print("Waiting for players to select world...")
        print("Players can use UP/DOWN arrow keys to navigate and Enter to confirm")
        print("="*50)
        
        # Broadcast initial world selection state
        self.__broadcast_world_selection_update()
        
        # Wait for world selection confirmation
        while not self.game_started and self.running:
            time.sleep(0.1)  # Small delay to prevent busy waiting
            if self.world_selection_confirmed:
                # Give a moment for all threads to see the game_started flag
                time.sleep(0.2)
                self.game_started = True
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
                    # Ignore world selection messages (they're handled by world selection handlers)
                    if isinstance(data, dict) and "world_selection" in data:
                        continue
                    # Store input for this player (data should be {"move": int, "jump": bool, "attack": bool} or {player_name: {...}})
                    self.player_inputs[client_name] = data
                    # Debug: print received input
                    if isinstance(data, dict) and ("move" in data or client_name in data):
                        with open("recieve_log.txt", "a") as f:
                            f.write(f"Received input from {client_name}: {data}")
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
        try:
            print("Starting game loop...")
            print(f"game_started = {self.game_started}, running = {self.running}")
            print(f"Player sockets: {len(self.player_sockets)}, Observer sockets: {len(self.observer_sockets)}")
            
            # Wait a moment to ensure world selection handlers have exited
            time.sleep(0.2)
            
            # Start client handler threads for all currently connected clients
            for sock in list(self.player_sockets):
                player_name = self.player_names.get(sock, f"player_{id(sock)}")
                thread = threading.Thread(
                    target=self.__handle_client,
                    args=(sock, player_name, "P"),
                    daemon=True
                )
                thread.start()
                print(f"Started game handler for player {player_name}")

            for sock in list(self.observer_sockets):
                observer_label = self.observer_names.get(sock, f"observer_{id(sock)}")
                thread = threading.Thread(
                    target=self.__handle_client,
                    args=(sock, observer_label, "O"),
                    daemon=True
                )
                thread.start()
                print(f"Started game handler for observer {observer_label}")
        except Exception as e:
            print(f"Error starting game loop: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Start a thread to accept new clients (as observers) even after game starts
        accept_thread = threading.Thread(target=self.__accept_new_clients, daemon=True)
        accept_thread.start()
        
        # Game loop
        clock = time.time()
        while self.running:
            try:
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
                
                # Debug: print collected inputs
                # if player_inputs:
                #     with open("input_log.txt", "a") as f:
                #         f.write(f"Collected inputs: {player_inputs}")
                
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
                # If no players or observers remain, shut down the server
                if not self.player_sockets and not self.observer_sockets:
                    print("No clients connected, shutting down server.")
                    self.shutdown()
                    break
                
                # Frame rate control (60 FPS)
                elapsed = time.time() - clock
                sleep_time = max(0, (1.0/60.0) - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                clock = time.time()
            except Exception as e:
                print(f"Error in game loop: {e}")
                import traceback
                traceback.print_exc()
                # Continue running unless it's a critical error
                time.sleep(0.1)  # Small delay before continuing
    
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

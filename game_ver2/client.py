# client.py
import socket
import pygame
import math
from net import send_json, recv_json
import addpath

HOST = "127.0.0.1"
PORT = 5000

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (220, 50, 50)

def load_image(name, size=None):
    """Load an image by name (e.g., 'Brick.png'); optionally scale to size=(w,h)."""
    try:
        img = pygame.image.load(addpath.image_path(name)).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception as e:
        print(f"Failed to load image '{name}': {e}")
        return None

def draw_tiled(surface, image, p, camera_x):
    img_w, img_h = image.get_width(), image.get_height()
    for y in range(p.top, p.bottom, img_h):
        for x in range(p.left, p.right, img_w):
            surface.blit(image, (x - camera_x, y))

class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Healthy Mario Bros (Client)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 64)

        # Player / world state
        self.platforms = {"brick": [], "pipe": []}
        self.camera_x = 0
        self.latest_state = None
        self.running = True

        # Networking fields
        self.s = None
        self.client_id = None
        self.name = None
        self.role = None  # "P" for player or "O" for observer

        # Load images
        self._load_img()
        
        self._init_networking()

    # -------------------- Networking ------------------------
    def _init_networking(self):
        # Ask user for role FIRST, before connecting
        while True:
            role_input = input("Enter your role [P (player) / O (observer)]: ").strip().upper()
            if role_input in ["P", "O"]:
                self.role = role_input
                break
            print("Invalid role. Please enter 'P' for player or 'O' for observer.")
        
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Enable TCP_NODELAY for low latency
            self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # For initial connection, use a longer timeout to ensure welcome message is received
            self.s.settimeout(10.0)  # 10 second timeout for initial connection
            
            # Connect to server (same port for both players and observers)
            print(f"Connecting to server on {HOST}:{PORT}...")
            self.s.connect((HOST, PORT))
            print("Connected! Sending role...")
            
            # Send role to server immediately after connecting
            send_json(self.s, {"role": self.role})
            print(f"Role '{self.role}' sent to server. Waiting for welcome message...")

            # Welcome packet with platform data - wait with longer timeout
            # Try multiple times in case of timing issues
            msg = None
            for attempt in range(3):
                msg = recv_json(self.s, timeout=5.0)  # Wait up to 5 seconds for welcome
                if msg:
                    break
                print(f"Attempt {attempt + 1} failed, retrying...")
                import time
                time.sleep(0.1)  # Small delay before retry
            
            if msg and "welcome" in msg:
                if "platform" in msg:
                    self.platforms = msg["platform"]
                if "player_name" in msg:
                    self.name = msg["player_name"]
                if "role" in msg:
                    self.role = msg["role"]
                role_name = "player" if self.role == "P" else "observer"
                print(f"Connected as {role_name}" + (f" ({self.name})" if self.name else ""))
            else:
                print(f"Failed to receive welcome message. Received: {msg}")
                if msg:
                    print(f"Message keys: {msg.keys() if isinstance(msg, dict) else 'Not a dict'}")
                self.running = False
                return
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False
            return
        
        # Now switch to non-blocking mode for game loop
        self.s.settimeout(0.01)  # 10ms timeout for game loop

    # -------------------- Game Loop -------------------------
    def run(self):
        while self.running:
            self._handle_events()
            # Receive state first (non-blocking)
            self._receive_state()
            # Then send input
            self._send_input()
            # Draw
            self._draw()
            self.clock.tick(FPS)
        pygame.quit()
        self.s.close()

    # -------------------- Event Handling --------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    # --------------------- Input Send -----------------------
    def _send_input(self):
        # Only send input if this client is a player
        if self.role != "P":
            return
            
        # Check if socket is still valid
        if self.s is None or not self.running:
            return
            
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move = 1
        
        jump = bool(keys[pygame.K_UP] or keys[pygame.K_w])
        attack = bool(keys[pygame.K_SPACE])
        
        # Only send if input changed or every few frames to reduce network traffic
        current_input = {"move": move, "jump": jump, "attack": attack}
        if not hasattr(self, '_last_input') or self._last_input != current_input:
            try:
                # Format according to format.txt: {"mario": {...}, "luigi": {...}}
                # Send input with player name as key
                if self.name:
                    send_json(self.s, {self.name.lower(): current_input})
                else:
                    # Fallback if name not received
                    send_json(self.s, current_input)
                self._last_input = current_input
            except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
                # Connection lost - stop trying to send
                print(f"Connection lost: {e}")
                self.running = False
            except Exception as e:
                # Other errors - log but don't necessarily stop
                print(f"Error sending input: {e}")
                # Only stop on critical errors
                if "10053" in str(e) or "10054" in str(e) or "Connection" in str(type(e).__name__):
                    self.running = False

    # -------------------- RECEIVE STATE ---------------------
    def _receive_state(self):
        """Receive state updates (non-blocking, won't stall game loop)"""
        if self.s is None or not self.running:
            return
            
        try:
            # Try to receive multiple messages if available (catch up on missed frames)
            for _ in range(5):  # Max 5 messages per frame to prevent lag
                msg = recv_json(self.s, timeout=0.001)  # Very short timeout
                if msg is None:
                    break  # No more data available
                if "status" in msg:  # Check if it's a state update
                    self.latest_state = msg
                elif "welcome" in msg:
                    # Handle welcome message if received late
                    if "platform" in msg:
                        self.platforms = msg["platform"]
                    if "player_name" in msg:
                        self.name = msg["player_name"]
        except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
            # Connection lost
            print(f"Connection lost while receiving: {e}")
            self.running = False
        except Exception as e:
            # Only stop on actual connection errors, not timeouts
            err_str = str(e).lower()
            if "timed out" not in err_str and "10060" not in str(e):
                # Check for connection abort errors
                if "10053" in str(e) or "10054" in str(e) or "connection" in err_str:
                    print(f"Connection error: {e}")
                    self.running = False

    # -------------------- DRAW FUNCTIONS --------------------
    def _draw_cloud(self, x, y):
        pygame.draw.ellipse(self.screen, WHITE, (x, y, 100, 40))
        pygame.draw.ellipse(self.screen, WHITE, (x + 30, y - 10, 120, 50))

    def _load_img(self):
        self.image = {}
        self.image["Brick"] = load_image("Brick.png", (32, 32))
        self.image["Pipe"] = load_image("Pipe.png", (60, 60))
        self.image["Coin"] = load_image("Coin.png", (20, 28))
        self.image["Goomba"] = load_image("Goomba.png", (32, 32))
        self.image["Mario"] = load_image("Mario.png", (24, 32))
        self.image["Luigi"] = load_image("Luigi.png", (24, 32))
        self.image["Flag"] = load_image("Flag.png", (48, 144))
        self.image["Flag_Mario"] = load_image("Flag_Mario.png", (48, 144))
        self.image["Flag_Luigi"] = load_image("Flag_Luigi.png", (48, 144))
        self.image["Flag_final"] = load_image("Flag_final.png", (48, 256))
        self.image["Flag_final_Mario"] = load_image("Flag_final_Mario.png", (48, 256))
        self.image["Flag_final_Luigi"] = load_image("Flag_final_Luigi.png", (48, 256))
        missing = False
        for name, img in self.image.items():
            if not img:
                missing = True
                print(f"ERROR: Failed loading image {name}")
        if missing:
            pygame.quit()

    def _draw(self):
        self.screen.fill(SKY_BLUE)
        # --- CLOUD BACKGROUND ---
        for i in range(10):
            cx = (i * 200 - int(self.camera_x * 0.5)) % (SCREEN_WIDTH + 100) - 50
            cy = 80 + (i % 3) * 30
            self._draw_cloud(cx, cy)

        # Draw platforms (always available from init)
        self._draw_platform_and_pipe()
        
        # check if we have a latest state
        if self.latest_state:
            # Update camera from state
            self.camera_x = self.latest_state.get("camera_x", 0)
            self._draw_entities()
            self._draw_props()
            self._draw_status()
        else:
            # Show waiting message
            waiting_text = self.font.render("Waiting for game state...", True, BLACK)
            self.screen.blit(waiting_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))

        pygame.display.flip()

    def _draw_platform_and_pipe(self):
        # Use stored platform data from init
        for b in self.platforms["brick"]:
            rect = pygame.Rect(b["x"], b["y"], b["w"], b["h"])
            draw_tiled(self.screen, self.image["Brick"], rect, self.camera_x)
        for p in self.platforms["pipe"]:
            rect = pygame.Rect(p["x"], p["y"], p["w"], p["h"])
            self.screen.blit(self.image["Pipe"], (p["x"] - self.camera_x, p["y"]))

    def _draw_entities(self):
        if "entity" not in self.latest_state:
            return
        ent = self.latest_state["entity"]
        for name, parameters in ent.items():
            # Handle goombas with indexed names
            if name.startswith("goomba_"):
                name = "Goomba"
            else:
                name = name.capitalize()
            
            img = self.image.get(name)
            if img:
                if parameters["dir"] == -1:
                    img = pygame.transform.flip(img, True, False)
                self.screen.blit(img, (parameters["x"], parameters["y"]))
    
    def _draw_props(self):
        if "prop" not in self.latest_state:
            return
        props = self.latest_state["prop"]
        
        # Draw coins
        for c in props.get("coin", []):
            img = self.image["Coin"]
            scale = abs(math.sin(c["rotate"]))
            scaled_w = max(2, int(img.get_width() * scale))
            scaled_img = pygame.transform.scale(img, (scaled_w, img.get_height()))
            x = c["x"] + (img.get_width() - scaled_w) // 2
            y = c["y"]
            self.screen.blit(scaled_img, (x, y))
        
        # Draw flags
        for f in props.get("flag", []):
            flag_name = f.get("name", "")
            if flag_name:
                img_name = f"Flag_{flag_name}"
            else:
                img_name = "Flag"
            img = self.image.get(img_name, self.image["Flag"])
            self.screen.blit(img, (f["x"], f["y"]))
        
        # Draw final flag
        if props.get("flag_final"):
            ff = props["flag_final"]
            flag_name = ff.get("name", "")
            if flag_name:
                img_name = f"Flag_final_{flag_name}"
            else:
                img_name = "Flag_final"
            img = self.image.get(img_name, self.image["Flag_final"])
            self.screen.blit(img, (ff["x"], ff["y"]))
    
    def _draw_status(self):
        status = self.latest_state["status"]
        y = 16
        mario_text = self.font.render(f"Mario X {status['mario_lives']}", True, BLACK)
        self.screen.blit(mario_text, (16, y))
        y += self.font.get_linesize()

        luigi_text = self.font.render(f"Luigi X {status['luigi_lives']}", True, BLACK)
        self.screen.blit(luigi_text, (16, y))

        score_text = self.font.render(f"Score: {status['score']}", True, BLACK)
        self.screen.blit(score_text, (650, 16))


if __name__ == "__main__":
    print("!!! NOTICE !!!\nCheck the HOST is on the correct IP address.\nPlace it with IPv4 address of the server.")
    GameClient().run()

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

        # Load images
        self._load_img()
        
        self._init_networking()

    # -------------------- Networking ------------------------
    def _init_networking(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((HOST, PORT))

        # Welcome packet with platform data
        msg = recv_json(self.s)
        if msg and "welcome" in msg:
            if "platform" in msg:
                self.platforms = msg["platform"]
            if "player_name" in msg:
                self.name = msg["player_name"]

    # -------------------- Game Loop -------------------------
    def run(self):
        while self.running:
            self._handle_events()
            self._send_input()
            self._receive_state()
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
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move = 1
        
        jump = bool(keys[pygame.K_UP] or keys[pygame.K_w])
        attack = bool(keys[pygame.K_SPACE])
        try:
            # Format according to format.txt: {"mario": {...}, "luigi": {...}}
            # Send input with player name as key
            if self.name:
                send_json(self.s, {self.name.lower(): {"move": move, "jump": jump, "attack": attack}})
            else:
                # Fallback if name not received
                send_json(self.s, {"move": move, "jump": jump, "attack": attack})
        except:
            self.running = False

    # -------------------- RECEIVE STATE ---------------------
    def _receive_state(self):
        try:
            msg = recv_json(self.s)
            if msg and "status" in msg:  # Check if it's a state update
                self.latest_state = msg
        except:
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
    GameClient().run()

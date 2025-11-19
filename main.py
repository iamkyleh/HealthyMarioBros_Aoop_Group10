import sys
import pygame
import addpath
import json

from player import Player
from enemy import *
from props import *

# --- constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

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


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Healthy Mario Bros")
        self.clock = pygame.time.Clock()

        # camera
        self.camera_x = 0

        # entities
        # fix: use a single mario like the rest of the code expects
        self.player = [Player('Mario', 80, 400, "arrows"), Player('Luigi', 120, 400, "wasd")]
        self.platforms, self.coins, self.enemies = self._load_level()
        self._selectmode()

        # UI state
        self.score = 0
        self.lives = 3
        self.won = False
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 64)

        # --- load images once ---
        self._imageloading()

    def _selectmode(self):
        try:
            self.playernum = int(input("enter number of players: [1/2]"))
        except Exception:
            print("invalid input, defaulting to 1 player")
            self.playernum = 1
        self.player = self.player[:self.playernum]

    def _imageloading(self):
        # guarantee every image is workng, no need to check after
        self.image = {}
        self.image["brick"] = load_image("Brick.png", (32, 32))
        self.image["pipe"] = load_image("Pipe.png", (60, 60))
        # self.image["cloud"] = load_image("Cloud.png", (140, 70))
        missing = False
        for name, img in self.image.items():
            if not img:
                missing = True
                print(f"ERROR: Failed loading image {name}")
        if missing:
            pygame.quit()
            sys.exit()

    def _load_level(self, filename="world1"):
        with open(addpath.world_path(f"{filename}.json")) as f:
            data = json.load(f)
            platforms, coins, enemies = [], [], []
            platforms.extend([pygame.Rect(p["x"], p["y"], p["w"], p["h"]) for p in data["Platforms"]])
            coins.extend([Coin(c["x"], c["y"]) for c in data["Coins"]])
            enemies.extend([Goomba(e["x"], e["y"]) for e in data["Goombas"]])
            return platforms, coins, enemies
    
    def draw_cloud(self, x, y):
            pygame.draw.ellipse(self.screen, WHITE, (x, y, 100, 40))
            pygame.draw.ellipse(self.screen, WHITE, (x + 30, y - 10, 120, 50))

    def draw_background(self):
        self.screen.fill(SKY_BLUE)
        for i in range(10):
            cx = (i * 200 - int(self.camera_x * 0.5)) % (SCREEN_WIDTH + 100) - 50
            cy = 80 + (i % 3) * 30
            self.draw_cloud(cx, cy)

    def update_camera(self):
        mid = 0
        for player in self.player:
            mid += player.x
        mid //= len(self.player)
        self.camera_x = int(mid) - SCREEN_WIDTH // 2
        if self.camera_x < 0:
            self.camera_x = 0

    def handle_collisions_and_rules(self):
        if self.won:
            return

        for player in self.player:
            mrect = player.rect
            # coins
            for c in self.coins:
                if not c.collected and mrect.colliderect(c.rect):
                    c.collected = True
                    self.score += 100
            # goombas
            for e in self.enemies:
                if not e.is_alive:
                    continue
                if mrect.colliderect(e.rect):
                    if player.vel_y > 0 and (mrect.bottom - e.rect.top) < 20:
                        e.stomped()
                        player.vel_y = -8
                        self.score += 200
                    else:
                        player.reborn()

            # fell off world
            if player.y > 800:
                player.reborn()

    def draw_world(self):
        # Draw platforms using images instead of rectangles:
        #  - For pipe-sized rects (60x60), draw the pipe image once.
        #  - For everything else, tile bricks to fill the rect area.
        for p in self.platforms:
            if p.width == 60 and p.height == 60:
                self.screen.blit(self.image["pipe"], (p.x - self.camera_x, p.y))
            else:
                draw_tiled(self.screen, self.image["brick"], p, self.camera_x)

        # coins & enemies (their own draw() can use images internally)
        for c in self.coins:
            c.draw(self.screen, self.camera_x)
        for e in self.enemies:
            e.draw(self.screen, self.camera_x)

        # player
        for player in self.player: 
            player.draw(self.screen, self.camera_x)

    def draw_ui(self):
        hud = self.font.render(f"Score: {self.score}   Lives: {self.player[0].lives}", True, BLACK)
        self.screen.blit(hud, (16, 16))
        if self.won:
            msg = self.big_font.render("YOU REACHED THE FLAG!", True, BLACK)
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 80))

    def debug_mouse_overlay(self):
        """Draw screen/world mouse coordinates (one function by request)."""
        mx, my = pygame.mouse.get_pos()
        wx = mx + self.camera_x
        text = self.font.render(f"S:({mx},{my})  W:({wx},{my})", True, (0, 0, 0))
        # slight shadow for readability
        self.screen.blit(self.font.render(f"S:({mx},{my})  W:({wx},{my})", True, (255, 255, 255)), (11,  SCREEN_HEIGHT - 31))
        self.screen.blit(text, (10, SCREEN_HEIGHT - 32))

    def run(self):
        running = True
        while running:
            # input
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            keys = pygame.key.get_pressed()

            # update
            if not self.won:
                for player in self.player:
                    player.update(self.platforms, keys)
                for e in self.enemies:
                    e.update(self.platforms)
                for c in self.coins:
                    c.update()
                self.handle_collisions_and_rules()
            else:
                pass

            self.update_camera()

            # draw
            self.draw_background()
            self.draw_world()
            self.draw_ui()
            self.debug_mouse_overlay()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()
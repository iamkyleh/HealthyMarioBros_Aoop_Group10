# client.py
import socket
import pygame
from net import send_json, recv_json

HOST = "127.0.0.1"
PORT = 65432
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (220, 50, 50)


class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Healthy Mario Bros (Client)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 64)

        # Player / world state
        self.platforms = []
        self.camera_x = 0
        self.latest_state = None
        self.running = True

        # Networking fields
        self.s = None
        self.client_id = None
        self.name = None

        self._init_networking()

    # -------------------- Networking ------------------------
    def _init_networking(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((HOST, PORT))

        # Welcome packet
        msg = recv_json(self.s)
        if msg and msg.get("type") == "welcome":
            self.client_id = msg.get("client_id")
            self.name = msg.get("name")

        # Init world data
        init_msg = recv_json(self.s)
        if init_msg and init_msg.get("type") == "init":
            self.platforms = init_msg.get("platforms", [])

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
        movement = 0
        attack = bool(keys[pygame.K_SPACE])

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            movement = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            movement = 1

        try:
            send_json(self.s, {"movement": movement, "attack": attack})
        except:
            self.running = False

    # -------------------- RECEIVE STATE ---------------------
    def _receive_state(self):
        msg = recv_json(self.s)
        if msg and msg.get("type") == "state":
            self.latest_state = msg["data"]
            self.camera_x = self.latest_state.get("camera_x", 0)

    # -------------------- DRAW FUNCTIONS --------------------
    def draw_cloud(self, x, y):
        pygame.draw.ellipse(self.screen, WHITE, (x, y, 100, 40))
        pygame.draw.ellipse(self.screen, WHITE, (x + 30, y - 10, 120, 50))

    def _draw(self):
        self.screen.fill(SKY_BLUE)

        # Parallax clouds
        for i in range(10):
            cx = (i * 200 - int(self.camera_x * 0.5)) % (SCREEN_WIDTH + 100) - 50
            cy = 80 + (i % 3) * 30
            self.draw_cloud(cx, cy)

        # Platforms
        for p in self.platforms:
            rect = pygame.Rect(p["x"] - self.camera_x, p["y"], p["w"], p["h"])
            color = (120, 120, 120) if (p["w"] == 60 and p["h"] == 60) else (160, 100, 60)
            pygame.draw.rect(self.screen, color, rect)

        # Entities from server
        if self.latest_state:
            self._draw_entities()

        pygame.display.flip()

    def _draw_entities(self):
        st = self.latest_state

        # Coins
        for c in st["coins"]:
            if not c["collected"]:
                pygame.draw.circle(self.screen, (255, 200, 0),
                                   (int(c["x"] - self.camera_x), int(c["y"])), 8)

        # Enemies
        for e in st["enemies"]:
            if e["alive"]:
                pygame.draw.rect(self.screen, RED,
                                 (e["x"] - self.camera_x, e["y"], e["w"], e["h"]))

        # Flags
        for f in st["flags"]:
            color = (50, 180, 50) if f["checkpoint_touched"] else (50, 120, 50)
            pygame.draw.rect(self.screen, color,
                             (f["x"] - self.camera_x, f["y"], f["w"], f["h"]))

        ff = st["flag_final"]
        pygame.draw.rect(self.screen, (30, 160, 30),
                         (ff["x"] - self.camera_x, ff["y"], ff["w"], ff["h"]))

        # Players + HUD
        y_ui = 16
        for p in st["players"]:
            pygame.draw.rect(self.screen, BLACK,
                             (p["x"] - self.camera_x, p["y"], p["w"], p["h"]))
            lives_ui = self.font.render(f"{p['name']} X {p['lives']}", True, BLACK)
            self.screen.blit(lives_ui, (16, y_ui))
            y_ui += self.font.get_linesize()

        # Score + win message
        score_ui = self.font.render(f"Score: {st['score']}", True, BLACK)
        self.screen.blit(score_ui, (650, 16))

        if st["won"]:
            msg = self.big_font.render("YOU REACHED THE FLAG!", True, BLACK)
            self.screen.blit(msg,
                             (SCREEN_WIDTH // 2 - msg.get_width() // 2, 80))


if __name__ == "__main__":
    GameClient().run()

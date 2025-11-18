# main.py
import sys
import pygame

from player import Mario
from enemy import Goomba, Coin, Flag

# --- constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

SKY_BLUE = (92, 148, 252)
MARIO_RED = (255, 0, 0)
MARIO_BLUE = (0, 0, 255)
BRICK_RED = (205, 92, 92)
PIPE_GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mini Mario (Python/Pygame)")
        self.clock = pygame.time.Clock()

        # camera
        self.camera_x = 0

        # entities
        self.mario = Mario(80, 400)
        self.goombas = [Goomba(520, 420), Goomba(980, 420)]
        self.coins = [
            Coin(300, 300), Coin(340, 280), Coin(380, 300),
            Coin(700, 260), Coin(740, 260)
        ]

        # level geometry and finish flag
        self.platforms = self._build_level()
        self.flag = Flag(1700, 500)  # near the end of ground

        # UI state
        self.score = 0
        self.lives = 3
        self.won = False
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 64)

    def _build_level(self):
        plats = []
        # ground tiles
        for i in range(0, 2000, 200):
            plats.append(pygame.Rect(i, 500, 200, 100))
        # bricks
        plats.append(pygame.Rect(260, 380, 120, 24))
        plats.append(pygame.Rect(600, 360, 160, 24))
        plats.append(pygame.Rect(960, 340, 120, 24))
        plats.append(pygame.Rect(1220, 420, 160, 24))
        # pipe
        plats.append(pygame.Rect(820, 440, 60, 60))
        return plats

    # simple background with clouds
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
        self.camera_x = int(self.mario.x) - SCREEN_WIDTH // 2
        if self.camera_x < 0:
            self.camera_x = 0

    def handle_collisions_and_rules(self):
        if self.won:
            return

        mrect = self.mario.rect

        # coins
        for c in self.coins:
            if not c.collected and mrect.colliderect(c.rect):
                c.collected = True
                self.score += 100

        # goombas
        for g in self.goombas:
            if not g.alive:
                continue
            if mrect.colliderect(g.rect):
                if self.mario.vel_y > 0 and self.mario.y + self.mario.height - 6 <= g.y:
                    g.stomped()
                    self.mario.vel_y = -8
                    self.score += 200
                else:
                    self.lives -= 1
                    # knockback
                    self.mario.x -= 24 if self.mario.x < g.x else -24

        # finish flag
        if mrect.colliderect(self.flag.rect):
            self.won = True

        # fell off world
        if self.mario.y > 800:
            self.lives -= 1
            self.mario.x, self.mario.y = 80, 400
            self.mario.vel_x = self.mario.vel_y = 0.0

    def draw_world(self):
        # platforms
        for p in self.platforms:
            color = PIPE_GREEN if p.width <= 80 else BRICK_RED
            pygame.draw.rect(self.screen, color, (p.x - self.camera_x, p.y, p.width, p.height))

        # coins & enemies
        for c in self.coins:
            c.draw(self.screen, self.camera_x)
        for g in self.goombas:
            g.draw(self.screen, self.camera_x)

        # finish flag
        self.flag.draw(self.screen, self.camera_x)

        # player
        self.mario.draw(self.screen, self.camera_x)

    def draw_ui(self):
        hud = self.font.render(f"Score: {self.score}   Lives: {self.lives}", True, BLACK)
        self.screen.blit(hud, (16, 16))
        if self.won:
            msg = self.big_font.render("YOU REACHED THE FLAG!", True, BLACK)
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 80))

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
                self.mario.update(self.platforms, keys)
                for g in self.goombas:
                    g.update(self.platforms)
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

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()

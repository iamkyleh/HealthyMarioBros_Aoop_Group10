# enemy.py
import math
import pygame

COIN_YELLOW = (255, 215, 0)
GOOMBA_BROWN = (139, 69, 19)
FLAG_GREEN = (0, 170, 0)
FLAG_WHITE = (240, 240, 240)

class Goomba:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.width = 28
        self.height = 28
        self.vel_x = -1.0
        self.vel_y = 0.0
        self.alive = True
        self.on_ground = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def _ground_ahead(self, platforms, step=6):
        """Return True if there's ground under the leading edge after a small step."""
        probe_x = self.x + (self.width + 1 if self.vel_x > 0 else -1) + (step if self.vel_x > 0 else -step)
        probe_rect = pygame.Rect(int(probe_x), int(self.y + self.height + 1), 2, 2)
        return any(p.colliderect(probe_rect) for p in platforms)

    def update(self, platforms):
        if not self.alive:
            return

        # horizontal patrol
        self.x += self.vel_x
        r = self.rect
        for p in platforms:
            if r.colliderect(p):
                if self.vel_x > 0:
                    self.x = p.left - self.width
                else:
                    self.x = p.right
                self.vel_x *= -1
                r = self.rect

        # gravity + vertical collisions
        self.vel_y += 0.8
        self.y += self.vel_y
        r = self.rect
        self.on_ground = False
        for p in platforms:
            if r.colliderect(p):
                if self.vel_y > 0:
                    self.y = p.top - self.height
                    self.vel_y = 0
                    self.on_ground = True
                else:
                    self.y = p.bottom
                    self.vel_y = 0
                r = self.rect

        # edge turn
        if self.on_ground and not self._ground_ahead(platforms):
            self.vel_x *= -1

    def stomped(self):
        self.alive = False

    def draw(self, screen, camera_x):
        if not self.alive:
            return
        x = int(self.x - camera_x)
        y = int(self.y)
        pygame.draw.rect(screen, GOOMBA_BROWN, (x, y, self.width, self.height))


class Coin:
    """A spinning coin using width scaling via sine."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.width = 18
        self.height = 18
        self.rotation = 0.0
        self.collected = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self):
        if not self.collected:
            self.rotation += 0.2

    def draw(self, screen, camera_x):
        if self.collected:
            return
        scale = abs(math.sin(self.rotation))
        scaled_w = max(2, int(self.width * scale))
        x = int(self.x - camera_x) + (self.width - scaled_w) // 2
        y = int(self.y)
        pygame.draw.ellipse(screen, COIN_YELLOW, (x, y, scaled_w, self.height))


class Flag:
    """Simple finish flag: a pole + triangular flag; collision ends the level."""
    def __init__(self, x, ground_y):
        self.x = float(x)
        self.y = float(ground_y) - 120
        self.width = 10
        self.height = 120

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def draw(self, screen, camera_x):
        pole_x = int(self.x - camera_x)
        pole_y = int(self.y)
        # pole
        pygame.draw.rect(screen, (180, 180, 180), (pole_x, pole_y, self.width, self.height))
        # flag (triangle)
        points = [
            (pole_x + self.width, pole_y + 10),
            (pole_x + self.width + 40, pole_y + 25),
            (pole_x + self.width, pole_y + 40),
        ]
        pygame.draw.polygon(screen, FLAG_GREEN, points)
        pygame.draw.polygon(screen, FLAG_WHITE, [
            (pole_x + self.width + 10, pole_y + 20),
            (pole_x + self.width + 22, pole_y + 25),
            (pole_x + self.width + 10, pole_y + 30),
        ])

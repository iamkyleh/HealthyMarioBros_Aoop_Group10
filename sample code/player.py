# player.py
import pygame

GRAVITY = 0.8
FRICTION = 0.85

def _pressed(keys, code):
    """True if key is down, whether keys is a dict or ScancodeWrapper."""
    try:
        if isinstance(keys, dict):
            return keys.get(code, False)
        return bool(keys[code])
    except Exception:
        return False

class Mario:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.width = 32
        self.height = 32

        self.vel_x = 0.0
        self.vel_y = 0.0
        self.speed = 5.0
        self.jump_power = 15.0
        self.on_ground = False

        # colors for "pixel" rectangles
        self.MARIO_RED = (255, 0, 0)
        self.MARIO_BLUE = (0, 0, 255)
        self.SKIN = (255, 220, 177)

    @property
    def rect(self) -> pygame.Rect:
        """Get the entity's rectangle for collision detection."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def handle_input(self, keys):
        move = 0
        if _pressed(keys, pygame.K_LEFT) or _pressed(keys, pygame.K_a):
            move -= 1
        if _pressed(keys, pygame.K_RIGHT) or _pressed(keys, pygame.K_d):
            move += 1

        # accelerate toward target
        self.vel_x += move * 0.8

        # jump (space / up / W)
        jump_pressed = (
            _pressed(keys, pygame.K_SPACE) or
            _pressed(keys, pygame.K_UP) or
            _pressed(keys, pygame.K_w)
        )
        if jump_pressed and self.on_ground:
            self.vel_y = -self.jump_power
            self.on_ground = False

    def apply_physics(self):
        self.vel_y += GRAVITY
        self.vel_x *= FRICTION
        if abs(self.vel_x) < 0.05:
            self.vel_x = 0.0

    def move_and_collide(self, platforms):
        # horizontal
        self.x += self.vel_x
        r = self.rect
        for p in platforms:
            if r.colliderect(p):
                if self.vel_x > 0:
                    self.x = p.left - self.width
                elif self.vel_x < 0:
                    self.x = p.right
                r = self.rect
                self.vel_x = 0.0

        # vertical
        self.y += self.vel_y
        r = self.rect
        self.on_ground = False
        for p in platforms:
            if r.colliderect(p):
                if self.vel_y > 0:
                    self.y = p.top - self.height
                    self.vel_y = 0.0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.y = p.bottom
                    self.vel_y = 0.0
                r = self.rect

    def update(self, platforms, keys):
        self.handle_input(keys)
        self.apply_physics()
        self.move_and_collide(platforms)

    def draw(self, screen, camera_x):
        x = int(self.x - camera_x)
        y = int(self.y)
        # shirt
        pygame.draw.rect(screen, self.MARIO_RED, (x + 8, y + 12, 16, 12))
        # overalls
        pygame.draw.rect(screen, self.MARIO_BLUE, (x + 6, y + 16, 20, 16))
        # head
        pygame.draw.rect(screen, self.SKIN, (x + 4, y, 24, 16))
        # hat
        pygame.draw.rect(screen, self.MARIO_RED, (x + 2, y - 4, 28, 8))

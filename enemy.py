from entity import Entity
import pygame

class Enemy(Entity):
    def __init__(self, x, y, width=32, height=32):
        super().__init__(x, y, width=width, height=height)
        self.faction = 'E'
        self.vel_x: float = -1
    
    def _ground_ahead(self, platforms, step=6):
        """Return True if there's ground under the leading edge after a small step."""
        probe_x = self.x + (self.width + 1 if self.vel_x > 0 else -1) + (step if self.vel_x > 0 else -step)
        probe_rect = pygame.Rect(int(probe_x), int(self.y + self.height + 1), 2, 2)
        return any(p.colliderect(probe_rect) for p in platforms)

    def wander_horizonal(self, platforms):
        # horizontal patrol
        self.x += self.vel_x
        r = self.rect
        for p in platforms:
            if r.colliderect(p):
                self.x -= self.vel_x
                self.vel_x *= -1
        # edge turn
        if self.on_ground and not self._ground_ahead(platforms):
            self.vel_x *= -1

class Goomba(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y)
    def update(self, platforms):
        if not self.is_alive:
            return
        self.vel_y += 0.8
        self.wander_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
    def stomped(self):
        if not self.is_alive:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.vel_x = 0.0
            self.vel_y = 0.0
    
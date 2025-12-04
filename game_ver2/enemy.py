from numpy.random import random_integers
from entity import Entity
import pygame

class Enemy(Entity):
    def __init__(self, x, y, width=32, height=32, points=200):
        super().__init__(x, y, width=width, height=height)
        self.faction = 'E'
        self.vel_x: float = -1
        self._points: int = points
        self.edgeturn = True
    
    @property
    def points(self) -> int:
        return self._points
    
    @property
    def canDealDamage(self) -> bool:
        return True
    
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
        if self.edgeturn and self.on_ground and not self._ground_ahead(platforms):
            self.vel_x *= -1

class Goomba(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, width=32, height=32, points=400)
    
    def update(self, platforms):
        if not self.is_alive:
            return
        self.vel_y += 0.8
        self.wander_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
        self.direction = 1 if self.vel_x>0 else -1

class KoopaTroopa(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, width=32, height=46, points=500)
    
    def update(self, platforms):
        if not self.is_alive:
            return
        self.vel_y += 0.8
        self.wander_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
        self.direction = 1 if self.vel_x>0 else -1

    def take_damage(self, from_faction) -> bool:
        if not self.is_alive:
            return False
        if self.name == "KoopaTroopa":
            self.name = "KoopaTroopaShell"
            self.edgeturn = False
            self.width = 32
            self.height = 28
            self._points = 0
            self.vel_x = 0
            self.x += 10
            return True
        elif self.name == "KoopaTroopaShell" and from_faction != self.faction:
            if self.vel_x == 0:
                self.vel_x = 5
            else:
                self.vel_x = 0
            return True
        return False
    
    @property
    def canDealDamage(self) -> bool:
        if self.name == "KoopaTroopa":
            return True
        if self.name == "KoopaTroopaShell":
            return self.vel_x
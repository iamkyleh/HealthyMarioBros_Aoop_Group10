# Server-side entity classes (no drawing code)
from math import factorial
from nt import DirEntry
import pygame
from types import SimpleNamespace

GRAVITY = 0.8
FRICTION = 0.85

class Entity:
    def __init__(self, x, y, width=32, height=32, name=None):
        self.name = self.__class__.__name__ if name is None else name
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height
        # Physics properties
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0
        self.on_ground: bool = False
        # Direction (1 for right, -1 for left)
        self.direction: int = 1
        # Faction system, default Neutral
        self.faction: str = 'N'
        # Entity state
        self.lives: int = 1
    
    @property
    def rect(self) -> pygame.Rect:
        """Return pygame.Rect for collision detection"""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def is_alive(self) -> bool:
        return self.lives > 0
    
    @property
    def status(self):
        s = SimpleNamespace(
            faction = self.faction,
            direction = self.direction
        )
        return s
    
    def take_damage(self, his_status) -> bool:
        if not self.is_alive:
            return False
        if his_status.faction != self.faction:
            self.lives -= 1
            self.lives = max(0, self.lives)
            return True
        return False
    
    def move_and_collide_horizonal(self, platforms):
        self.x += self.vel_x
        r = self.rect
        for p in platforms:
            if r.colliderect(p):
                self.x -= self.vel_x
                self.vel_x = 0.0

    def move_and_collide_vertical(self, platforms):
        self.y += self.vel_y
        r = self.rect
        for p in platforms:
            if r.colliderect(p):
                if self.vel_y > 0:
                    self.y = p.top - self.height
                    self.vel_y = 0.0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.y = p.bottom
                    self.vel_y = 0.0


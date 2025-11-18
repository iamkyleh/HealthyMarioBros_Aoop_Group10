import pygame
from abc import ABC, abstractmethod
import addpath

GRAVITY = 0.8
FRICTION = 0.85

class Entity(ABC):
    def __init__(self, x, y, width=32, height=32, name=None):
        self.name = self.__class__.__name__ if name is None else name
        self.image = None
        self.x: float = x
        self.y: float = y
        self.width: int= width
        self.height: int = height
        # Physics properties
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0
        self.on_ground: bool = False
        # Direction (1 for right, -1 for left)
        self.direction: int = 1
        # Faction system, defeult Neutral
        self.faction: str = 'N'
        # Entity state
        self.lives: int = 1
        try:
            self.image = pygame.image.load(addpath.image_path(f"{self.name}.png"))
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except pygame.error:
            self.image = None
    
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def is_alive(self) -> bool:
        return self.lives > 0
    
    def take_damage(self, damage=1):
        self.lives = max(0, self.lives - damage)
    
    @abstractmethod
    def update(self, platforms, keys=None):
        pass

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

    def draw(self, screen, camera_x):
        if self.image:
            screen_x = int(self.x - camera_x)
            screen_y = int(self.y)
            if self.direction == -1:
                flipped_image = pygame.transform.flip(self.image, True, False)
                screen.blit(flipped_image, (screen_x, screen_y))
            else:
                screen.blit(self.image, (screen_x, screen_y))
        else:
            pygame.draw.rect(screen, (255, 0, 0), (int(self.x - camera_x), int(self.y), self.width, self.height))
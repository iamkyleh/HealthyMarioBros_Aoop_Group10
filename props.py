import pygame
import math
import addpath
from abc import abstractmethod

class Props():
    def __init__(self, x, y, width, height):
        self.name = self.__class__.__name__
        self.x: int = x
        self.y: int = y
        self.width: int = width
        self.height: int = height
        self.image = pygame.image.load(addpath.image_path(f"{self.name}.png"))
    
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
    
    @abstractmethod
    def draw(self, screen, camera_x):
        pass

class Coin(Props):
    def __init__(self, x, y):
        super().__init__(x, y, width=20, height=28)
        self.rotation = 0.0
        self.collected = False

    def update(self):
        if not self.collected:
            self.rotation += 0.2

    def draw(self, screen, camera_x):
        if self.collected:
            return

        # spin illusion using sine scaling on X-axis
        scale = abs(math.sin(self.rotation))
        scaled_w = max(2, int(self.width * scale))  # never go to 0 width
        scaled_image = pygame.transform.scale(self.image, (scaled_w, self.height))

        # center it where the coin’s middle should be
        x = int(self.x - camera_x) + (self.width - scaled_w) // 2
        y = int(self.y)

        screen.blit(scaled_image, (x, y))
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

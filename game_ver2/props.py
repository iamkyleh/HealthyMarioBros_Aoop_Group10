# Server-side props (no drawing code)
import math
import pygame

class Props:
    def __init__(self, x, y, width, height):
        self.name = self.__class__.__name__
        self.x: int = x
        self.y: int = y
        self.width: int = width
        self.height: int = height
    
    @property
    def rect(self) -> pygame.Rect:
        """Return pygame.Rect for collision detection"""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

class Coin(Props):
    def __init__(self, x, y):
        super().__init__(x, y, width=20, height=28)
        self.rotation = 0.0
        self.collected = False

    def update(self):
        if not self.collected:
            self.rotation += 0.2

class Flag(Props):
    def __init__(self, x, y):
        super().__init__(x, y, width=48, height=144)
        self.owner_name = ""

    def update(self, player_name):
        self.owner_name = player_name

class Flag_final(Props):
    def __init__(self, x, y, width=48, height=256):
        super().__init__(x, y, width=width, height=height)
        self.owner_name = ""

    def update(self, player_name):
        self.owner_name = player_name


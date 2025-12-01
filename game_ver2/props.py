# Server-side props (no drawing code)
import math

class Props:
    def __init__(self, x, y, width, height):
        self.name = self.__class__.__name__
        self.x: int = x
        self.y: int = y
        self.width: int = width
        self.height: int = height
    
    @property
    def rect(self):
        """Return a dict representation of rect for collision detection"""
        return {
            "x": int(self.x),
            "y": int(self.y),
            "width": self.width,
            "height": self.height
        }
    
    def get_rect_pygame_style(self):
        """Helper to create a rect-like object for collision"""
        class Rect:
            def __init__(self, x, y, w, h):
                self.left = x
                self.top = y
                self.right = x + w
                self.bottom = y + h
            def colliderect(self, other):
                return not (self.right <= other.left or 
                           self.left >= other.right or
                           self.bottom <= other.top or
                           self.top >= other.bottom)
        return Rect(int(self.x), int(self.y), self.width, self.height)

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
        self.checkpoint_touched = False
        self.touched_by = None  # player name who touched it

    @property
    def is_checkpoint(self):
        return self.checkpoint_touched

    def update(self, player_name):
        self.checkpoint_touched = True
        self.touched_by = player_name

class Flag_final(Props):
    def __init__(self, x, y, width=48, height=256):
        super().__init__(x, y, width=width, height=height)
        self.checkpoint_touched = False
        self.touched_by = None  # player name who touched it

    @property
    def is_checkpoint(self):
        return self.checkpoint_touched

    def update(self, player_name):
        self.checkpoint_touched = True
        self.touched_by = player_name


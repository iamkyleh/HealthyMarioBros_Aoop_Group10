# Server-side entity classes (no drawing code)
GRAVITY = 0.8
FRICTION = 0.85

class Entity:
    def __init__(self, x, y, width=32, height=32, name=None):
        self.name = self.__class__.__name__ if name is None else name
        self.x: float = x
        self.y: float = y
        self.width: int = width
        self.height: int = height
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
                self.width = w
                self.height = h
            def colliderect(self, other):
                return not (self.right <= other.left or 
                           self.left >= other.right or
                           self.bottom <= other.top or
                           self.top >= other.bottom)
        return Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def is_alive(self) -> bool:
        return self.lives > 0
    
    def take_damage(self, from_faction) -> bool:
        if not self.is_alive:
            return False
        if from_faction != self.faction:
            self.lives -= 1
            self.lives = max(0, self.lives)
            return True
        return False
    
    def move_and_collide_horizonal(self, platforms):
        self.x += self.vel_x
        r = self.get_rect_pygame_style()
        for p in platforms:
            if r.colliderect(p):
                self.x -= self.vel_x
                self.vel_x = 0.0

    def move_and_collide_vertical(self, platforms):
        self.y += self.vel_y
        r = self.get_rect_pygame_style()
        for p in platforms:
            if r.colliderect(p):
                if self.vel_y > 0:
                    self.y = p.top - self.height
                    self.vel_y = 0.0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.y = p.bottom
                    self.vel_y = 0.0


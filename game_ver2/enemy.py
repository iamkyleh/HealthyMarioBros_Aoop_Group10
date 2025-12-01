from entity import Entity

class Enemy(Entity):
    def __init__(self, x, y, width=32, height=32, points=200):
        super().__init__(x, y, width=width, height=height)
        self.faction = 'E'
        self.vel_x: float = -1
        self._points: int = points
    
    @property
    def points(self) -> int:
        return self._points
    
    def _ground_ahead(self, platforms, step=6):
        """Return True if there's ground under the leading edge after a small step."""
        probe_x = self.x + (self.width + 1 if self.vel_x > 0 else -1) + (step if self.vel_x > 0 else -step)
        # Create a simple rect-like object for probing
        class ProbeRect:
            def __init__(self, x, y, w, h):
                self.left = x
                self.top = y
                self.right = x + w
                self.bottom = y + h
        probe_rect = ProbeRect(int(probe_x), int(self.y + self.height + 1), 2, 2)
        for p in platforms:
            if not (probe_rect.right <= p.left or 
                   probe_rect.left >= p.right or
                   probe_rect.bottom <= p.top or
                   probe_rect.top >= p.bottom):
                return True
        return False

    def wander_horizonal(self, platforms):
        # horizontal patrol
        self.x += self.vel_x
        r = self.get_rect_pygame_style()
        for p in platforms:
            if r.colliderect(p):
                self.x -= self.vel_x
                self.vel_x *= -1
        # edge turn
        if self.on_ground and not self._ground_ahead(platforms):
            self.vel_x *= -1

class Goomba(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, points=2000)
    
    def update(self, platforms):
        if not self.is_alive:
            return
        self.vel_y += 0.8
        self.wander_horizonal(platforms)
        self.move_and_collide_vertical(platforms)


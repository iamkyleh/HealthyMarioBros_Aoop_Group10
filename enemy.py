from entity import Entity

class Enemy(Entity):
    def __init__(self, x, y, width=32, height=32):
        super().__init__(x, y, width=width, height=height)
        self.faction = 'E'
        self.vel_x: float = -1
    def wander_horizonal(self):
        pass

class Goomba(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y)
    def update(self, platforms):
        if not self.is_alive:
            return
        self.wander_horizonal()
        self.move_and_collide_vertical(platforms)
    def stomped(self):
        if not self.is_alive:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.vel_x = 0.0
            self.vel_y = 0.0
    
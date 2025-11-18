from entity import Entity

class Player(Entity):
    def __init__(self, name, x, y):
        super().__init__(x, y, width=24, height=32, name=name)
        self.faction = 'P'
        self.lives: int = 3
        self.speed: float = 5.0
        self.jump_strength: float = 15.0

    def reborn(self):
        self.lives -= 1
        self.x, self.y = 80, 400
        self.vel_x = self.vel_y = 0.0

    def actuate(self, keys):
        pass

    def update(self, platforms, keys=None):
        self.actuate(keys)
        self.move_and_collide_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
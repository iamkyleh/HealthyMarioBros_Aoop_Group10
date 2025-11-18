from entity import Entity

class Enemy(Entity):
    def __init__(self, x, y, width=32, height=32):
        super().__init__(x, y, width=width, height=height)
        self.faction = 'E'
        self.vel_x: float = -1
    def patrol(self):
        pass
    
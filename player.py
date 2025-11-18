from entity import Entity, GRAVITY, FRICTION
from input import input

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
        move_x, jump_pressed, attack_pressed = input(keys)
        self.vel_x += move_x * 0.8
        self.vel_x =  max(-self.speed, min(self.speed, self.vel_x))
        if move_x != 0:
            self.direction = move_x
        if jump_pressed and self.on_ground:
            self.vel_y = -self.jump_strength
            self.on_ground = False
        #apply physics
        self.vel_y += GRAVITY
        self.vel_x *= FRICTION
        if abs(self.vel_x) < 0.05:
            self.vel_x = 0.0

    def update(self, platforms, keys=None):
        self.actuate(keys)
        self.move_and_collide_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
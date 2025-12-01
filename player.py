from entity import Entity, GRAVITY, FRICTION
from input import input

class Player(Entity):
    def __init__(self, name, rebornpoint, keyboard):
        super().__init__(rebornpoint[0], rebornpoint[1], width=24, height=32, name=name)
        self.faction = 'P'
        self.lives: int = 3
        self.speed: float = 5.0
        self.jump_strength: float = 15.0
        self.keyboard = keyboard
    
    def take_damage(self, from_faction, respawn_point):
        if super().take_damage(from_faction):
            self.x, self.y = respawn_point  # respawn position

    def actuate(self, keys):
        move_x, jump_pressed = input(keys, self.keyboard)
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
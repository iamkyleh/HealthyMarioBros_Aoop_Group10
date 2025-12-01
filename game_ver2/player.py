from entity import Entity, GRAVITY, FRICTION

class Player(Entity):
    def __init__(self, name, rebornpoint):
        super().__init__(rebornpoint[0], rebornpoint[1], width=24, height=32, name=name)
        self.faction = 'P'
        self.lives: int = 3
        self.speed: float = 5.0
        self.jump_strength: float = 15.0
    
    def take_damage(self, from_faction, respawn_point):
        if super().take_damage(from_faction):
            self.x, self.y = respawn_point  # respawn position

    def actuate(self, inp):
        """Process input: move_x is -1, 0, or 1; jump_pressed is bool"""
        self.vel_x += inp["move"] * 0.8
        self.vel_x = max(-self.speed, min(self.speed, self.vel_x))
        if inp["move"] != 0:
            self.direction = inp["move"]
        if inp["jump"] and self.on_ground:
            self.vel_y = -self.jump_strength
            self.on_ground = False
        # apply physics
        self.vel_y += GRAVITY
        self.vel_x *= FRICTION
        if abs(self.vel_x) < 0.05:
            self.vel_x = 0.0

    def update(self, platforms, inp):
        self.actuate(inp)
        self.move_and_collide_horizonal(platforms)
        self.move_and_collide_vertical(platforms)
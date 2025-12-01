# mario_sprite.py
import pygame

class Mario(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Mario block size
        self.width = 40
        self.height = 50

        # Create a basic block (Surface)
        self.image = pygame.Surface((self.width, self.height))
        self.color_idle = (255, 180, 0)   # orange/yellow block
        self.color_walk = (255, 140, 0)   # darker while walking
        self.color_jump = (255, 100, 0)   # darker while jumping

        self.image.fill(self.color_idle)
        self.rect = self.image.get_rect(topleft=(x, y))

        # Physics
        self.vel_x = 0
        self.vel_y = 0
        self.gravity = 0.6
        self.on_ground = True

        # Walk animation timer
        self.anim_timer = 0

    def apply_input(self, move_left, move_right, jump):
        speed = 4

        if move_left:
            self.vel_x = -speed
        elif move_right:
            self.vel_x = speed
        else:
            self.vel_x = 0

        if jump and self.on_ground:
            self.vel_y = -12
            self.on_ground = False

    def update(self):
        # Apply gravity
        self.vel_y += self.gravity

        # Move
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        # Ground collision
        ground_y = 400
        if self.rect.bottom >= ground_y:
            self.rect.bottom = ground_y
            self.vel_y = 0
            self.on_ground = True

        # === Block Animation ===
        if not self.on_ground:
            # Jumping color
            self.image.fill(self.color_jump)

        elif self.vel_x != 0:
            # Walking: alternate color like "animation"
            self.anim_timer += 1
            if (self.anim_timer // 10) % 2 == 0:
                self.image.fill(self.color_walk)
            else:
                self.image.fill(self.color_idle)
        else:
            # Idle
            self.image.fill(self.color_idle)

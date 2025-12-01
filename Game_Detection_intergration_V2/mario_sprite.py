# mario_sprite.py
import pygame

class Mario(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.images = {
            "idle": pygame.image.load("sprites/idle.png"),
            "walk1": pygame.image.load("sprites/walk1.png"),
            "walk2": pygame.image.load("sprites/walk2.png"),
            "jump": pygame.image.load("sprites/jump.png"),
        }

        self.image = self.images["idle"]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.vel_x = 0
        self.vel_y = 0
        self.gravity = 0.6
        self.on_ground = True
        self.anim_timer = 0

    def apply_input(self, move_left, move_right, jump):
        speed = 4

        # horizontal movement
        if move_left:
            self.vel_x = -speed
        elif move_right:
            self.vel_x = speed
        else:
            self.vel_x = 0

        # jump
        if jump and self.on_ground:
            self.vel_y = -12
            self.on_ground = False

    def update(self):
        # apply gravity
        self.vel_y += self.gravity

        # update position
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        # ground collision (simple)
        if self.rect.bottom >= 400:
            self.rect.bottom = 400
            self.vel_y = 0
            self.on_ground = True

        # animation
        if not self.on_ground:
            self.image = self.images["jump"]
        elif self.vel_x != 0:
            self.anim_timer += 1
            if (self.anim_timer // 10) % 2 == 0:
                self.image = self.images["walk1"]
            else:
                self.image = self.images["walk2"]
        else:
            self.image = self.images["idle"]

# mario_game.py
import pygame

class MarioGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption("Mario Game")

        self.mario_x = 100
        self.mario_y = 300
        self.vy = 0
        self.gravity = 0.6
        self.jump_force = -12
        self.ground_y = 300

        self.clock = pygame.time.Clock()
        self.running = True
        self.pending_jump = False

    def apply_jump(self):
        self.pending_jump = True

    def game_loop_step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        if self.pending_jump and self.mario_y == self.ground_y:
            self.vy = self.jump_force
            self.pending_jump = False

        self.vy += self.gravity
        self.mario_y += self.vy

        if self.mario_y >= self.ground_y:
            self.mario_y = self.ground_y
            self.vy = 0

        self.screen.fill((135, 206, 235))
        pygame.draw.rect(self.screen, (255, 0, 0),
                         (self.mario_x, int(self.mario_y), 40, 40))

        pygame.display.update()
        self.clock.tick(60)

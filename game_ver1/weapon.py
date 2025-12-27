from abc import ABC, abstractmethod
import pygame
import time
from entity import Entity, GRAVITY

class Weapon(ABC):
    def __init__(self, owner=None):
        self.cooldown = 0.5
        self.last_attack_time = 0.0
        self.owner = owner
    
    def can_attack(self):
        """Check if enough time has passed since last attack"""
        current_time = time.time()
        return current_time >= self.last_attack_time + self.cooldown
    
    def update_attack_time(self):
        """Update the last attack time to current time"""
        self.last_attack_time = time.time()
    
    def attack(self):
        if self.can_attack():
            self.update_attack_time()
            self.attak_effects()

    @abstractmethod
    def attak_effects(self):
        pass

    @abstractmethod
    def get_visual_effects(self):
        """Return list of visual effects to be rendered"""
        return []

class FireBall(Weapon):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self.projectiles = []

    def attack(self):
        if not self.can_attack():
            return []

        self.update_attack_time()

        # fireball origin slightly in front of the player
        fb_x = self.owner.x + (self.owner.width // 2) + self.owner.direction * 12
        fb_y = self.owner.y + self.owner.height // 3

        fb = Fireball_projectile(fb_x, fb_y, self.owner.direction, self.owner.faction)
        self.projectiles.append(fb)
        return [fb]

    def attak_effects(self):
        pass  # unused for now

    def get_visual_effects(self):
        return self.projectiles


class Fireball_projectile(Entity):
    def __init__(self, x, y, direction, faction):
        super().__init__(x, y, width=8, height=8, name="FireBall")
        self.direction = direction
        self.faction = faction
        self.speed = 8 * direction
        self.spawn_time = time.time()
        self.life_time = 3.0   # disappear after 3 sec
        self.vel_y = -2.0
        self.damage = 1

    def update(self, platforms, entities):
        # --- lifetime ---
        if time.time() - self.spawn_time >= self.life_time:
            self.lives = 0
            return

        # --- movement ---
        self.x += self.speed
        self.vel_y += GRAVITY * 0.3
        self.y += self.vel_y

        # --- platform collision: vanish instantly ---
        my_rect = self.rect
        for p in platforms:
            if my_rect.colliderect(p):
                self.lives = 0
                return

        # --- hit any entity of different faction ---
        for e in entities:
            if e is self: 
                continue
            if not e.is_alive:
                continue
            if e.faction != self.faction and my_rect.colliderect(e.rect):
                e.take_damage(self.faction)
                self.lives = 0
                return
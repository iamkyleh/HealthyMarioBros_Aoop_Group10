import time
import pygame
from entity import Entity, GRAVITY

class FireballProjectile(Entity):
    """Fireball projectile that can damage entities of different factions"""
    def __init__(self, x, y, direction, faction):
        super().__init__(x, y, width=8, height=8, name="Fireball")
        self.direction = direction
        self.faction = faction
        self.speed = 8 * direction
        self.spawn_time = time.time()
        self.life_time = 3.0  # disappear after 3 sec
        self.vel_y = -2.0
        self.damage = 1
    
    def update(self, platforms, entities):
        """Update fireball position and check collisions"""
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
                # Create a status object for damage dealing
                from types import SimpleNamespace
                fireball_status = SimpleNamespace(faction=self.faction, direction=self.direction)
                e.take_damage(fireball_status)
                self.lives = 0
                return

class FireFlower:
    """FireFlower weapon that can shoot fireballs"""
    def __init__(self, owner=None):
        self.cooldown = 0.5
        self.last_attack_time = 0.0
        self.owner = owner
        self.projectiles = []  # Store active fireballs
    
    def can_attack(self):
        """Check if enough time has passed since last attack"""
        current_time = time.time()
        return current_time >= self.last_attack_time + self.cooldown
    
    def update_attack_time(self):
        """Update the last attack time to current time"""
        self.last_attack_time = time.time()
    
    def attack(self):
        """Create a fireball if cooldown allows"""
        if not self.can_attack():
            return None
        
        self.update_attack_time()
        
        # Fireball origin slightly in front of the player
        fb_x = self.owner.x + (self.owner.width // 2) + self.owner.direction * 12
        fb_y = self.owner.y + self.owner.height // 3
        
        fb = FireballProjectile(fb_x, fb_y, self.owner.direction, self.owner.faction)
        self.projectiles.append(fb)
        return fb
    
    def update_projectiles(self, platforms, entities):
        """Update all active fireballs and remove dead ones"""
        for fb in self.projectiles[:]:  # Use slice to avoid modification during iteration
            if fb.is_alive:
                fb.update(platforms, entities)
            if not fb.is_alive:
                self.projectiles.remove(fb)
    
    def get_active_projectiles(self):
        """Get list of active fireball projectiles"""
        return [fb for fb in self.projectiles if fb.is_alive]


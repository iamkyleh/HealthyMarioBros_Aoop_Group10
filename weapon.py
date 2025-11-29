from abc import ABC, abstractmethod
import pygame
import time

class WEAPONS(ABC):
    def __init__(self):
        self.cooldown = 0.5
        self.last_attack_time = 0.0
    
    def can_attack(self):
        """Check if enough time has passed since last attack"""
        current_time = time.time()
        return current_time >= self.last_attack_time + self.cooldown
    
    def update_attack_time(self):
        """Update the last attack time to current time"""
        self.last_attack_time = time.time()
    
    def attack(self):
        if self.can_attack():
            self.update_attack_time(self)
            self.attak_effects()

    @abstractmethod
    def attak_effects(self):
        pass
    
    @abstractmethod
    def get_visual_effects(self):
        """Return list of visual effects to be rendered"""
        return []
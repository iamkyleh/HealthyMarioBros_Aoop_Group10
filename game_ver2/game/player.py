from .entity import Entity, GRAVITY, FRICTION
import time

class Player(Entity):
    def __init__(self, name, rebornpoint, width=24, height=32):
        super().__init__(rebornpoint[0], rebornpoint[1], width=width, height=height, name=name)
        self.faction = 'P'
        self.lives: int = 3
        self.speed: float = 3.5
        self.jump_strength: float = 15.0
        # Invincibility after respawn
        self.invincible = False
        self.invincible_start_time = 0
        self.invincible_duration = 2.0  # 2 seconds of invincibility after respawn
    
    @property
    def is_invincible(self):
        """Check if player is currently invincible"""
        if self.invincible:
            if time.time() - self.invincible_start_time >= self.invincible_duration:
                self.invincible = False
                return False
            return True
        return False
    
    def start_invincibility(self):
        """Start invincibility period"""
        self.invincible = True
        self.invincible_start_time = time.time()
    
    def take_damage(self, his_status=None, respawn_point=None, from_faction=None):
        """Handle damage - can be called with his_status (SimpleNamespace) or from_faction (str)"""
        # Can't take damage while invincible
        if self.is_invincible:
            return False
        
        if from_faction:
            # Legacy format - create a status object
            from types import SimpleNamespace
            his_status = SimpleNamespace(faction=from_faction, direction=1)
        if his_status and super().take_damage(his_status):
            if respawn_point:
                self.x, self.y = respawn_point  # respawn position
                self.vel_x = 0
                self.vel_y = 0
            # Start invincibility after taking damage
            self.start_invincibility()
            return True
        return False

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

    def handle_player_collision(self, other_player, respawn_point):
        """
        Handle collision with another player.
        If different factions, deal damage. Otherwise, push apart.
        Returns True if damage was dealt.
        """
        if not self.is_alive or not other_player.is_alive:
            return False
        
        mrect = self.rect
        orect = other_player.rect
        
        if not mrect.colliderect(orect):
            return False
        
        # Check if different factions - battle mode
        if self.faction != other_player.faction:
            # Different factions - deal damage based on collision direction
            if self.vel_y > 0 and (mrect.bottom - orect.top) < 20:
                # This player landing on other player - damage other player
                other_player.take_damage(from_faction=self.faction, respawn_point=respawn_point)
                self.vel_y = -8
                self.y = orect.top - self.height
                return True
            elif self.vel_y < 0 and (orect.bottom - mrect.top) < 20:
                # Other player landing on this player - damage this player
                self.take_damage(from_faction=other_player.faction, respawn_point=respawn_point)
                self.vel_y = 2
                self.y = orect.bottom
                return True
            else:
                # Horizontal collision - both take damage
                self.take_damage(from_faction=other_player.faction, respawn_point=respawn_point)
                other_player.take_damage(from_faction=self.faction, respawn_point=respawn_point)
                return True
        else:
            # Same faction - just push apart (no damage)
            # Vertical collision handling
            if self.vel_y > 0 and (mrect.bottom - orect.top) < 20:
                # Player landing on another player - bounce slightly
                self.vel_y = -8
                self.y = orect.top - self.height
            elif self.vel_y < 0 and (orect.bottom - mrect.top) < 20:
                # Player hitting another player from below - bounce down
                self.vel_y = 2
                self.y = orect.bottom
            # Horizontal push-back (only if not already handled by vertical)
            elif abs(self.vel_x) > 0:
                if self.x < other_player.x:
                    # Push player to the left
                    self.x = orect.left - self.width
                    self.vel_x = 0
                else:
                    # Push player to the right
                    self.x = orect.right
                    self.vel_x = 0
            return False

    def update(self, platforms, inp):
        self.actuate(inp)
        self.move_and_collide_horizonal(platforms)
        self.move_and_collide_vertical(platforms)

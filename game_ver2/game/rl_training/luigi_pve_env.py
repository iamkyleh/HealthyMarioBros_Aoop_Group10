"""
Custom Gym environment for training Luigi AI to fight against Mario in PVE mode.
Luigi (AI) vs Mario (simulated opponent during training, human during gameplay).
"""
import sys
import os
import numpy as np
import gymnasium as gym
from gymnasium import spaces

# Add parent paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from game.player import Player
from game.weapon import FireFlower


class SimplePlatformEnv:
    """Simple platform environment for training without full game overhead."""
    def __init__(self):
        import pygame
        pygame.init()
        # Arena platforms matching PVE1.json
        self.platforms = [
            pygame.Rect(0, 500, 800, 100),     # Ground
            pygame.Rect(100, 400, 150, 20),    # Left platform
            pygame.Rect(350, 350, 100, 20),    # Middle platform
            pygame.Rect(550, 400, 150, 20),    # Right platform
            pygame.Rect(200, 250, 100, 20),    # Upper left
            pygame.Rect(500, 250, 100, 20),    # Upper right
            pygame.Rect(350, 150, 100, 20),    # Top middle
        ]
        self.respawn_point_luigi = (600, 400)
        self.respawn_point_mario = (200, 400)


class LuigiPVEEnv(gym.Env):
    """
    Custom Gym environment for RL Luigi vs Mario.
    
    Luigi (agent) learns to:
    - Chase and attack Mario
    - Dodge Mario's attacks
    - Use platforms strategically
    - Win by reducing Mario's lives to 0
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}
    
    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        
        # Initialize simple platform environment
        self.arena = SimplePlatformEnv()
        
        # Action space: Discrete actions
        # 0: idle, 1: move_left, 2: move_right, 3: jump, 4: attack
        # 5: move_left+jump, 6: move_right+jump, 7: move_left+attack, 8: move_right+attack
        self.action_space = spaces.Discrete(9)
        
        # Observation space: normalized values
        # [luigi_x, luigi_y, luigi_vel_x, luigi_vel_y, luigi_lives, luigi_on_ground,
        #  mario_x, mario_y, mario_vel_x, mario_vel_y, mario_lives, mario_on_ground,
        #  distance_x, distance_y, relative_vel_x, relative_vel_y]
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(16,),
            dtype=np.float32
        )
        
        # Game constants
        self.max_x = 800
        self.max_y = 600
        self.max_vel = 20
        self.max_lives = 3
        
        # Episode settings
        self.max_steps = 3000  # Max steps per episode
        self.current_step = 0
        
        # Initialize players
        self.luigi = None
        self.mario = None
        self.mario_ai_policy = "aggressive"  # Training opponent behavior
        
        self.reset()
    
    def _create_players(self):
        """Create fresh player instances."""
        # Luigi spawns on right side
        self.luigi = Player("Luigi", self.arena.respawn_point_luigi)
        self.luigi.faction = "E"
        self.luigi.weapon = FireFlower(owner=self.luigi)
        self.luigi.lives = 3
        
        # Mario spawns on left side
        self.mario = Player("Mario", self.arena.respawn_point_mario)
        self.mario.faction = "P"
        self.mario.weapon = FireFlower(owner=self.mario)
        self.mario.lives = 3
    
    def _get_observation(self):
        """Get normalized observation vector."""
        # Normalize positions to [-1, 1]
        luigi_x = (self.luigi.x / self.max_x) * 2 - 1
        luigi_y = (self.luigi.y / self.max_y) * 2 - 1
        luigi_vel_x = np.clip(self.luigi.vel_x / self.max_vel, -1, 1)
        luigi_vel_y = np.clip(self.luigi.vel_y / self.max_vel, -1, 1)
        luigi_lives = self.luigi.lives / self.max_lives
        luigi_on_ground = 1.0 if self.luigi.on_ground else 0.0
        
        mario_x = (self.mario.x / self.max_x) * 2 - 1
        mario_y = (self.mario.y / self.max_y) * 2 - 1
        mario_vel_x = np.clip(self.mario.vel_x / self.max_vel, -1, 1)
        mario_vel_y = np.clip(self.mario.vel_y / self.max_vel, -1, 1)
        mario_lives = self.mario.lives / self.max_lives
        mario_on_ground = 1.0 if self.mario.on_ground else 0.0
        
        # Relative position and velocity
        distance_x = (self.mario.x - self.luigi.x) / self.max_x
        distance_y = (self.mario.y - self.luigi.y) / self.max_y
        relative_vel_x = np.clip((self.mario.vel_x - self.luigi.vel_x) / self.max_vel, -1, 1)
        relative_vel_y = np.clip((self.mario.vel_y - self.luigi.vel_y) / self.max_vel, -1, 1)
        
        return np.array([
            luigi_x, luigi_y, luigi_vel_x, luigi_vel_y, luigi_lives, luigi_on_ground,
            mario_x, mario_y, mario_vel_x, mario_vel_y, mario_lives, mario_on_ground,
            distance_x, distance_y, relative_vel_x, relative_vel_y
        ], dtype=np.float32)
    
    def _action_to_input(self, action):
        """Convert discrete action to game input dict."""
        actions_map = {
            0: {"move": 0, "jump": False, "attack": False},   # idle
            1: {"move": -1, "jump": False, "attack": False},  # left
            2: {"move": 1, "jump": False, "attack": False},   # right
            3: {"move": 0, "jump": True, "attack": False},    # jump
            4: {"move": 0, "jump": False, "attack": True},    # attack
            5: {"move": -1, "jump": True, "attack": False},   # left + jump
            6: {"move": 1, "jump": True, "attack": False},    # right + jump
            7: {"move": -1, "jump": False, "attack": True},   # left + attack
            8: {"move": 1, "jump": False, "attack": True},    # right + attack
        }
        return actions_map.get(action, actions_map[0])
    
    def _get_mario_action(self):
        """Get Mario's action based on AI policy (training opponent)."""
        dx = self.luigi.x - self.mario.x
        dy = self.luigi.y - self.mario.y
        distance = np.sqrt(dx**2 + dy**2)
        
        if self.mario_ai_policy == "aggressive":
            # Move toward Luigi and attack when close
            move = 1 if dx > 20 else (-1 if dx < -20 else 0)
            jump = dy < -50 and self.mario.on_ground and np.random.random() < 0.3
            attack = distance < 100 and np.random.random() < 0.2
        elif self.mario_ai_policy == "defensive":
            # Keep distance and attack occasionally
            move = -1 if dx > 0 else 1
            jump = self.mario.on_ground and np.random.random() < 0.1
            attack = distance < 150 and np.random.random() < 0.1
        else:  # random
            move = np.random.choice([-1, 0, 1])
            jump = np.random.random() < 0.1 and self.mario.on_ground
            attack = np.random.random() < 0.05
        
        return {"move": move, "jump": jump, "attack": attack}
    
    def _handle_combat(self):
        """Handle combat between Luigi and Mario."""
        damage_dealt = 0
        damage_taken = 0
        
        luigi_rect = self.luigi.rect
        mario_rect = self.mario.rect
        
        if luigi_rect.colliderect(mario_rect):
            # Luigi landing on Mario
            if self.luigi.vel_y > 0 and (luigi_rect.bottom - mario_rect.top) < 20:
                self.mario.lives -= 1
                self.luigi.vel_y = -10
                self.luigi.y = mario_rect.top - self.luigi.height
                damage_dealt = 1
            # Mario landing on Luigi
            elif self.mario.vel_y > 0 and (mario_rect.bottom - luigi_rect.top) < 20:
                self.luigi.lives -= 1
                self.mario.vel_y = -10
                damage_taken = 1
            # Horizontal collision - both take damage
            elif abs(self.luigi.vel_x) > 1 or abs(self.mario.vel_x) > 1:
                if np.random.random() < 0.3:  # 30% chance of damage on collision
                    self.luigi.lives -= 1
                    self.mario.lives -= 1
                    damage_dealt = 0.5
                    damage_taken = 0.5
        
        return damage_dealt, damage_taken
    
    def step(self, action):
        """Execute one step in the environment."""
        self.current_step += 1
        
        # Store previous state for reward calculation
        prev_luigi_lives = self.luigi.lives
        prev_mario_lives = self.mario.lives
        prev_distance = np.sqrt((self.mario.x - self.luigi.x)**2 + (self.mario.y - self.luigi.y)**2)
        
        # Execute Luigi's action
        luigi_input = self._action_to_input(action)
        self.luigi.update(self.arena.platforms, luigi_input)
        
        # Execute Mario's AI action
        mario_input = self._get_mario_action()
        self.mario.update(self.arena.platforms, mario_input)
        
        # Handle combat
        damage_dealt, damage_taken = self._handle_combat()
        
        # Keep players in bounds
        self.luigi.x = np.clip(self.luigi.x, 0, self.max_x - self.luigi.width)
        self.mario.x = np.clip(self.mario.x, 0, self.max_x - self.mario.width)
        
        # Respawn if fell off world
        if self.luigi.y > 700:
            self.luigi.lives -= 1
            self.luigi.x, self.luigi.y = self.arena.respawn_point_luigi
            self.luigi.vel_x, self.luigi.vel_y = 0, 0
            damage_taken += 1
        if self.mario.y > 700:
            self.mario.lives -= 1
            self.mario.x, self.mario.y = self.arena.respawn_point_mario
            self.mario.vel_x, self.mario.vel_y = 0, 0
            damage_dealt += 1
        
        # Calculate reward
        reward = 0.0
        
        # Reward for dealing damage to Mario
        reward += (prev_mario_lives - self.mario.lives) * 50.0
        
        # Penalty for taking damage
        reward -= (prev_luigi_lives - self.luigi.lives) * 50.0
        
        # Small reward for getting closer to Mario (encourages engagement)
        current_distance = np.sqrt((self.mario.x - self.luigi.x)**2 + (self.mario.y - self.luigi.y)**2)
        distance_reward = (prev_distance - current_distance) * 0.01
        reward += distance_reward
        
        # Small penalty for being idle
        if action == 0:
            reward -= 0.1
        
        # Bonus for winning
        if self.mario.lives <= 0:
            reward += 100.0
        
        # Penalty for losing
        if self.luigi.lives <= 0:
            reward -= 100.0
        
        # Check termination
        terminated = self.luigi.lives <= 0 or self.mario.lives <= 0
        truncated = self.current_step >= self.max_steps
        
        observation = self._get_observation()
        info = {
            "luigi_lives": self.luigi.lives,
            "mario_lives": self.mario.lives,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
        }
        
        return observation, reward, terminated, truncated, info
    
    def reset(self, seed=None, options=None):
        """Reset the environment."""
        super().reset(seed=seed)
        
        self._create_players()
        self.current_step = 0
        
        # Randomize Mario's AI policy for variety
        self.mario_ai_policy = np.random.choice(["aggressive", "defensive", "random"])
        
        observation = self._get_observation()
        info = {}
        
        return observation, info
    
    def render(self):
        """Render the environment (optional)."""
        if self.render_mode == "human":
            print(f"Step {self.current_step}: Luigi({self.luigi.x:.0f},{self.luigi.y:.0f}) lives={self.luigi.lives} | "
                  f"Mario({self.mario.x:.0f},{self.mario.y:.0f}) lives={self.mario.lives}")
    
    def close(self):
        """Clean up."""
        pass


# Register the environment
gym.register(
    id="LuigiPVE-v0",
    entry_point="luigi_pve_env:LuigiPVEEnv",
)

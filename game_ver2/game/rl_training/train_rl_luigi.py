"""
Train an RL agent (Luigi) to fight against a human-controlled Mario using Stable Baselines3.
All game logic is in game_core.py.
"""
import sys
import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import gymnasium as gym

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from game.game_core import GAME
from game.player import Player

class MarioVsLuigiEnv(gym.Env):
    """Custom Gym environment for RL Luigi vs Human Mario."""
    def __init__(self):
        super().__init__()
        self.game = GAME(filename="pvp_arena", pvp_mode=True)
        self.luigi = Player("Luigi", (600, 400))
        self.mario = Player("Mario", (100, 400))
        self.game.players = [self.mario, self.luigi]
        # Action: [move_left, move_right, jump, attack]
        self.action_space = gym.spaces.MultiDiscrete([2, 2, 2, 2])
        # Observation: [luigi_x, luigi_y, luigi_lives, mario_x, mario_y, mario_lives, dx, dy]
        self.observation_space = gym.spaces.Box(
            low=np.array([0, 0, 0, 0, 0, 0, -800, -600]),
            high=np.array([800, 600, 3, 800, 600, 3, 800, 600]),
            dtype=np.float32
        )
        self.reset()

    def reset(self, seed=None, options=None):
        self.game = GAME(filename="pvp_arena", pvp_mode=True)
        self.luigi = Player("Luigi", (600, 400))
        self.mario = Player("Mario", (100, 400))
        self.game.players = [self.mario, self.luigi]
        return self._get_obs(), {}

    def _get_obs(self):
        dx = self.mario.x - self.luigi.x
        dy = self.mario.y - self.luigi.y
        return np.array([
            self.luigi.x, self.luigi.y, self.luigi.lives,
            self.mario.x, self.mario.y, self.mario.lives,
            dx, dy
        ], dtype=np.float32)

    def step(self, action):
        move_left, move_right, jump, attack = action
        move_dir = 0
        if move_right and not move_left:
            move_dir = 1
        elif move_left and not move_right:
            move_dir = -1
        luigi_input = {"move": move_dir, "jump": bool(jump), "attack": bool(attack)}
        # Mario is controlled by a simple script or can be replaced by human input in the future
        mario_input = {"move": 0, "jump": False, "attack": False}
        self.luigi.update(self.game.platforms, luigi_input)
        self.mario.update(self.game.platforms, mario_input)
        self.game.update_camera()
        # Reward: +10 for damaging Mario, -10 for Luigi damage, +0.1 for getting closer
        reward = 0
        if self.mario.lives < 3:
            reward += 10
        if self.luigi.lives < 3:
            reward -= 10
        dx = abs(self.mario.x - self.luigi.x)
        reward += 0.1 * (800 - dx) / 800
        done = self.luigi.lives <= 0 or self.mario.lives <= 0
        return self._get_obs(), reward, done, False, {}

if __name__ == "__main__":
    env = DummyVecEnv([MarioVsLuigiEnv])
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)
    model.save("luigi_rl_agent")
    print("Training complete. Model saved as luigi_rl_agent.zip")

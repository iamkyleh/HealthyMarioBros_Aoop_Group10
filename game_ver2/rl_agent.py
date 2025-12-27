import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import os
import torch
from player import Player
from entity import GRAVITY, FRICTION

class MarioEnv(gym.Env):
    """Custom Gym environment for Mario PvP"""

    def __init__(self, game, ai_player, human_player):
        super(MarioEnv, self).__init__()

        self.game = game
        self.ai_player = ai_player
        self.human_player = human_player
        self.prev_ai_lives = ai_player.lives
        self.prev_human_lives = human_player.lives
        self.prev_distance = 0

        # Action space: [move_left, move_right, jump, attack]
        self.action_space = spaces.MultiDiscrete([2, 2, 2, 2])

        # Observation space: [ai_x, ai_y, ai_vel_x, ai_vel_y, ai_lives,
        #                     human_x, human_y, human_vel_x, human_vel_y, human_lives,
        #                     distance_x, distance_y, ai_direction, human_direction]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, -10, -20, 0, 0, 0, -10, -20, 0, -800, -600, -1, -1]),
            high=np.array([800, 600, 10, 20, 3, 800, 600, 10, 20, 3, 800, 600, 1, 1]),
            dtype=np.float32
        )

    def _get_obs(self):
        """Get current observation"""
        ai_x, ai_y = self.ai_player.x, self.ai_player.y
        human_x, human_y = self.human_player.x, self.human_player.y

        obs = np.array([
            ai_x, ai_y, self.ai_player.vel_x, self.ai_player.vel_y, self.ai_player.lives,
            human_x, human_y, self.human_player.vel_x, self.human_player.vel_y, self.human_player.lives,
            human_x - ai_x, human_y - ai_y,
            self.ai_player.direction, self.human_player.direction
        ], dtype=np.float32)

        return obs

    def reset(self, seed=None, options=None):
        """Reset the environment"""
        super().reset(seed=seed)

        # Reset players to starting positions
        self.ai_player.x, self.ai_player.y = 100, 400
        self.ai_player.vel_x, self.ai_player.vel_y = 0, 0
        self.ai_player.lives = 3

        self.human_player.x, self.human_player.y = 600, 400
        self.human_player.vel_x, self.human_player.vel_y = 0, 0
        self.human_player.lives = 3

        self.prev_ai_lives = 3
        self.prev_human_lives = 3
        self.prev_distance = abs(self.human_player.x - self.ai_player.x)

        return self._get_obs(), {}

    def step(self, action):
        """Execute one step in the environment"""
        # Convert action to input dict
        move_left, move_right, jump, attack = action

        # Calculate move direction
        move_dir = 0
        if move_right and not move_left:
            move_dir = 1
        elif move_left and not move_right:
            move_dir = -1

        inp = {
            "move": move_dir,
            "jump": bool(jump),
            "attack": bool(attack)
        }

        # Generate simulated human input (simple AI behavior for training)
        human_input = self._get_simulated_human_input()

        # Update AI player
        self.ai_player.update(self.game.platforms, inp)

        # Update human player with simulated input
        self.human_player.update(self.game.platforms, human_input)

        # Update game state (this will handle collisions)
        self.game.update({self.ai_player.name: inp, self.human_player.name: human_input})

        # Calculate reward
        reward = 0

        # Reward for damaging opponent
        if self.human_player.lives < self.prev_human_lives:
            reward += 10
        if self.ai_player.lives < self.prev_ai_lives:
            reward -= 10

        # Reward for getting closer to opponent
        current_distance = abs(self.human_player.x - self.ai_player.x)
        if current_distance < self.prev_distance:
            reward += 0.1
        elif current_distance > self.prev_distance:
            reward -= 0.1

        # Small reward for staying alive
        reward += 0.01

        # Check if episode is done
        done = False
        if self.ai_player.lives <= 0 or self.human_player.lives <= 0:
            done = True
            if self.ai_player.lives > 0:
                reward += 50  # Win reward
            else:
                reward -= 50  # Loss penalty

        # Update previous values
        self.prev_ai_lives = self.ai_player.lives
        self.prev_human_lives = self.human_player.lives
        self.prev_distance = current_distance

        return self._get_obs(), reward, done, False, {}

    def _get_simulated_human_input(self):
        """Generate simulated human input for training (simple AI behavior)"""
        # Simple AI: move towards AI player, occasional jumps and attacks
        distance_x = self.ai_player.x - self.human_player.x
        distance_y = self.ai_player.y - self.human_player.y

        # Move towards AI player
        move_dir = 0
        if distance_x > 20:  # AI is to the right
            move_dir = 1
        elif distance_x < -20:  # AI is to the left
            move_dir = -1

        # Occasional jump (10% chance)
        jump = np.random.random() < 0.1

        # Occasional attack (5% chance)
        attack = np.random.random() < 0.05

        return {
            "move": move_dir,
            "jump": jump,
            "attack": attack
        }

class RLAgent:
    """Reinforcement Learning Agent for Mario PvP"""

    def __init__(self, model_path=None, difficulty='medium'):
        self.model_path = model_path or "mario_pvp_ai"
        self.model = None
        self.difficulty = difficulty

    def create_env(self, game, ai_player, human_player):
        """Create the RL environment"""
        def make_env():
            return MarioEnv(game, ai_player, human_player)

        self.env = DummyVecEnv([make_env])
        return self.env

    def train(self, env, total_timesteps=100000):
        """Train the RL model"""
        self.model = PPO("MlpPolicy", env, verbose=1, learning_rate=3e-4, n_steps=2048, batch_size=64, n_epochs=10)
        self.model.learn(total_timesteps=total_timesteps)
        self.save_model()

    def load_model(self):
        """Load a trained model"""
        if os.path.exists(f"{self.model_path}.zip"):
            self.model = PPO.load(self.model_path)
            print(f"Loaded model from {self.model_path}")
        else:
            print(f"No model found at {self.model_path}")

    def save_model(self):
        """Save the trained model"""
        if self.model:
            self.model.save(self.model_path)
            print(f"Saved model to {self.model_path}")

    def get_action(self, observation):
        """Get action from the model"""
        if self.model is None:
            return [0, 0, 0, 0]  # Default action: do nothing

        action, _ = self.model.predict(observation, deterministic=True)
        return action

class AIPlayer(Player):
    """AI-controlled player using RL"""

    def __init__(self, name, rebornpoint, agent=None):
        super().__init__(name, rebornpoint)
        self.agent = agent
        self.observation = None

    def get_ai_input(self, game, human_player):
        """Get input from AI agent"""
        if self.agent is None or self.agent.model is None:
            # Fallback: simple AI (move toward player, jump/attack randomly)
            move_dir = 1 if human_player.x > self.x else -1 if human_player.x < self.x else 0
            difficulty = getattr(self.agent, 'difficulty', 'medium') if self.agent else 'medium'
            if difficulty == 'easy':
                jump = np.random.random() < 0.05
                attack = np.random.random() < 0.05
            elif difficulty == 'hard':
                jump = np.random.random() < 0.2
                attack = np.random.random() < 0.5
            else:
                jump = np.random.random() < 0.1
                attack = np.random.random() < 0.2
            print(f"[Luigi {difficulty} AI] move: {move_dir}, jump: {jump}, attack: {attack}")
            return {"move": move_dir, "jump": jump, "attack": attack}
        # RL agent
        ai_x, ai_y = self.x, self.y
        human_x, human_y = human_player.x, human_player.y
        obs = np.array([
            ai_x, ai_y, self.vel_x, self.vel_y, self.lives,
            human_x, human_y, human_player.vel_x, human_player.vel_y, human_player.lives,
            human_x - ai_x, human_y - ai_y,
            self.direction, human_player.direction
        ], dtype=np.float32)
        action = self.agent.get_action(obs)
        move_left, move_right, jump, attack = action
        move_dir = 0
        if move_right and not move_left:
            move_dir = 1
        elif move_left and not move_right:
            move_dir = -1
        print(f"[Luigi RL AI] move: {move_dir}, jump: {bool(jump)}, attack: {bool(attack)}")
        return {
            "move": move_dir,
            "jump": bool(jump),
            "attack": bool(attack)
        }
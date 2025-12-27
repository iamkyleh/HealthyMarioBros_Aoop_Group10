#!/usr/bin/env python3
"""
Training script for Mario PvP AI using Stable Baselines 3
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rl_agent import MarioEnv, RLAgent, AIPlayer
from player import Player
from server import Game
from weapon import FireFlower
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import numpy as np

def create_training_env():
    """Create environment for training"""
    # Create a game instance
    game = Game("pvp_arena", pvp_mode=True)

    # Create AI player
    ai_player = AIPlayer("AI_Train", (100, 400))

    # Create human player (simulated opponent)
    human_player = Player("Human", (600, 400))

    # Set factions
    ai_player.faction = "p1"
    human_player.faction = "p2"

    # Give weapons
    from weapon import FireFlower
    ai_player.weapon = FireFlower(owner=ai_player)
    human_player.weapon = FireFlower(owner=human_player)

    # Add players to game
    game.players = [ai_player, human_player]

    def make_env():
        return MarioEnv(game, ai_player, human_player)

    env = DummyVecEnv([make_env])
    return env

def train_ai():
    """Train the AI model"""
    print("Creating training environment...")
    env = create_training_env()

    print("Creating RL agent...")
    agent = RLAgent("mario_pvp_ai")

    print("Starting training...")
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=3e-4, n_steps=2048, batch_size=64, n_epochs=10)
    model.learn(total_timesteps=100000)  # Increased for better training

    print("Saving model...")
    model.save("mario_pvp_ai")
    print("Training completed!")

def test_ai():
    """Test the trained AI"""
    print("Loading trained model...")
    agent = RLAgent("mario_pvp_ai")
    agent.load_model()

    if agent.model is None:
        print("No trained model found. Please train the AI first.")
        return

    print("Creating test environment...")
    env = create_training_env()

    print("Testing AI...")
    obs = env.reset()
    total_reward = 0
    done = False
    step = 0

    while not done and step < 1000:
        action, _ = agent.model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        total_reward += reward
        step += 1

    print(f"Test completed. Total reward: {total_reward}, Steps: {step}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train or test Mario PvP AI")
    parser.add_argument("action", choices=["train", "test"], help="Action to perform")

    args = parser.parse_args()

    if args.action == "train":
        train_ai()
    elif args.action == "test":
        test_ai()
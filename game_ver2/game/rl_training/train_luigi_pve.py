"""
Train Luigi RL agent for PVE mode using Stable Baselines3.
Run this script to train the AI, then the trained model will be used in PVE game mode.
"""
import sys
import os
import numpy as np
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Initialize pygame before importing game modules
import pygame
pygame.init()

from luigi_pve_env import LuigiPVEEnv

def train_luigi(total_timesteps=100000, save_path=None):
    """
    Train Luigi RL agent using PPO algorithm.
    
    Args:
        total_timesteps: Number of training steps
        save_path: Path to save the trained model (default: saves to game_ver2/ folder)
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
        from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
        from stable_baselines3.common.monitor import Monitor
    except ImportError:
        print("=" * 60)
        print("ERROR: stable_baselines3 not installed!")
        print("Please install it with: pip install stable-baselines3[extra]")
        print("=" * 60)
        return None
    
    print("=" * 60)
    print("Luigi RL Training for PVE Mode")
    print("=" * 60)
    print(f"Training for {total_timesteps:,} timesteps")
    print()
    
    # Default save path
    if save_path is None:
        save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../luigi_pve_ai'))
    
    # Create environment
    def make_env():
        env = LuigiPVEEnv()
        env = Monitor(env)
        return env
    
    # Use vectorized environment for faster training
    n_envs = 4  # Number of parallel environments
    env = DummyVecEnv([make_env for _ in range(n_envs)])
    
    # Create evaluation environment
    eval_env = DummyVecEnv([make_env])
    
    # Create callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=10000 // n_envs,
        save_path=os.path.dirname(save_path),
        name_prefix="luigi_checkpoint"
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.dirname(save_path),
        log_path=os.path.dirname(save_path),
        eval_freq=5000 // n_envs,
        deterministic=True,
        render=False
    )
    
    # Create PPO model with tuned hyperparameters for combat
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,  # Discount factor
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,  # Entropy coefficient for exploration
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=os.path.join(os.path.dirname(save_path), "tensorboard_logs")
    )
    
    print(f"Model created. Training...")
    print(f"Model will be saved to: {save_path}.zip")
    print()
    
    # Train the model
    start_time = datetime.now()
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback],
        progress_bar=True
    )
    training_time = datetime.now() - start_time
    
    # Save the final model
    model.save(save_path)
    print()
    print("=" * 60)
    print(f"Training complete!")
    print(f"Training time: {training_time}")
    print(f"Model saved to: {save_path}.zip")
    print("=" * 60)
    
    # Cleanup
    env.close()
    eval_env.close()
    
    return model


def test_luigi(model_path=None, episodes=5):
    """
    Test the trained Luigi agent.
    
    Args:
        model_path: Path to the saved model
        episodes: Number of test episodes
    """
    try:
        from stable_baselines3 import PPO
    except ImportError:
        print("ERROR: stable_baselines3 not installed!")
        return
    
    if model_path is None:
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../luigi_pve_ai.zip'))
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        print("Please train the model first using: python train_luigi_pve.py --train")
        return
    
    print("=" * 60)
    print("Testing Luigi RL Agent")
    print("=" * 60)
    
    # Load model
    model = PPO.load(model_path)
    
    # Create test environment
    env = LuigiPVEEnv(render_mode="human")
    
    wins = 0
    losses = 0
    
    for episode in range(episodes):
        obs, info = env.reset()
        total_reward = 0
        done = False
        step = 0
        
        print(f"\n--- Episode {episode + 1} ---")
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
            step += 1
            
            if step % 100 == 0:
                env.render()
        
        print(f"Episode {episode + 1} finished:")
        print(f"  Steps: {step}")
        print(f"  Total reward: {total_reward:.2f}")
        print(f"  Luigi lives: {info['luigi_lives']}")
        print(f"  Mario lives: {info['mario_lives']}")
        
        if info['mario_lives'] <= 0:
            wins += 1
            print("  Result: LUIGI WINS!")
        elif info['luigi_lives'] <= 0:
            losses += 1
            print("  Result: MARIO WINS!")
        else:
            print("  Result: DRAW (timeout)")
    
    env.close()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {wins} wins, {losses} losses out of {episodes} episodes")
    print(f"Win rate: {wins/episodes*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train or test Luigi RL agent for PVE mode")
    parser.add_argument("--train", action="store_true", help="Train the agent")
    parser.add_argument("--test", action="store_true", help="Test the trained agent")
    parser.add_argument("--timesteps", type=int, default=100000, help="Number of training timesteps")
    parser.add_argument("--episodes", type=int, default=5, help="Number of test episodes")
    parser.add_argument("--model", type=str, default=None, help="Path to model file")
    
    args = parser.parse_args()
    
    if args.train:
        train_luigi(total_timesteps=args.timesteps, save_path=args.model)
    elif args.test:
        test_luigi(model_path=args.model, episodes=args.episodes)
    else:
        print("Luigi PVE RL Training Script")
        print("=" * 40)
        print("Usage:")
        print("  Train:  python train_luigi_pve.py --train --timesteps 100000")
        print("  Test:   python train_luigi_pve.py --test --episodes 10")
        print()
        print("The trained model will be saved as 'luigi_pve_ai.zip' in game_ver2/")
        print()
        
        # Default: train with fewer timesteps for quick start
        print("Starting quick training (50000 timesteps)...")
        train_luigi(total_timesteps=50000)

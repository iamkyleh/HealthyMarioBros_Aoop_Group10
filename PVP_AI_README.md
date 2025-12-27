# Healthy Mario Bros - PvP Mode with AI

This project now includes a Player vs Player (PvP) mode with reinforcement learning AI opponents.

## Quick Start - Play Against AI

1. **Train the AI** (optional - a basic model is already trained):

   ```bash
   python train_ai.py train
   ```

2. **Start the game**:

   ```bash
   python play_ai.py
   ```

   This will start both server and client automatically.

3. **Enable PvP mode**:
   - During world selection, press **'V'** to toggle PvP mode
   - Select **"pvp_arena"** world
   - The AI will automatically join as your opponent!

## Manual Setup

If you prefer to start manually:

1. **Terminal 1 - Start Server**:

   ```bash
   python server.py
   ```

2. **Terminal 2 - Start Client**:

   ```bash
   python client.py
   ```

3. **In Client**:
   - Press **'V'** to enable PvP mode
   - Select **"pvp_arena"** from world list
   - AI joins automatically!
4. Select the "pvp_arena" world for the box arena
5. The AI will automatically join as a second player if you're alone

### Training the AI

1. Install dependencies:

   ```bash
   pip install stable-baselines3 gymnasium
   ```

2. Train the AI:

   ```bash
   python train_ai.py train
   ```

3. Test the trained AI:
   ```bash
   python train_ai.py test
   ```

### Controls

- **Movement**: WASD or Arrow keys
- **Jump**: Space or W/Up arrow
- **Attack**: Left mouse button or X key
- **Toggle PvP**: V key (during world selection)

## AI Training Details

The AI observes:

- Player positions and velocities
- Health (lives) of both players
- Relative distance between players
- Direction facing

The AI can perform:

- Move left/right
- Jump
- Attack with fireballs

Rewards:

- +10 for damaging opponent
- -10 for taking damage
- Small rewards for getting closer to opponent
- +50 for winning, -50 for losing

## Technical Details

- Uses PPO (Proximal Policy Optimization) algorithm
- Custom Gym environment compatible with Stable Baselines 3
- Model saved as `mario_pvp_ai.zip`
- Training uses 50,000 timesteps (adjustable)

## Future Improvements

- More sophisticated reward functions
- Additional AI behaviors (dodging, combo attacks)
- Multiple AI difficulty levels
- Human vs Human PvP support
- Tournament mode

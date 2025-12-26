# Healthy Mario Bros

## Introduction

Healthy Mario Bros is an innovative take on the classic Super Mario Bros game, designed to promote physical health and activity. Unlike traditional games that rely on keyboard or controller inputs, this version uses real-time pose detection via webcam to control the character. By leveraging MediaPipe's advanced computer vision capabilities, players perform physical movements (such as jumping) to navigate Mario through levels, turning gameplay into an active fitness experience.

This project was developed as part of an AOOP (Advanced Object-Oriented Programming) course by Group 10.

## Features

- **Pose-Based Controls**: Use body movements to control Mario's actions, detected using MediaPipe.
- **Health Integration**: Encourages physical activity by requiring players to jump or move in real life.
- **Multiple Versions**: Includes basic (ver1) and advanced (ver2) implementations with networking support.
- **Detection Modules**: Separate components for pose detection, jump detection, and camera integration.

## Project Structure

- `game_ver1/`: Basic single-player Pygame implementation.
- `game_ver2/`: Advanced version with multiplayer networking, pose detection, and client-server architecture.
- `MediaPipe_Detection/`: Standalone detection scripts for testing pose and jump detection.
- `Game_Detection_iIntergrate_Test/`: Integration tests combining game and detection.
- `images/`: Game sprites and assets.
- `worlds/`: JSON files defining game levels.
- `sample code/`: Example implementations.

## Requirements

- Python 3.x
- Pygame
- MediaPipe
- OpenCV
- NumPy

Install dependencies using pip:

```
pip install pygame mediapipe opencv-python numpy
```

## How to Run

### Version 1 (Basic)

Navigate to `game_ver1/` and run:

```
python main.py
```

### Version 2 (Advanced with Detection)

1. Start the server:
   ```
   python game_ver2/server.py
   ```
2. Start the client:
   ```
   python game_ver2/client.py
   ```
3. Ensure your webcam is connected for pose detection.

### Testing Detection

Run detection modules separately:

```
python MediaPipe_Detection/pose_camera.py
```

## Controls

- **Pose Controls**: Physical jumping detected via webcam for Mario's jump action.
- **Keyboard**: Arrow keys or WASD for movement (fallback controls).

## Contributing

This is a group project. For contributions, please coordinate with Group 10 members.

## License

[Add license if applicable]

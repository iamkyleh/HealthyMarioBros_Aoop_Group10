import os

BASE_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(BASE_DIR)
IMAGE_DIR = os.path.join(PARENT_DIR, "images")
WORLD_DIR = os.path.join(PARENT_DIR, "worlds")

def image_path(name: str) -> str:
    return os.path.join(IMAGE_DIR, name)

def world_path(name: str) -> str:
    return os.path.join(WORLD_DIR, name)


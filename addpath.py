import os

BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")
WORLD_DIR = os.path.join(BASE_DIR, "worlds")

def image_path(name: str) -> str:
    return os.path.join(IMAGE_DIR, name)
def world_path(name: str) -> str:
    return os.path.join(WORLD_DIR, name)
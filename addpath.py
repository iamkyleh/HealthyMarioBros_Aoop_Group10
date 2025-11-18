import os

BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")

def image_path(name: str) -> str:
    return os.path.join(IMAGE_DIR, name)
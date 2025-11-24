import pygame

def _pressed(keys, code):
    try:
        if isinstance(keys, dict):
            return keys.get(code, False)
        return bool(keys[code])
    except Exception:
        return False

def get_keyboard_input(keys, mapping):
    move_x = 0
    if _pressed(keys, mapping["left"]):
        move_x -= 1
    if _pressed(keys, mapping["right"]):
        move_x += 1
    jump_pressed = _pressed(keys, mapping["jump"])
    return move_x, jump_pressed

KEYBOARD_MAPPINGS = {
    "wasd": {
        "left": pygame.K_a,
        "right": pygame.K_d,
        "jump": pygame.K_w,
    },
    "arrows": {
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "jump": pygame.K_UP,
    },
    "ijkl": {
        "left": pygame.K_j,
        "right": pygame.K_l,
        "jump": pygame.K_i,
    },
}

def input(keys, keyboard):
    mapping = KEYBOARD_MAPPINGS.get(keyboard)
    if mapping:
        return get_keyboard_input(keys, mapping)
    return 0, False

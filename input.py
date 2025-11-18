import pygame

def _pressed(keys, code):
    try:
        if isinstance(keys, dict):
            return keys.get(code, False)
        return bool(keys[code])
    except Exception:
        return False

def get_keyboard_input_wasd(keys):
    move_x: int = 0
    if _pressed(keys, pygame.K_a):
        move_x -= 1
    if _pressed(keys, pygame.K_d):
        move_x += 1
    jump_pressed = _pressed(keys, pygame.K_w)
    return move_x, jump_pressed

def get_keyboard_input_arrows(keys):
    move_x: int = 0
    if _pressed(keys, pygame.K_LEFT):
        move_x -= 1
    if _pressed(keys, pygame.K_RIGHT):
        move_x += 1
    jump_pressed = _pressed(keys, pygame.K_UP)
    return move_x, jump_pressed

def input(keys, keyboard):
    if keyboard == "wasd":
        return get_keyboard_input_wasd(keys)
    elif keyboard == "arrows":
        return get_keyboard_input_arrows(keys)
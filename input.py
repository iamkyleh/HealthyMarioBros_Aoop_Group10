import pygame

def _pressed(keys, code):
    try:
        if isinstance(keys, dict):
            return keys.get(code, False)
        return bool(keys[code])
    except Exception:
        return False

def get_keyboard_input(keys):
    move_x: int = 0
    if _pressed(keys, pygame.K_a) or _pressed(keys, pygame.K_LEFT):
        move_x -= 1
    if _pressed(keys, pygame.K_d) or _pressed(keys, pygame.K_RIGHT):
        move_x += 1
    jump_pressed = (
        _pressed(keys, pygame.K_SPACE) or
        _pressed(keys, pygame.K_w) or
        _pressed(keys, pygame.K_UP)
    )
    attack_pressed = _pressed(keys, pygame.K_k)
    return move_x, jump_pressed, attack_pressed

input = get_keyboard_input
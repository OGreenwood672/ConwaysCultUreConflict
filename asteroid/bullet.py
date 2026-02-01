import math

import pygame

from globals import BULLET_LIFETIME, BULLET_SPEED, WHITE


class Bullet:
    def __init__(self, x, y, target_x, target_y, target_id):
        self.x = x
        self.y = y
        self.target_id = target_id
        self.life = BULLET_LIFETIME

        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.vx = dx / dist * BULLET_SPEED
            self.vy = dy / dist * BULLET_SPEED
        else:
            self.vx = 0
            self.vy = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (int(self.x) + 200, int(self.y) + 200), 3)

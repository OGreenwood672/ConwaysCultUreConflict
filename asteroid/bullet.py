

import pygame
import math
from asteroid.globals import BULLET_LIFETIME, BULLET_SPEED, WHITE, wrap_position


class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.life = BULLET_LIFETIME
        # Calculate velocity based on angle
        rad = math.radians(self.angle)
        self.vx = math.cos(rad) * BULLET_SPEED
        self.vy = -math.sin(rad) * BULLET_SPEED 

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.x, self.y = wrap_position(self.x, self.y)
        self.life -= 1

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), 3)
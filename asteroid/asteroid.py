import math
from random import random, randint
import pygame

from globals import ASTEROID_SPEED, WHITE, wrap_position


class Asteroid:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size  # 3 = large, 2 = medium, 1 = small
        self.radius = size * 15

        # Random velocity
        angle = randint(0, 360)
        speed = randint(1, ASTEROID_SPEED)
        rad = math.radians(angle)
        self.vx = math.cos(rad) * speed
        self.vy = math.sin(rad) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.x, self.y = wrap_position(self.x, self.y)

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)


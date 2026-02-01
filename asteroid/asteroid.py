import pygame

from globals import WHITE


class Asteroid:
    def __init__(self, x, y, size=2):
        self.x = x
        self.y = y
        self.radius = size * 15

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)


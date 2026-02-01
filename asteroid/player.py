import math

import pygame

CULTURE_COLORS = [
    (255, 255, 255),  # Culture 0: white
    (0, 255, 255),    # Culture 1: cyan
]


class Player:
    def __init__(self, x, y, culture=0):
        self.x = x
        self.y = y
        self.angle = 90  # Pointing up
        self.radius = 15
        self.alive = True
        self.color = CULTURE_COLORS[culture % len(CULTURE_COLORS)]

    def update(self):
        pass

    def draw(self, surface):
        if not self.alive:
            return

        rad = math.radians(self.angle)
        tip_x = self.x + math.cos(rad) * 20
        tip_y = self.y - math.sin(rad) * 20

        rad_left = math.radians(self.angle + 140)
        left_x = self.x + math.cos(rad_left) * 20
        left_y = self.y - math.sin(rad_left) * 20

        rad_right = math.radians(self.angle - 140)
        right_x = self.x + math.cos(rad_right) * 20
        right_y = self.y - math.sin(rad_right) * 20

        pygame.draw.polygon(
            surface,
            self.color,
            [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)],
            2,
        )


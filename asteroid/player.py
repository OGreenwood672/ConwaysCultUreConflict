
import math
from asteroid.bullet import Bullet
from asteroid.globals import HEIGHT, PLAYER_ACCEL, PLAYER_FRICTION, PLAYER_ROTATION_SPEED, WIDTH, wrap_position

import pygame


class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.angle = 90  # Pointing up
        self.vx = 0
        self.vy = 0
        self.radius = 15
        self.bullets = []
        self.alive = True

    def update(self):
        keys = pygame.key.get_pressed()

        # Rotation
        if keys[pygame.K_LEFT]:
            self.angle += PLAYER_ROTATION_SPEED
        if keys[pygame.K_RIGHT]:
            self.angle -= PLAYER_ROTATION_SPEED

        # Thrust
        if keys[pygame.K_UP]:
            rad = math.radians(self.angle)
            self.vx += math.cos(rad) * PLAYER_ACCEL
            self.vy -= math.sin(rad) * PLAYER_ACCEL

        # Physics application
        self.x += self.vx
        self.y += self.vy
        self.vx *= PLAYER_FRICTION
        self.vy *= PLAYER_FRICTION
        
        self.x, self.y = wrap_position(self.x, self.y)

        # Update bullets
        for b in self.bullets[:]:
            b.update()
            if b.life <= 0:
                self.bullets.remove(b)

    def shoot(self):
        self.bullets.append(Bullet(self.x, self.y, self.angle))

    def draw(self, surface):
        if not self.alive: return
        
        # Draw Ship (Triangle)
        # Tip of the ship
        rad = math.radians(self.angle)
        tip_x = self.x + math.cos(rad) * 20
        tip_y = self.y - math.sin(rad) * 20
        
        # Rear Left
        rad_left = math.radians(self.angle + 140)
        left_x = self.x + math.cos(rad_left) * 20
        left_y = self.y - math.sin(rad_left) * 20

        # Rear Right
        rad_right = math.radians(self.angle - 140)
        right_x = self.x + math.cos(rad_right) * 20
        right_y = self.y - math.sin(rad_right) * 20

        pygame.draw.polygon(surface, WHITE, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)], 2)

        # Draw bullets
        for b in self.bullets:
            b.draw(surface)
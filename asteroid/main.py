from asteroid.asteroid import Asteroid
from asteroid.globals import BLACK, FPS, HEIGHT, RED, WIDTH
from asteroid.player import Player
import pygame
import math
import random


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Asteroids")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 30)


def main():
    player = Player()
    asteroids = []
    
    # Spawn initial asteroids
    for _ in range(5):
        # Spawn away from center so player doesn't die instantly
        while True:
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            if math.hypot(x - player.x, y - player.y) > 150:
                asteroids.append(Asteroid(x, y, 3)) # Size 3 = Large
                break

    running = True
    while running:
        clock.tick(FPS)
        screen.fill(BLACK)

        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.alive:
                    player.shoot()
                if event.key == pygame.K_r and not player.alive:
                    main() # Restart
                    return

        # 2. Updates
        player.update()
        for a in asteroids:
            a.update()

        # 3. Collision Logic
        if player.alive:
            # Check Ship vs Asteroids
            player_rect = pygame.Rect(player.x - player.radius, player.y - player.radius, player.radius*2, player.radius*2)
            for a in asteroids:
                dist = math.hypot(player.x - a.x, player.y - a.y)
                if dist < player.radius + a.radius:
                    player.alive = False
                    print("GAME OVER")

            # Check Bullets vs Asteroids
            for b in player.bullets[:]:
                for a in asteroids[:]:
                    dist = math.hypot(b.x - a.x, b.y - a.y)
                    if dist < a.radius:
                        if b in player.bullets: player.bullets.remove(b)
                        if a in asteroids: asteroids.remove(a)
                        
                        # Split asteroid
                        if a.size > 1:
                            asteroids.append(Asteroid(a.x, a.y, a.size - 1))
                            asteroids.append(Asteroid(a.x, a.y, a.size - 1))
                        break

        # 4. Drawing
        player.draw(screen)
        for a in asteroids:
            a.draw(screen)

        if not player.alive:
            text = font.render("GAME OVER - Press R to Restart", True, RED)
            screen.blit(text, (WIDTH//2 - 200, HEIGHT//2))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
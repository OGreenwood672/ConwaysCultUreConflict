import json
import os

from globals import BLACK, FPS, WIDTH, HEIGHT
from player import Player
import pygame


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Asteroids")
clock = pygame.time.Clock()

START_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "public", "logs", "start.json"
)


def load_players():
    with open(START_JSON_PATH) as f:
        data = json.load(f)
    # Data is keyed by player name; flatten all entries
    players = []
    for entries in data.values():
        for entry in entries:
            gx, gy = entry["initial_position"]
            x = gx * WIDTH / 100
            y = gy * HEIGHT / 100
            players.append(Player(x, y, culture=entry["culture"]))
    return players


def main():
    players = load_players()

    running = True
    while running:
        clock.tick(FPS)
        screen.fill(BLACK)

        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. Updates
        for p in players:
            p.update()

        # 3. Drawing
        for p in players:
            p.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()


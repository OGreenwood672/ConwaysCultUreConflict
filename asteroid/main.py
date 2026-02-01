import csv
import json
import os
from collections import defaultdict

import math

from asteroid import Asteroid
from bullet import Bullet
from globals import BLACK, FPS, WIDTH, HEIGHT
from player import Player
import pygame


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Asteroids")
clock = pygame.time.Clock()

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "logs")


def load_players():
    with open(os.path.join(LOGS_DIR, "start.json")) as f:
        data = json.load(f)["bob"]
    players = {}
    for entry in data:
        gx, gy = entry["initial_position"]
        x = gx * WIDTH / 100
        y = gy * HEIGHT / 100
        players[entry["id"]] = Player(x, y, culture=entry["culture"])
    return players


def load_updates():
    """Returns a dict mapping tick -> list of (agent_id, action, x, y, other_agent_id)."""
    updates = defaultdict(list)
    with open(os.path.join(LOGS_DIR, "updates.csv"), newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tick = int(row["tick"])
            agent_id = int(row["agent_id"])
            action = row["action"]
            x = float(row["x"]) * WIDTH / 100 if row["x"] else 0
            y = float(row["y"]) * HEIGHT / 100 if row["y"] else 0
            other = int(row["other_agent_id"]) if row["other_agent_id"] else None
            updates[tick].append((agent_id, action, x, y, other))
    return updates


def main():
    players = load_players()
    updates = load_updates()
    asteroids = []
    bullets = []
    max_tick = max(updates.keys()) if updates else 0
    tick = 0
    next_tick_time = pygame.time.get_ticks() + 1000  # first tick fires after 1 second

    running = True
    while running:
        clock.tick(FPS)
        screen.fill(BLACK)

        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. Apply updates once per second
        now = pygame.time.get_ticks()
        if now >= next_tick_time and tick <= max_tick:
            for agent_id, action, x, y, other_agent_id in updates.get(tick, []):
                if agent_id in players:
                    players[agent_id].x = x
                    players[agent_id].y = y
                if action == "build":
                    asteroids.append(Asteroid(x, y))
                if action == "move_attack" and other_agent_id in players:
                    target = players[other_agent_id]
                    attacker = players[agent_id]
                    bullets.append(Bullet(attacker.x, attacker.y, target.x, target.y, other_agent_id))
            tick += 1
            next_tick_time = now + 1000

        # 3. Update and collide bullets
        for b in bullets[:]:
            b.update()
            target = players.get(b.target_id)
            if target and target.alive:
                if math.hypot(b.x - target.x, b.y - target.y) < target.radius:
                    target.alive = False
                    bullets.remove(b)
            elif b.life <= 0:
                bullets.remove(b)

        # 4. Drawing
        for a in asteroids:
            a.draw(screen)
        for b in bullets:
            b.draw(screen)
        for p in players.values():
            p.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

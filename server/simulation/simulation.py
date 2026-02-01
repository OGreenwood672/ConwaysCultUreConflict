import csv
import json
from dataclasses import dataclass
from interface import SimulationInterface
from actions import SimAction, SimActionType


def relative(pos1, pos2):
    return (pos2.x - pos1.x), (pos2.y - pos1.y)


@dataclass
class Pos:
    x: int
    y: int


@dataclass
class Person:
    id: int
    culture: int
    pos: Pos
    hunger: int = 100

@dataclass
class Food:
    pos: Pos

@dataclass
class Building:
    id: int
    culture: int
    pos: Pos


def get_start_json(people):
    json = []

    for person in people:
        json.append({"id": person.id, "culture": person.culture})

    return json


def give_green_what_he_really_really_wants(people):
    json_content = []

    for person in people:
        json_content.append(
            {
                "id": person.id,
                "culture": person.culture,
                "initial_position": (person.pos.x, person.pos.y),
            }
        )

    with open("frontend/public/logs/start.json", "w") as file:
        json.dump({"bob": json_content}, file)


def write_checkpoint(tick, people, buildings, foods, updates_buffer):
    """Write intermediate results every N ticks."""
    import os

    checkpoint_dir = "frontend/public/logs/checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Write state snapshot as JSON
    state = {
        "tick": tick,
        "people": [
            {"id": p.id, "culture": p.culture, "x": p.pos.x, "y": p.pos.y}
            for p in people
        ],
        "buildings": [
            {"id": b.id, "culture": b.culture, "x": b.pos.x, "y": b.pos.y}
            for b in buildings
        ],
        "foods": [{"x": f.pos.x, "y": f.pos.y} for f in foods],
    }
    with open(f"{checkpoint_dir}/state_tick_{tick:04d}.json", "w") as f:
        json.dump(state, f, indent=2)

    # Write updates buffer as CSV
    with open(f"{checkpoint_dir}/updates_tick_{tick:04d}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tick", "agent_id", "action", "x", "y", "other_agent_id", "culture"])
        writer.writerows(updates_buffer)

    print(f"Checkpoint written at tick {tick}")


def get_action_json(people, buildings, foods):
    json = []

    for person in people:
        json.append(
            {
                "id": person.id,
                "culture": person.culture,
                "relative_people": [
                    {
                        "id": other.id,
                        "culture": other.culture,
                        "my_culture": person.culture == other.culture,
                        "relative_pos": relative(person.pos, other.pos),
                    }
                    for other in people
                    if person.id != other.id
                ],
                "relative_buildings": [
                    {
                        "id": building.id,
                        "culture": building.culture,
                        "my_culture": person.culture == building.culture,
                        "relative_pos": relative(person.pos, building.pos),
                    }
                    for building in buildings
                ],
                "relative_foods": [
                    {
                        "relative_pos": relative(
                            person.pos,
                            food.pos,
                        )
                    }
                    for food in foods
                ]
            }
        )

    return json


def update_world(updates, people, buildings, foods, csv_writer):
    """Apply actions to the world state."""
    people_by_id = {p.id: p for p in people}
    pos_to_person = {(p.pos.x, p.pos.y): p for p in people}

    for action in updates:
        person = people_by_id.get(action.person_id)
        if not person:
            continue

        other_agent_id = ""
        extra_info = ""

        if action.action_type == SimActionType.MOVE:
            # Move in direction (dx, dz)
            dx = action.dx or 0
            dz = action.dz or 0
            person.pos.x += dx
            person.pos.y += dz  # y in our 2D sim = z in Minecraft

        elif action.action_type == SimActionType.BUILD:
            # Build at current position
            buildings.append(
                Building(
                    id=len(buildings),
                    culture=person.culture,
                    pos=Pos(person.pos.x, person.pos.y),
                )
            )
            extra_info = action.content or "structure"

        elif action.action_type == SimActionType.COMMUNICATE:
            # Talk to target agent
            if action.target_id is not None:
                other_agent_id = action.target_id
                extra_info = action.content or ""

        elif action.action_type == SimActionType.GATHER:
            # Gather resource at position
            dx = action.dx or 0
            dz = action.dz or 0
            food_pos = (person.pos.x + dx, person.pos.y + dz)
            food_to_remove = None
            for food in foods:
                if (food.pos.x, food.pos.y) == food_pos:
                    food_to_remove = food
                    break
            if food_to_remove:
                foods.remove(food_to_remove)
                person.hunger = min(100, person.hunger + 20)

        elif action.action_type == SimActionType.GIVE:
            # Give item to target agent
            if action.target_id is not None:
                other_agent_id = action.target_id
                extra_info = action.content or "item"

        elif action.action_type == SimActionType.ATTACK:
            # Attack entity at position
            dx = action.dx or 0
            dz = action.dz or 0
            target_pos = (person.pos.x + dx, person.pos.y + dz)
            target = pos_to_person.get(target_pos)
            if target:
                other_agent_id = target.id

        elif action.action_type == SimActionType.EAT:
            # Eat food from inventory
            person.hunger = min(100, person.hunger + 25)
            extra_info = action.content or "food"

        elif action.action_type == SimActionType.IDLE:
            # Do nothing
            pass

        csv_writer.writerow(
            [
                action.tick,
                action.person_id,
                action.action_type.value,
                person.pos.x,
                person.pos.y,
                other_agent_id,
                person.culture,
            ]
        )


def spawn_foods(count: int = 20, world_size: int = 20) -> list[Food]:
    """Spawn food sources randomly across the world."""
    import random
    foods = []
    for _ in range(count):
        x = random.randint(-world_size // 2, world_size // 2)
        y = random.randint(-world_size // 2, world_size // 2)
        foods.append(Food(pos=Pos(x, y)))
    return foods


def start():
    simulation_interface = SimulationInterface()

    cultures = [i for i in range(2)]

    culture_start = [(0, 0), (5, 5)]

    individual_id = 0

    num_individuals = 5

    people = []
    buildings = []
    foods = spawn_foods(count=30)

    for culture in cultures:
        for _ in range(num_individuals):
            people.append(
                Person(
                    id=individual_id, culture=culture, pos=Pos(*culture_start[culture])
                )
            )

            individual_id += 1

    start_json = get_start_json(people)
    simulation_interface.initialize(start_json)

    give_green_what_he_really_really_wants(people)

    total_ticks = 1000
    checkpoint_interval = 10
    updates_buffer = []  # Buffer for checkpoint writes

    with open("frontend/public/logs/updates.csv", "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(
            ["tick", "agent_id", "action", "x", "y", "other_agent_id", "culture"]
        )

        for tick in range(total_ticks):
            # Respawn food periodically
            if tick % 50 == 0 and len(foods) < 10:
                foods.extend(spawn_foods(count=5))

            action_json = get_action_json(people, buildings, foods)
            results = simulation_interface.process_tick(tick, action_json)
            # Handle both dict and SimAction returns (depends on import path)
            updates = [
                SimAction.from_dict(r) if isinstance(r, dict) else r
                for r in results
            ]

            # Collect rows for buffer before update_world modifies positions
            people_by_id = {p.id: p for p in people}
            for action in updates:
                person = people_by_id.get(action.person_id)
                if person:
                    updates_buffer.append([
                        action.tick,
                        action.person_id,
                        action.action_type.value,
                        person.pos.x,
                        person.pos.y,
                        "",
                        person.culture,
                    ])

            update_world(updates, people, buildings, foods, csv_writer)
            print(f"Tick {tick}: {len(updates)} actions, {len(foods)} foods remaining")

            # Write checkpoint every N ticks
            if (tick + 1) % checkpoint_interval == 0:
                write_checkpoint(tick + 1, people, buildings, foods, updates_buffer)
                updates_buffer = []  # Clear buffer after checkpoint

    print(f"Simulation complete: {total_ticks} ticks")


if __name__ == "__main__":
    start()

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


def get_action_json(people, buildings):
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
            }
        )

    return json


def update_world(updates, people, buildings, csv_writer):
    people_by_id = {p.id: p for p in people}
    pos_to_person = {(p.pos.x, p.pos.y): p for p in people}

    for action in updates:
        person = people_by_id.get(action.person_id)
        if not person:
            continue

        other_agent_id = ""

        if action.action_type == SimActionType.MOVE:
            person.pos.x += action.x
            person.pos.y += action.y
        elif action.action_type == SimActionType.BUILD:
            buildings.append(
                Building(
                    id=len(buildings),
                    culture=person.culture,
                    pos=Pos(person.pos.x, person.pos.y),
                )
            )
        elif action.action_type == SimActionType.COMMUNICATE:
            target = pos_to_person.get(
                (person.pos.x + action.x, person.pos.y + action.y)
            )
            if target:
                other_agent_id = target.id

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


def start():
    simulation_interface = SimulationInterface()

    cultures = [i for i in range(2)]

    culture_start = [(0, 0), (5, 5)]

    individual_id = 0

    num_individuals = 5

    people = []
    buildings = []

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

    with open("frontend/public/logs/updates.csv", "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(
            ["tick", "agent_id", "action", "x", "y", "other_agent_id", "culture"]
        )

        for tick in range(2):
            action_json = get_action_json(people, buildings)
            updates = simulation_interface.process_tick(tick, action_json)
            update_world(updates, people, buildings, csv_writer)


if __name__ == "__main__":
    start()

import json
from dataclasses import dataclass
from interface import SimulationInterface


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
        json.dump(json_content, file)


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


def send_get_action_json(action_json):
    pass


def update_world(updates, people, world):
    pass


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

    for tick in range(2):
        action_json = get_action_json(people, buildings)
        updates = simulation_interface.process_tick(tick, action_json)
        update_world(updates, people, buildings)


if __name__ == "__main__":
    start()

from dataclasses import dataclass


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


def start():
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

    get_start_json(people)

    for _ in range(2):
        json = get_action_json(people, buildings)


if __name__ == "__main__":
    start()

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


people = [Person(0, 0, Pos(0, 0)), Person(1, 0, Pos(1, 3))]
buildings = [Building(0, 0, Pos(1, 0)), Building(1, 1, Pos(1, 1))]

for person in people:
    json = {
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

    print(json)

# def start():
#     for i in range

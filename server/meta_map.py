from types import Optional

NUM_ROWS = 10
NUM_COLS = 10


class Cell:
    people: list[int]
    building: Optional[int]

    def __init__(self):
        self.people =

    def pprint():
        print("")


class Grid:
    def __init__(self):
        self.grid = [[Cell() for _ in range(NUM_COLS)]
                     for _ in range(NUM_ROWS)]

    def pprint(self):
        pass

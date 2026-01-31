#!/usr/bin/env python3
"""Test script for grid pretty printing"""

from meta_map import Metamap, Building, Person, Culture

# Create a metamap
metamap = Metamap()

# Create some test cultures
culture1 = Culture(id=1, md="Culture A")
culture2 = Culture(id=2, md="Culture B")
culture3 = Culture(id=3, md="Culture C")

# Add some test data
# Building at (0, 0) with 3 people from culture1
metamap.grid[0][0].building = Building(culture=culture1)
metamap.grid[0][0].people = [
    Person(id=101, culture=culture1, md="Person 101"),
    Person(id=102, culture=culture1, md="Person 102"),
    Person(id=103, culture=culture1, md="Person 103"),
]

# Building at (0, 5) with 1 person from culture2
metamap.grid[0][5].building = Building(culture=culture2)
metamap.grid[0][5].people = [Person(id=104, culture=culture2, md="Person 104")]

# Building at (3, 3) with 5 people from mixed cultures
metamap.grid[3][3].building = Building(culture=culture3)
metamap.grid[3][3].people = [
    Person(id=201, culture=culture1, md="Person 201"),
    Person(id=202, culture=culture1, md="Person 202"),
    Person(id=203, culture=culture2, md="Person 203"),
    Person(id=204, culture=culture2, md="Person 204"),
    Person(id=205, culture=culture1, md="Person 205"),
]

# Empty cell with people at (5, 2) from culture2
metamap.grid[5][2].people = [
    Person(id=301, culture=culture2, md="Person 301"),
    Person(id=302, culture=culture2, md="Person 302"),
]

# Building at (7, 8) with no people from culture1
metamap.grid[7][8].building = Building(culture=culture1)

# Building at (9, 9) with 10 people from culture1
metamap.grid[9][9].building = Building(culture=culture2)
metamap.grid[9][9].people = [
    Person(id=i, culture=culture1, md=f"Person {i}") for i in range(401, 411)
]

print("Metamap Visualization:\n")
metamap.pprint()

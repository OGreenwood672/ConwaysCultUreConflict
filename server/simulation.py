from typing import List

from game import Game


class Culture:
    id: int
    prompt: str

    def __init__(self, id: int, prompt: str):
        self.id = id
        self.prompt = prompt


class Individual:
    id: int
    culture: Culture
    prompt: str

    def __init__(self, id: int, culture: Culture, prompt: str):
        self.id = id
        self.culture = culture
        self.prompt = prompt


class Simulation:
    def __init__(self, games: List[str]):
        def extract(x):
            return open(x).read().strip()

        self.god = extract("initial_prompts/god.md")

        self.cultures = [
            Culture(id, extract(f"initial_prompts/cultures/{name}.md"))
            for name in cultures
        ]

        for culture in self.cultures:
            self.individuals = [
                Individual(, culture, "") for name, culture in individuals
            ]

        self.games = [
            Game(name, websocket=8000 + index) for index, name in enumerate(games)
        ]

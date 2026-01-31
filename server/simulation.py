from typing import List

from server.game import Game

class Culture:
    def __init__(self, name: str, prompt: str):
        self.name = name
        self.prompt = prompt

class Individual:
    def __init__(self, name: str, culture: str):
        self.name = name
        self.culture = culture


class Simulation:

    def __init__(self, cultures, individuals, games: List[str]):

        extract = lambda x: open(x).read().strip()

        self.god = extract("initial_prompts/god.md")

        self.cultures = [Culture(name, extract(f"initial_prompts/cultures/{name}.md")) for name in cultures]

        self.individuals = [Individual(name, culture) for name, culture in individuals]

        self.games = [Game(name, 8000 + index) for index, name in enumerate(games)]

    
    def get_god_prompt(self) -> str:
        return self.god
    
    def get_culture_prompt(self, culture: str) -> str:
        return self.cultures[culture]
    
    def list_cultures(self) -> List[str]:
        return list(self.cultures.keys())
    

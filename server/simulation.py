from typing import List

from server.game import Game


class Simulation:

    def __init__(self, cultures: List[str], games: List[str]):

        extract = lambda x: open(x).read().strip()

        self.god = extract("initial_prompts/god.md")

        self.cultures = {culture: extract(f"initial_prompts/{culture}.md") for culture in cultures}

        self.games = [Game(name, 8000 + index) for index, name in enumerate(games)]

    
    def get_god_prompt(self) -> str:
        return self.god
    
    def get_culture_prompt(self, culture: str) -> str:
        return self.cultures[culture]
    
    def list_cultures(self) -> List[str]:
        return list(self.cultures.keys())
    

import json
from typing import Any, List
from meta_map import Grid

class Game:
    def __init__(self, name: str, websocket: Any):
        self.name = name
        self.websocket = websocket
        self.meta_map = Grid()

    async def stream_json(self, data: dict):
        """
        Streams a JSON-encoded dictionary to the associated websocket.
        """
        await self.websocket.send(json.dumps(data))
    
    def add_player():
        """
        Placeholder method for adding a player to the game.
        """
        pass

    def remove_player():
        """
        Placeholder method for removing a player from the game.
        """
        pass

    def get_relative_locations(player_id: str) -> List[str]:
        """
        Placeholder method for getting relative locations for a player.
        """
        pass

    def move_player(player_id: str, direction: str):
        """
        Placeholder method for moving a player within the game.
        """
        pass

    def make_building(building_type: str):
        """
        Placeholder method for making a building in the game.
        """
        pass

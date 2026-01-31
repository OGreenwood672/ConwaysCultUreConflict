import json
from typing import Any
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

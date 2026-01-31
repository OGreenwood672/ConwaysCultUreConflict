from dataclasses import dataclass
import yaml
from typing import Dict

@dataclass
class CulturesConfig:
    narcissist: int
    collectivist: int
    individualist: int
    traditionalist: int

@dataclass
class Config:
    cultures: CulturesConfig

    @classmethod
    def load_from_yaml(cls, file_path: str = "config.yaml") -> "Config":
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            
        cultures_data = data.get("cultures", {})
        cultures_config = CulturesConfig(
            narcissist=cultures_data.get("narcissist", 0),
            collectivist=cultures_data.get("collectivist", 0),
            individualist=cultures_data.get("individualist", 0),
            traditionalist=cultures_data.get("traditionalist", 0)
        )
        return cls(cultures=cultures_config)

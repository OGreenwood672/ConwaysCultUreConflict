from dataclasses import dataclass
import yaml
from typing import Dict

@dataclass
class Config:
    cultures: Dict[str, int]

    @classmethod
    def load_from_yaml(cls, file_path: str = "config.yaml") -> "Config":
        """
        Loads the configuration from a YAML file.
        Expected format:
        cultures:
          narcissist: 10
          collectivist: 8
          individualist: 6
          traditionalist: 4
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            
        cultures_dict = data.get("cultures", {})
        return cls(cultures=cultures_dict)

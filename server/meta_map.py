from typing import Optional
from dataclasses import dataclass

NUM_ROWS = 10
NUM_COLS = 10

# ANSI color codes for different cultures
CULTURE_COLORS = [
    "\033[91m",  # Red
    "\033[92m",  # Green
    "\033[93m",  # Yellow
    "\033[94m",  # Blue
    "\033[95m",  # Magenta
    "\033[96m",  # Cyan
    "\033[97m",  # White
    "\033[31m",  # Dark Red
    "\033[32m",  # Dark Green
    "\033[33m",  # Dark Yellow
]
RESET_COLOR = "\033[0m"


def get_culture_color(culture_id: int) -> str:
    """Get color for a culture based on its ID"""
    return CULTURE_COLORS[culture_id % len(CULTURE_COLORS)]


@dataclass
class God:
    md: str


@dataclass
class Culture:
    id: int
    md: str


@dataclass
class Person:
    id: int
    culture: Culture
    md: str


@dataclass
class Building:
    culture: Culture


class Cell:
    people: list[Person]
    building: Optional[Building]

    def __init__(self):
        self.people = []
        self.building = None

    def pprint(self, width):
        """Pretty print the cell contents - returns list of lines"""
        # Line 1: Building info with color based on culture
        if self.building is not None:
            color = get_culture_color(self.building.culture.id)
            line1 = f"{color}B:C{self.building.culture.id}{RESET_COLOR}"
            # Calculate padding accounting for ANSI codes
            visible_len = len(f"B:C{self.building.culture.id}")
            padding = width - visible_len
            line1 = line1 + " " * padding
        else:
            line1 = "-".ljust(width)

        # Line 2: People IDs with colors based on their cultures
        if self.people:
            colored_ids = []
            for p in self.people:
                color = get_culture_color(p.culture.id)
                colored_ids.append(f"{color}{p.id}{RESET_COLOR}")
            people_str = "[" + ",".join(colored_ids) + "]"
            # Calculate visible length (without ANSI codes)
            visible_len = len("[" + ",".join(str(p.id) for p in self.people) + "]")
            padding = width - visible_len
            people_str = people_str + " " * padding
        else:
            people_str = "[]".ljust(width)

        return [line1, people_str]


class Metamap:
    def __init__(self):
        self.grid = [[Cell() for _ in range(NUM_COLS)] for _ in range(NUM_ROWS)]

    def pprint(self):
        """Pretty print the entire grid with box-drawing characters"""
        # Calculate maximum width needed per column (based on visible characters)
        col_widths = []
        for col_idx in range(NUM_COLS):
            max_width = 0
            for row in self.grid:
                cell = row[col_idx]
                # Check building width (visible characters only)
                if cell.building is not None:
                    building_str = f"B:C{cell.building.culture.id}"
                else:
                    building_str = "-"
                max_width = max(max_width, len(building_str))
                # Check people list width (visible characters only)
                if cell.people:
                    people_str = "[" + ",".join(str(p.id) for p in cell.people) + "]"
                else:
                    people_str = "[]"
                max_width = max(max_width, len(people_str))
            # Ensure minimum width and add padding
            col_widths.append(max(max_width + 2, 6))

        # Top border with column numbers
        print("    ", end="")
        for col_idx, width in enumerate(col_widths):
            print(f"{col_idx:^{width + 1}}", end="")
        print()

        # Top border
        print("   ┌" + "┬".join(["─" * w for w in col_widths]) + "┐")

        # Print each row (2 lines per row: building line and people line)
        for row_idx, row in enumerate(self.grid):
            # Get all cell contents (each cell returns 2 lines)
            cell_contents = [cell.pprint(col_widths[i]) for i, cell in enumerate(row)]

            # Print line 1: Buildings
            print(f" {row_idx} │", end="")
            for content in cell_contents:
                print(content[0], end="│")
            print()

            # Print line 2: People
            print("   │", end="")
            for content in cell_contents:
                print(content[1], end="│")
            print()

            # Row separator (except after last row)
            if row_idx < NUM_ROWS - 1:
                print("   ├" + "┼".join(["─" * w for w in col_widths]) + "┤")

        # Bottom border
        print("   └" + "┴".join(["─" * w for w in col_widths]) + "┘")

        # Legend
        print("\nLegend:")
        print("  Line 1: Building (B:Cid) - colored by culture")
        print("  Line 2: People IDs [list] - colored by culture")
        print("\nCultures:")
        # Show color samples for cultures seen in the grid
        cultures_seen = set()
        for row in self.grid:
            for cell in row:
                if cell.building:
                    cultures_seen.add(cell.building.culture.id)
                for person in cell.people:
                    cultures_seen.add(person.culture.id)
        for culture_id in sorted(cultures_seen):
            color = get_culture_color(culture_id)
            print(f"  Culture {culture_id}: {color}████{RESET_COLOR}")


@dataclass
class Simulation:
    god: God
    metamaps: list[Metamap]
    people: list[Person]

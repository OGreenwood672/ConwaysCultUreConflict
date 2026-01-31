from typing import Optional

NUM_ROWS = 10
NUM_COLS = 10


class Cell:
    people: list[int]
    building: Optional[int]

    def __init__(self):
        self.people = []
        self.building = None

    def pprint(self, width):
        """Pretty print the cell contents - returns list of lines"""
        # Line 1: Building info
        if self.building is not None:
            line1 = f"B:{self.building}"
        else:
            line1 = "-"

        # Line 2: People IDs (compact format without spaces)
        if self.people:
            # Compact format: [id,id,id] without spaces
            people_str = "[" + ",".join(str(p) for p in self.people) + "]"
        else:
            people_str = "[]"

        return [line1.ljust(width), people_str.ljust(width)]


class Grid:
    def __init__(self):
        self.grid = [[Cell() for _ in range(NUM_COLS)] for _ in range(NUM_ROWS)]

    def pprint(self):
        """Pretty print the entire grid with box-drawing characters"""
        # Calculate maximum width needed per column
        col_widths = []
        for col_idx in range(NUM_COLS):
            max_width = 0
            for row in self.grid:
                cell = row[col_idx]
                # Check building width
                building_str = (
                    f"B:{cell.building}" if cell.building is not None else "-"
                )
                max_width = max(max_width, len(building_str))
                # Check people list width
                if cell.people:
                    people_str = "[" + ",".join(str(p) for p in cell.people) + "]"
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
        print("  Line 1: Building (B:id or -)")
        print("  Line 2: People IDs [list]")

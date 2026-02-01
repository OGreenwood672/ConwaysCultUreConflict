import pyautogui
import requests
import json
import time
import keyboard  # To allow a "kill switch"
from pathlib import Path

# --- CONFIGURATION ---
SIM_LOG_URL = "http://localhost:5173/sim_log.csv"
PERSON_CULTURE_URL = "http://localhost:5173/person_culture.json"
CONFIG_FILE = Path(__file__).parent / "kolourpaint_config.json"

# Safety: Fail-safe if mouse slams into corner
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001  # Make it move as fast as possible


def load_config() -> dict:
    """Load KolourPaint configuration from calibration file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_FILE}\n"
            "Run 'python calibrate.py' first to configure KolourPaint positions."
        )
    with open(CONFIG_FILE) as f:
        return json.load(f)


# Load configuration
CONFIG = load_config()

# Build color lookup: culture_id -> (x, y)
COLOR_POSITIONS = {
    c["culture_id"]: tuple(c["position"])
    for c in CONFIG.get("colors", [])
}

# Tool positions
TOOLS = CONFIG.get("tools", {})

# Canvas mapping
CANVAS = CONFIG.get("canvas", {})
CANVAS_OFFSET_X = CANVAS.get("top_left", [0, 0])[0]
CANVAS_OFFSET_Y = CANVAS.get("top_left", [0, 0])[1]
CANVAS_WIDTH = CANVAS.get("width", 800)
CANVAS_HEIGHT = CANVAS.get("height", 600)

class CsvStreamer:
    def __init__(self, url):
        self.url = url
        self.response = None
        self.line_iterator = None
        self.start()

    def start(self):
        try:
            print(f"Connecting to {self.url}...")
            self.response = requests.get(self.url, stream=True)
            self.line_iterator = self.response.iter_lines(decode_unicode=True)
        except Exception as e:
            print(f"Error connecting: {e}")

    def get_next_line(self):
        # Python iterators are cleaner than the TS buffer implementation
        try:
            line = next(self.line_iterator)
            if line:
                # Parse CSV line into dict
                parts = line.split(',')
                # Assuming CSV columns: tick, person_id, action, x, y, culture
                if len(parts) < 3: return None
                return {
                    "tick": int(parts[0]),
                    "person_id": int(parts[1]),
                    "action": parts[2],
                    "x": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
                    "y": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
                    "culture": int(parts[5]) if len(parts) > 5 and parts[5] else 0,
                    "new_x": float(parts[3]) if len(parts) > 3 and parts[3] else 0, # Mapping for 'move'
                    "new_y": float(parts[4]) if len(parts) > 4 and parts[4] else 0
                }
        except StopIteration:
            return None
        return None

def load_initial_culture():
    """Load initial person/culture mapping from server."""
    print("Loading initial culture...")
    resp = requests.get(PERSON_CULTURE_URL)
    data = resp.json()
    # Convert list to dict for fast lookup
    return {p['id']: p for p in data}


def select_color(culture_id: int) -> bool:
    """Select the color for a given culture. Returns True if successful."""
    if culture_id not in COLOR_POSITIONS:
        print(f"Warning: No color calibrated for culture {culture_id}")
        return False

    current_x, current_y = pyautogui.position()
    btn_x, btn_y = COLOR_POSITIONS[culture_id]
    pyautogui.click(btn_x, btn_y)
    # Move back to where we were to continue drawing
    pyautogui.moveTo(current_x, current_y)
    return True


def select_tool(tool_name: str) -> bool:
    """Select a tool by name (pen, rectangle, eraser). Returns True if successful."""
    if tool_name not in TOOLS:
        print(f"Warning: Tool '{tool_name}' not calibrated")
        return False

    current_x, current_y = pyautogui.position()
    btn_x, btn_y = TOOLS[tool_name]
    pyautogui.click(btn_x, btn_y)
    # Move back to where we were to continue drawing
    pyautogui.moveTo(current_x, current_y)
    return True


def sim_to_screen(x: float, y: float, world_width: float = 100, world_height: float = 100) -> tuple[int, int]:
    """Convert simulation coordinates to screen coordinates."""
    # Map simulation (0,0)-(world_width, world_height) to canvas
    screen_x = CANVAS_OFFSET_X + int((x / world_width) * CANVAS_WIDTH)
    screen_y = CANVAS_OFFSET_Y + int((y / world_height) * CANVAS_HEIGHT)
    return screen_x, screen_y

def main():
    sim_log = CsvStreamer(SIM_LOG_URL)
    person_culture = load_initial_culture()

    curr_tick = 0
    log_entry = sim_log.get_next_line()

    print("Starting simulation in 5 seconds... Switch to KolourPaint!")
    time.sleep(5)

    # Select pen tool initially
    select_tool("pen")
    current_color = None

    while True:
        # Emergency exit
        if keyboard.is_pressed('q'):
            print("Stopping...")
            break

        curr_tick_actions = []

        # Batch read lines for the current tick
        while log_entry and log_entry['tick'] == curr_tick:
            curr_tick_actions.append(log_entry)
            log_entry = sim_log.get_next_line()

            if not log_entry or log_entry['tick'] != curr_tick:
                break

        # Process actions for this tick
        for action in curr_tick_actions:
            pid = action['person_id']

            # Handle "add-person"
            if action['action'] in ("add", "add-person"):
                person_culture[pid] = {
                    'id': pid,
                    'culture': action['culture'],
                    'x': action['x'],
                    'y': action['y']
                }
                continue

            person = person_culture.get(pid)
            if not person:
                continue

            # Convert simulation coords to screen coords
            screen_x, screen_y = sim_to_screen(
                action.get('x', person['x']),
                action.get('y', person['y'])
            )

            if action['action'] == "move":
                # Update position data
                person['x'] = action['new_x']
                person['y'] = action['new_y']

                # Switch color if needed
                culture_id = person['culture']
                if current_color != culture_id:
                    select_color(culture_id)
                    current_color = culture_id

                # Draw at new position
                new_screen_x, new_screen_y = sim_to_screen(
                    action['new_x'], action['new_y']
                )
                pyautogui.click(new_screen_x, new_screen_y)

            elif action['action'] == "build":
                # Switch to rectangle tool
                select_tool("rectangle")
                pyautogui.click(screen_x, screen_y)
                # Switch back to pen
                select_tool("pen")

            elif action['action'] == "die":
                # Optionally use eraser to mark death
                if "eraser" in TOOLS:
                    select_tool("eraser")
                    pyautogui.click(screen_x, screen_y)
                    select_tool("pen")
                # Remove from tracking
                if pid in person_culture:
                    del person_culture[pid]

            elif action['action'] == "idle":
                # No visual action
                pass

        curr_tick += 1


if __name__ == "__main__":
    main()
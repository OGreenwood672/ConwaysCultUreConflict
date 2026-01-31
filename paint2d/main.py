import pyautogui
import requests
import json
import time
import keyboard # To allow a "kill switch"
from collections import deque

# --- CONFIGURATION ---
SIM_LOG_URL = "http://localhost:5173/sim_log.csv"
PERSON_CULTURE_URL = "http://localhost:5173/person_culture.json"

# Screen locations for your Paint app buttons (You must fill these!)
# Use a tool to find X,Y coords of your color palette on screen
BUTTONS = {
    "CULTURE_0": (100, 50), # e.g., Blue
    "CULTURE_1": (150, 50), # e.g., Red
    "CULTURE_2": (200, 50), # e.g., Green
    "BUILD_TOOL": (300, 50), # e.g., Rectangle Tool
    "PEN_TOOL":   (350, 50)  # e.g., Pencil/Brush
}

# Calibration: Where is (0,0) on your drawing canvas?
CANVAS_OFFSET_X = 500
CANVAS_OFFSET_Y = 200
SCALE = 1.0 # Scale coordinates if needed

# Safety: Fail-safe if mouse slams into corner
pyautogui.FAILSAFE = True 
pyautogui.PAUSE = 0.001 # Make it move as fast as possible

class CsvStreamer:
    def __init__(self, url):
        self.url = url
        self.response = None
        self.line_iterator = None
        self.buffer = deque()
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
    print("Loading initial culture...")
    resp = requests.get(PERSON_CULTURE_URL)
    data = resp.json()
    # Convert list to dict for fast lookup
    return {p['id']: p for p in data}

def select_tool(tool_name):
    if tool_name in BUTTONS:
        current_x, current_y = pyautogui.position()
        btn_x, btn_y = BUTTONS[tool_name]
        pyautogui.click(btn_x, btn_y)
        # Move back to where we were to continue drawing
        pyautogui.moveTo(current_x, current_y)

def main():
    sim_log = CsvStreamer(SIM_LOG_URL)
    person_culture = load_initial_culture()
    
    curr_tick = 0
    # Initial read
    log_entry = sim_log.get_next_line()
    
    print("Starting simulation in 5 seconds... Switch to your Paint app!")
    time.sleep(5)
    
    current_tool = None
    
    while True:
        # Emergency exit
        if keyboard.is_pressed('q'):
            print("Stopping...")
            break

        curr_tick_actions = []
        
        # Batch read lines for the current tick
        # Note: parseInt(logEntry.tick) === curr_tick logic
        while log_entry and log_entry['tick'] == curr_tick:
            curr_tick_actions.push(log_entry)
            log_entry = sim_log.get_next_line()
            
            # If we hit the end of the stream or next tick, stop reading
            if not log_entry or log_entry['tick'] != curr_tick:
                break
        
        # Process Actions for this Tick
        for action in curr_tick_actions:
            pid = action['person_id']
            
            # Handle "Add"
            if action['action'] == "add":
                person_culture[pid] = {
                    'id': pid,
                    'culture': action['culture'],
                    'x': action['x'],
                    'y': action['y']
                }
                continue

            person = person_culture.get(pid)
            if not person: continue

            # --- EXECUTE DRAWING ---
            screen_x = CANVAS_OFFSET_X + (action.get('x', person['x']) * SCALE)
            screen_y = CANVAS_OFFSET_Y + (action.get('y', person['y']) * SCALE)

            if action['action'] == "move":
                # Update data
                person['x'] = action['new_x']
                person['y'] = action['new_y']
                
                # Draw the dot
                # Check if we need to switch color based on culture
                needed_tool = f"CULTURE_{person['culture']}"
                if current_tool != needed_tool:
                    select_tool(needed_tool)
                    current_tool = needed_tool
                
                # Move and Click (Draw)
                pyautogui.click(screen_x, screen_y)

            elif action['action'] == "build":
                # Switch to build tool (e.g., rectangle)
                if current_tool != "BUILD_TOOL":
                    select_tool("BUILD_TOOL")
                    current_tool = "BUILD_TOOL"
                
                pyautogui.click(screen_x, screen_y)
                
            elif action['action'] == "die":
                # Maybe select eraser or cross them out?
                del person_culture[pid]

        curr_tick += 1
        # No sleep needed really, PyAutoGUI is the bottleneck

if __name__ == "__main__":
    main()
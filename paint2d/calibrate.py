#!/usr/bin/env python3
"""
Calibration tool for KolourPaint automation.
Records screen positions of colors, tools, and canvas boundaries.
"""

import pyautogui
import json
import time
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "kolourpaint_config.json"

def wait_for_enter(prompt: str) -> tuple[int, int]:
    """Wait for user to press Enter, then capture mouse position."""
    input(f"\n{prompt}\nPosition your mouse and press ENTER...")
    pos = pyautogui.position()
    print(f"  Recorded: ({pos.x}, {pos.y})")
    return (pos.x, pos.y)

def calibrate_colors(config: dict) -> None:
    """Calibrate color palette positions."""
    print("\n" + "="*50)
    print("COLOR CALIBRATION")
    print("="*50)
    print("""
KolourPaint's color palette is typically at the bottom of the window.
You'll record positions for each color you want to use.

For each color:
1. Hover your mouse over the color in the palette
2. Press ENTER to record

Press Ctrl+C when done adding colors.
""")

    colors = []
    color_idx = 0

    try:
        while True:
            pos = wait_for_enter(f"Color {color_idx} (culture {color_idx})")
            colors.append({
                "culture_id": color_idx,
                "position": list(pos)
            })
            color_idx += 1
    except KeyboardInterrupt:
        print(f"\n  Recorded {len(colors)} colors")

    config["colors"] = colors

def calibrate_tools(config: dict) -> None:
    """Calibrate tool positions."""
    print("\n" + "="*50)
    print("TOOL CALIBRATION")
    print("="*50)

    tools = {}

    # Pen/Brush tool (for movement trails)
    tools["pen"] = list(wait_for_enter(
        "PEN/BRUSH tool (for drawing movement)"
    ))

    # Rectangle tool (for buildings)
    tools["rectangle"] = list(wait_for_enter(
        "RECTANGLE tool (for buildings)"
    ))

    # Eraser (for deaths - optional)
    print("\nEraser is optional. Press ENTER to record, or Ctrl+C to skip.")
    try:
        tools["eraser"] = list(wait_for_enter("ERASER tool (for deaths)"))
    except KeyboardInterrupt:
        print("  Skipped eraser")

    config["tools"] = tools

def calibrate_canvas(config: dict) -> None:
    """Calibrate canvas boundaries."""
    print("\n" + "="*50)
    print("CANVAS CALIBRATION")
    print("="*50)
    print("""
Record the drawable canvas area boundaries.
This maps simulation coordinates to screen positions.
""")

    top_left = wait_for_enter("TOP-LEFT corner of canvas")
    bottom_right = wait_for_enter("BOTTOM-RIGHT corner of canvas")

    config["canvas"] = {
        "top_left": list(top_left),
        "bottom_right": list(bottom_right),
        "width": bottom_right[0] - top_left[0],
        "height": bottom_right[1] - top_left[1]
    }

def save_config(config: dict) -> None:
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nConfiguration saved to: {CONFIG_FILE}")

def load_config() -> dict:
    """Load existing configuration if available."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def show_current_position():
    """Utility: continuously show mouse position."""
    print("\nMouse position tracker (Ctrl+C to stop):")
    print("Move your mouse to see coordinates.\n")
    try:
        while True:
            pos = pyautogui.position()
            print(f"\r  Position: ({pos.x:4d}, {pos.y:4d})  ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         KolourPaint Calibration Tool                     ║
╠══════════════════════════════════════════════════════════╣
║  1. Open KolourPaint and arrange your window             ║
║  2. Create a new canvas (or open existing)               ║
║  3. Run this calibration                                 ║
╚══════════════════════════════════════════════════════════╝
""")

    print("Options:")
    print("  1. Full calibration (colors, tools, canvas)")
    print("  2. Calibrate colors only")
    print("  3. Calibrate tools only")
    print("  4. Calibrate canvas only")
    print("  5. Show mouse position (helper)")
    print("  6. View current config")
    print("  q. Quit")

    choice = input("\nChoice: ").strip().lower()

    config = load_config()

    if choice == "1":
        print("\nStarting full calibration in 3 seconds...")
        print("Make sure KolourPaint is visible!")
        time.sleep(3)
        calibrate_colors(config)
        calibrate_tools(config)
        calibrate_canvas(config)
        save_config(config)

    elif choice == "2":
        time.sleep(2)
        calibrate_colors(config)
        save_config(config)

    elif choice == "3":
        time.sleep(2)
        calibrate_tools(config)
        save_config(config)

    elif choice == "4":
        time.sleep(2)
        calibrate_canvas(config)
        save_config(config)

    elif choice == "5":
        show_current_position()

    elif choice == "6":
        if config:
            print("\nCurrent configuration:")
            print(json.dumps(config, indent=2))
        else:
            print("\nNo configuration file found.")

    elif choice == "q":
        return
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()

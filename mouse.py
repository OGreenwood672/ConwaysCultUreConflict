import csv
from collections import defaultdict
from time import sleep
import pyautogui

pyautogui.FAILSAFE = True


CSV_PATH = "frontend/public/logs/updates.csv"


def load_positions(path):
    """Parse updates.csv into per-tick position lists by culture.

    Returns dict: tick -> {culture_id: [(x, y), ...]}
    """
    ticks = defaultdict(lambda: defaultdict(list))
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tick = int(row["tick"])
            culture = int(row["culture"])
            x = int(row["x"])
            y = int(row["y"])
            ticks[tick][culture].append((x, y))
    return ticks


ticks = load_positions(CSV_PATH)


for tick in sorted(ticks.keys()):
    pos = ticks[tick].get(0, [])  # culture 0
    pos2 = ticks[tick].get(1, [])  # culture 1

    pyautogui.click(60, 200, button="left")

    pyautogui.click(210, 950)
    for x, y in pos:
        pyautogui.click(650 + x * 20, 500 + y * 20, button="left")

    pyautogui.click(400, 950)
    for x, y in pos2:
        pyautogui.click(650 + x * 20, 500 + y * 20, button="left")

    sleep(2)

    pyautogui.hotkey("ctrl", "a")  # Select all
    pyautogui.press("delete")

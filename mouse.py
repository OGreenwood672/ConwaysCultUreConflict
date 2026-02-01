from time import sleep
import pyautogui

pyautogui.FAILSAFE = False


pos = [
    (87, 100),
    (89, 100),
    (100, 130),
    (102, 140),
    (150, 190),
]


pos2 = [
    (87, 200),
    (89, 200),
    (100, 230),
    (102, 240),
    (150, 290),
]


pyautogui.click(60, 200, button="left")

pyautogui.click(210, 950)

for x, y in pos:
    pyautogui.click(x, y, button="left")

pyautogui.click(400, 950)

for x, y in pos2:
    pyautogui.click(x, y, button="left")

sleep(2)

pyautogui.hotkey("ctrl", "a")  # Select all
pyautogui.press("delete")

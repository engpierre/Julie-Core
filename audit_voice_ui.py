import time
import os
import pyautogui
from julie import run_julie_query

print('[1/3] Testing Voice Latency...')
start_time = time.time()
run_julie_query('Hello Pierre! Launching the Julie desktop interface now. Voice latency test in progress.')
elapsed = time.time() - start_time
print(f'-> Voice dispatch completed in {elapsed:.2f} seconds.')

print('[2/3] Capturing Desktop UI Screenshot...')
time.sleep(2)
try:
    screenshot = pyautogui.screenshot()
    screenshot_path = r'C:\Users\Pierre\.openclaw\workspace\Julie-Core\julie_ui_audit.png'
    screenshot.save(screenshot_path)
    print(f'-> Screenshot saved to {screenshot_path}')
except Exception as e:
    print(f'-> Desktop grab note: {e}')

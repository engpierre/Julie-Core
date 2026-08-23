@echo off
cd /d "C:\Users\Pierre\.openclaw\workspace\Julie-Core"
"C:\Users\Pierre\.openclaw\workspace\Julie-Core\.venv\Scripts\python.exe" "C:\Users\Pierre\.openclaw\workspace\Julie-Core\warmup.py"
start "" "C:\Users\Pierre\.openclaw\workspace\Julie-Core\.venv\Scripts\python.exe" "C:\Users\Pierre\.openclaw\workspace\Julie-Core\app_eel.py"
ping 127.0.0.1 -n 3 >nul
start "" msedge.exe --app=http://127.0.0.1:8080/index.html

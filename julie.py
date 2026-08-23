# ==============================================================================
# GOOGLE ANTI-GRAVITY MANDATE:
# ALL FUTURE MODIFICATIONS MUST BE PRECEDING BY READING 'status.md' AND 'progress.md'.
# DO NOT ADD AGGRESSIVE PROCESS-KILLING COMMANDS OR PRE-LOAD HEAVY CONTEXT FILES.
# ==============================================================================
import sys
import os
import glob
import json
import subprocess
import threading
import builtins
import re
import ollama

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from julie.core.contracts import JulieState

STATE_FILE = Path("state/state")
_state_lock = threading.Lock()

def set_julie_state(state: JulieState) -> None:
    """Updates the file state bus atomically with thread safety."""
    with _state_lock:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(state).strip(), encoding="utf-8")

# Initialize idle state on startup
set_julie_state("idle")

from workspace_router import (
    search_obsidian_vault,
    read_vault_index,
    hermes_interface,
    openclaw_interface,
    web_search,
    augment_prompt_with_context,
)

def get_hermes_intel():
    """Reads the latest Chronos-Bolt forecast metrics via workspace_router."""
    return hermes_interface(action="read")

def check_openclaw_status():
    """Reads OpenClaw scout intel buffer via workspace_router."""
    return openclaw_interface(action="read")

def read_workspace_file(filename="MEMORY.md"):
    """Reads a specific file or Obsidian note from the workspace on demand."""
    workspace_path = r"C:\Users\Pierre\.openclaw\workspace"
    target = os.path.join(workspace_path, filename)
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                return f"[FILE {filename}]: {f.read(1500)}"
        except Exception as e:
            return f"Error reading {filename}: {e}"
    return search_obsidian_vault(filename)

def run_chronos_forecast_async(ticker: str) -> str:
    """Spawns chronos forecast in a background window via workspace_router."""
    return hermes_interface(action="dispatch", ticker=ticker)

def run_openclaw_analysis_async(target: str) -> str:
    """Triggers an OpenClaw analysis task asynchronously via workspace_router."""
    return openclaw_interface(action="dispatch", task=f"Analyze {target}")

def handle_direct_dispatches(user_text: str):
    """Intercepts launch/dispatch commands. Avoids hijacking read/status queries."""
    text_lower = user_text.lower()

    # If the user is asking for status/readings, DO NOT dispatch new background jobs!
    read_keywords = ["status", "latest", "read", "buffer", "check", "what is", "get"]
    if any(k in text_lower for k in read_keywords):
        return None  # Let augment_prompt_with_context attach the JSON buffers instead!

    # 1. Hermes Forecast Dispatch Pattern
    if ("hermes" in text_lower or "chronos" in text_lower) and ("forecast" in text_lower or "launch" in text_lower or "run" in text_lower):
        # Clean speech filler words
        clean_text = re.sub(r'(?i)\bjulie\b|\blaunch\b|\ba\b|\bhermes\b|\bchronos\b|\bforecast\b|\bfor\b|\bthe\b|\bstock\b|\brun\b', '', user_text)
        words = re.findall(r'\b[A-Za-z0-9]{1,5}\b', clean_text)
        ticker = words[0].upper() if words else "HD"
        return run_chronos_forecast_async(ticker)

    # 2. OpenClaw Analysis Dispatch Pattern
    if ("openclaw" in text_lower or "open clock" in text_lower) and ("analyze" in text_lower or "analysis" in text_lower or "scout" in text_lower):
        clean_text = re.sub(r'(?i)\bjulie\b|\bask\b|\bopenclaw\b|\bopen\b|\bclock\b|\bto\b|\brun\b|\ba\b|\bscout\b|\banalysis\b|\bon\b|\bfor\b', '', user_text)
        target = clean_text.strip() or "General Workspace"
        return run_openclaw_analysis_async(target)

    return None

# CRITICAL: Expose functions to interpreter / execution global scope
EXPOSED_TOOLS = {
    "get_hermes_intel": get_hermes_intel,
    "check_openclaw_status": check_openclaw_status,
    "read_workspace_file": read_workspace_file,
    "search_obsidian_vault": search_obsidian_vault,
    "web_search": web_search,
    "hermes_interface": hermes_interface,
    "openclaw_interface": openclaw_interface,
    "run_chronos_forecast_async": run_chronos_forecast_async,
    "run_openclaw_analysis_async": run_openclaw_analysis_async,
    "handle_direct_dispatches": handle_direct_dispatches,
    "set_julie_state": set_julie_state
}

# Bind to builtins & __main__ module to eliminate NameError during execution
for tool_name, tool_func in EXPOSED_TOOLS.items():
    setattr(builtins, tool_name, tool_func)
    if '__main__' in sys.modules:
        setattr(sys.modules['__main__'], tool_name, tool_func)

def get_hermes_status() -> str:
    """Fast, non-blocking check of Hermes Chronos-Bolt forecast buffer."""
    return get_hermes_intel()

def execute_workspace_script(script_name: str) -> str:
    """Spawns heavy workspace scripts as detached background processes."""
    set_julie_state("executing")
    workspace_dir = r"C:\Users\Pierre\.openclaw\workspace"
    script_path = os.path.join(workspace_dir, script_name)
    python_exe = os.path.join(workspace_dir, "Julie-Core", ".venv", "Scripts", "python.exe")
    
    if not os.path.exists(script_path):
        set_julie_state("idle")
        return f"Error: Script '{script_name}' not found."

    try:
        no_window = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        subprocess.Popen(
            [python_exe, script_path],
            cwd=workspace_dir,
            creationflags=no_window
        )
        return f"Successfully initiated '{script_name}' in a background process. The UI remains active."
    except Exception as e:
        return f"Failed to spawn background process: {e}"
    finally:
        set_julie_state("idle")

try:
    from interpreter import interpreter
    # 1. Configure Open Interpreter to use local Ollama instance (gemma4:26b) for SAFE CHAT ONLY
    interpreter.offline = True
    interpreter.llm.model = "ollama/gemma4:26b"
    interpreter.llm.api_base = "http://localhost:11434"
    interpreter.llm.max_tokens = 2048
    interpreter.auto_run = False  # Prevent OpenInterpreter from entering automatic script execution loops
    interpreter.safe_mode = "off"
except Exception as e:
    interpreter = None

# 2. UNIFIED SYSTEM PROMPT (ZERO CODE-EXECUTION DEPENDENCY)
BASE_SYSTEM_MESSAGE = """
You are Julie, an authentic, high-speed Jarvis-style autonomous voice assistant and spatial HUD controller for Pierre.
Always address the user simply as Pierre.
You are fast, concise, direct, and actionable (1-3 sentences maximum per answer).
You have read-only access to Pierre Quant Swarm telemetry and the Lossless Claw SQLite DAG vault.
When context is provided under '--- CONTEXT ---', read it and answer immediately and naturally.
Zero speculation: if data is missing or uncorroborated, flag the blindspot immediately.
Do NOT attempt to write or execute Python code blocks in chat.
"""

if interpreter is not None:
    try:
        interpreter.system_message = BASE_SYSTEM_MESSAGE
    except Exception:
        pass

def speak_async(text: str):
    """Non-blocking voice handler using Windows SAPI / TTS voice synthesis with COM threading safety."""
    def _speak():
        clean_text = re.sub(r'[*#`_~\[\]\(\)]', '', text).strip()
        if not clean_text:
            return
        
        co_init = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            co_init = True
        except Exception:
            pass

        try:
            set_julie_state("speaking")
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(clean_text)
        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            if co_init:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
            set_julie_state("idle")

    threading.Thread(target=_speak, daemon=True).start()

def run_julie_query(prompt: str):
    set_julie_state("thinking")
    # Check for direct dispatches first!
    dispatch_response = handle_direct_dispatches(prompt)
    if dispatch_response:
        set_julie_state("executing")
        print(f"\n[Julie Core] Direct dispatch intercepted: '{prompt}' -> {dispatch_response}")
        speak_async(dispatch_response)
        return dispatch_response

    augmented_prompt = augment_prompt_with_context(prompt)
    print(f"\n[Julie Core] Processing query: '{prompt}'")
    
    # 1. Direct Ollama Chat API (Fast, pure text, zero execution loop or stdin deadlock)
    try:
        response = ollama.chat(
            model="gemma4:26b",
            messages=[
                {"role": "system", "content": BASE_SYSTEM_MESSAGE},
                {"role": "user", "content": augmented_prompt}
            ]
        )
        msg_content = response.get("message", {}).get("content", "")
        if msg_content:
            speak_async(msg_content)
            return msg_content
    finally:
        set_julie_state("idle")

    # 2. Fallback: OpenInterpreter (if available)
    if interpreter is not None:
        try:
            response = interpreter.chat(augmented_prompt)
            if response:
                last_msg = response[-1].get("content", "") if isinstance(response, list) else str(response)
                speak_async(last_msg)
                return last_msg
        except Exception as e:
            print(f"[Interpreter Error] {e}")

    set_julie_state("idle")
    return "Operational. Ready for directive."

chat_with_julie = run_julie_query

if __name__ == "__main__":
    print("[JULIE CORE] Starting single-window Eel UI on port 8080...")
    try:
        import eel
        eel.init("web")
        eel.start("index.html", mode="chrome", port=8080, host="localhost", block=True)
    except Exception as e:
        print(f"[JULIE ERROR] Eel startup failed: {e}")

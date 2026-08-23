"""
Julie Package Initialization
============================
Exports core contracts, state bus primitives, and query dispatchers.
"""

import sys
import threading
import importlib.util
from pathlib import Path
from julie.core.contracts import JulieState, VoiceIntentPayload

STATE_FILE = Path("state/state")
_state_lock = threading.Lock()


def set_julie_state(state: JulieState) -> None:
    """Updates the file state bus atomically with thread safety."""
    with _state_lock:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(state).strip(), encoding="utf-8")


_julie_main = None


def _get_julie_main():
    global _julie_main
    if _julie_main is None:
        julie_py = Path(__file__).resolve().parent.parent / "julie.py"
        spec = importlib.util.spec_from_file_location("julie_runner", julie_py)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _julie_main = module
    return _julie_main


def run_julie_query(prompt: str) -> str:
    """Invokes Julie-Core Open Interpreter engine."""
    mod = _get_julie_main()
    if mod and hasattr(mod, "run_julie_query"):
        return mod.run_julie_query(prompt)
    return "Julie engine runner unavailable."


def speak_async(text: str) -> None:
    """Non-blocking voice synthesis."""
    mod = _get_julie_main()
    if mod and hasattr(mod, "speak_async"):
        mod.speak_async(text)


def handle_direct_dispatches(prompt: str):
    """Direct dispatcher evaluation."""
    mod = _get_julie_main()
    if mod and hasattr(mod, "handle_direct_dispatches"):
        return mod.handle_direct_dispatches(prompt)
    return None


__all__ = [
    "JulieState",
    "VoiceIntentPayload",
    "set_julie_state",
    "run_julie_query",
    "speak_async",
    "handle_direct_dispatches",
    "STATE_FILE",
]

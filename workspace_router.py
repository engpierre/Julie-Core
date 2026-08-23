"""
Julie Workspace Router: Deterministic Memory & Decoupled Telemetry Engine
========================================================================
Provides deterministic memory priming via VAULT-INDEX.md and decoupled,
read-only telemetry interfaces into Hermes Chronos and OpenClaw Swarm buffers.
"""

import sys
import os
import json
import subprocess
import threading
from typing import Dict, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')

WORKSPACE_DIR = r"C:\Users\Pierre\.openclaw\workspace"
OBSIDIAN_ROOTS = [
    r"C:\Users\Pierre\Documents\ObsidianVault",
    WORKSPACE_DIR,
]


def ensure_default_buffers() -> None:
    """Ensures default buffer JSON files exist for read operations."""
    chronos_buf = os.path.join(WORKSPACE_DIR, "chronos_intel_buffer.json")
    scout_buf = os.path.join(WORKSPACE_DIR, "scout_intel_buffer.json")
    
    if not os.path.exists(chronos_buf):
        try:
            default_chronos = {
                "status": "INITIALIZED",
                "timestamp": "2026-07-29T00:00:00Z",
                "active_ticker": "HD",
                "recommendation": "NEUTRAL",
                "sigma_bounds": {"lower": 0, "upper": 0}
            }
            with open(chronos_buf, "w", encoding="utf-8") as f:
                json.dump(default_chronos, f, indent=2)
        except Exception:
            pass

    if not os.path.exists(scout_buf):
        try:
            default_scout = {
                "status": "INITIALIZED",
                "timestamp": "2026-07-29T00:00:00Z",
                "active_task": "Idle",
                "scout_insights": ["OpenClaw scout initialized and awaiting tasks."]
            }
            with open(scout_buf, "w", encoding="utf-8") as f:
                json.dump(default_scout, f, indent=2)
        except Exception:
            pass


ensure_default_buffers()


def read_vault_index() -> str:
    """Deterministic lookup of primary VAULT-INDEX.md with zero directory sweep overhead."""
    for root_dir in OBSIDIAN_ROOTS:
        index_path = os.path.join(root_dir, "VAULT-INDEX.md")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(600).strip()
            except Exception:
                continue
    return "- User: Pierre (AI Architect)\n- Directives: Quant Swarm & Julie Voice Assistant"


def search_obsidian_vault(query_keywords: str = "") -> str:
    """[DEPRECATED] Directs caller to deterministic VAULT-INDEX.md."""
    return read_vault_index()


def web_search(query: str) -> str:
    """Executes a lightweight web search and returns top snippets."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(query, max_results=2))
        if results:
            return "\n".join([f"- {r['title']}: {r['body'][:150]}" for r in results])
    except Exception:
        pass

    try:
        import urllib.request
        import urllib.parse
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            html = response.read().decode('utf-8')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            snippets = [a.text.strip() for a in soup.find_all('a', class_='result__snippet')[:2] if a.text.strip()]
            if snippets:
                return "\n".join(snippets[:2])
    except Exception:
        pass

    return "No search results found."


def hermes_interface(action: str = "read", ticker: str = "HD") -> str:
    """Handles Hermes buffer reading (strictly read-only) and background task dispatch."""
    buffer_path = os.path.join(WORKSPACE_DIR, "chronos_intel_buffer.json")
    
    if action == "dispatch":
        ticker_clean = ticker.strip().upper() or "HD"
        def _run():
            python_exe = os.path.join(WORKSPACE_DIR, "chronos-swarm", ".venv", "Scripts", "python.exe")
            swarm_script = os.path.join(WORKSPACE_DIR, "chronos-swarm", "run_swarm.py")
            if not os.path.exists(python_exe):
                python_exe = "python"
            cmd = [python_exe, swarm_script, "--ticker", ticker_clean]
            no_window = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            subprocess.Popen(cmd, cwd=os.path.dirname(swarm_script), creationflags=no_window)
        threading.Thread(target=_run, daemon=True).start()
        return f"Hermes forecast dispatched for ticker {ticker_clean} in background."
        
    # Strictly read-only buffer lookup
    if os.path.exists(buffer_path):
        try:
            with open(buffer_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return f"Hermes [{data.get('active_ticker', 'HD')}]: {data.get('recommendation', 'HOLD')} | Sigma: {data.get('sigma_bounds', {})}"
        except Exception as e:
            return f"Hermes buffer read notice: {e}"
    return "Hermes intel buffer unavailable."


def openclaw_interface(action: str = "read", task: str = "General Analysis") -> str:
    """Handles OpenClaw scout buffer reading (strictly read-only) and background task dispatch."""
    buffer_path = os.path.join(WORKSPACE_DIR, "scout_intel_buffer.json")
    
    if action == "dispatch":
        def _run():
            cmd = ["cmd.exe", "/c", "openclaw", "run", task]
            no_window = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            subprocess.Popen(cmd, creationflags=no_window)
        threading.Thread(target=_run, daemon=True).start()
        return f"OpenClaw task '{task}' dispatched to background worker."
        
    # Strictly read-only buffer lookup
    if os.path.exists(buffer_path):
        try:
            with open(buffer_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                insights = data.get("scout_insights", ["Standby"])
                first_insight = insights[0] if insights else "Standby"
                return f"Scout [{data.get('active_task', 'Idle')}]: {first_insight[:140]}"
        except Exception as e:
            return f"Scout buffer read notice: {e}"
    return "OpenClaw scout buffer unavailable."


def augment_prompt_with_context(user_text: str) -> str:
    """Deterministic prompt context injection (< 250 tokens) from VAULT-INDEX and active telemetry."""
    text_lower = user_text.lower()
    injected_lines = []

    # 1. Deterministic Vault Index Memory Priming (Always Included as Baseline Identity & Projects, ~50 tokens)
    injected_lines.append(f"[VAULT-INDEX]:\n{read_vault_index()}")

    # 2. Hermes / Chronos Telemetry
    hermes_keywords = ["hermes", "chronos", "forecast", "prediction", "intel", "buffer", "stock", "stocks", "market", "trade"]
    if any(k in text_lower for k in hermes_keywords):
        injected_lines.append(f"[TELEMETRY]: {hermes_interface(action='read')}")

    # 3. OpenClaw Swarm Telemetry
    scout_keywords = ["openclaw", "scout", "swarm", "recon", "status", "agent", "agents", "system"]
    if any(k in text_lower for k in scout_keywords):
        injected_lines.append(f"[SWARM]: {openclaw_interface(action='read')}")

    # 4. Web Search
    search_keywords = ["search", "weather", "news", "google", "lookup", "find out"]
    if any(k in text_lower for k in search_keywords):
        snippets = web_search(user_text)
        injected_lines.append(f"[WEB]:\n{snippets}")

    compact_context = "\n".join(injected_lines)
    return f"{user_text}\n\n--- CONTEXT ---\n{compact_context}"

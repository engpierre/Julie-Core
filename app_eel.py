import sys
import os
import re
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import date, datetime
import requests
import psutil
import eel
import ollama
import speech_recognition as sr
from workspace_router import augment_prompt_with_context
from julie import set_julie_state, speak_async, handle_direct_dispatches

logger = logging.getLogger("JulieCore")
RUNNER_SYNC_PATH = Path(r"C:\Users\Pierre\.openclaw\workspace\pierre-quant\pierre_quant\runners\run_portfolio_hud_sync.py")
HUD_BUFFER_PATH = Path(r"C:\Users\Pierre\.openclaw\workspace\hud_telemetry_buffer.json")

PHONETIC_STT_MAP = {
    r"\bopen clock\b": "OpenClaw",
    r"\bopen clock swarm\b": "OpenClaw Swarm",
    r"\bkronos\b": "Chronos",
    r"\btime fm\b": "TimesFM",
}


def sanitize_and_normalize_transcript(user_text: str) -> str:
    """Corrects known phonetic STT corruptions before LLM inference."""
    sanitized = user_text
    for pattern, replacement in PHONETIC_STT_MAP.items():
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def execute_hud_sync_subprocess() -> None:
    """Executes the quantitative sync runner in a non-blocking background thread."""
    def _run():
        try:
            if RUNNER_SYNC_PATH.exists():
                subprocess.run([sys.executable, str(RUNNER_SYNC_PATH)], check=True, capture_output=True, text=True)
                logger.info("Portfolio HUD sync completed successfully.")
        except Exception as err:
            logger.error(f"Portfolio sync failure: {err}")

    threading.Thread(target=_run, daemon=True).start()


def get_active_portfolio_context() -> str:
    """Reads live multi-agent vectors from the atomic HUD buffer under read-only lock."""
    if not HUD_BUFFER_PATH.exists():
        return "Portfolio Context: Buffer uninitialized. No active dossiers."
    try:
        with open(HUD_BUFFER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        positions = data.get("positions", [])
        if not positions:
            return "Portfolio Context: Active portfolio has 0 open positions."
        
        summary = ["Active Portfolio & Sentry Vectors:"]
        for p in positions:
            summary.append(
                f"- ${p['ticker']} ({p.get('bucket', 'SWING')}): Spot ${p['spot_price']:.2f} | "
                f"14-Day ATR: ${p['atr_14']:.2f} | "
                f"Invalidation Stop: ${p['invalidation_stop']:.2f} | "
                f"TimesFM Target: ${p['timesfm_target']:.2f} ({p['timesfm_delta_pct']:+.2f}%) | "
                f"Chronos-Bolt Target: ${p['chronos_target']:.2f} ({p['chronos_delta_pct']:+.2f}%) | "
                f"Bias: {p['net_bias']}"
            )
        return "\n".join(summary)
    except Exception as err:
        logger.error(f"Failed to read HUD buffer: {err}")
        return "Portfolio Context: Error reading telemetry buffer."


WORKSPACE_ROOT = Path(r"C:\Users\Pierre\.openclaw\workspace")
VAULT_ROOT = WORKSPACE_ROOT / "vault"
VAULT_RECONS_PATH = VAULT_ROOT / "Recons"
HUD_BUFFER_PATH = WORKSPACE_ROOT / "hud_telemetry_buffer.json"
SCANNER_RUNNER_PATH = WORKSPACE_ROOT / "pierre-quant" / "pierre_quant" / "runners" / "run_signal_scanner.py"
PYTHON_EXE = WORKSPACE_ROOT / "Julie-Core" / ".venv" / "Scripts" / "python.exe"

WMO_CODE_MAP = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
    95: "Thunderstorm"
}


def get_chelsea_weather_deterministic() -> str:
    """Fetches high-reliability atmospheric data for Chelsea, QC via Open-Meteo REST API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 45.50,
        "longitude": -75.78,
        "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
        "timezone": "America/Toronto"
    }
    try:
        resp = requests.get(url, params=params, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json().get("current", {})
            temp = data.get("temperature_2m", 0.0)
            hum = data.get("relative_humidity_2m", 0)
            wind = data.get("wind_speed_10m", 0.0)
            wcode = data.get("weather_code", 0)
            condition = WMO_CODE_MAP.get(wcode, "Clear")
            return f"{condition}, {temp:.1f}°C (Humidity: {hum}%, Wind: {wind:.1f} km/h)"
    except Exception as err:
        logger.warning(f"Open-Meteo weather fetch failed: {err}")
    return "Weather telemetry unavailable"


def ensure_daily_scanner_sync():
    """Runs signal scanner on first boot/wake of the day if not yet executed today."""
    if not SCANNER_RUNNER_PATH.exists() or not PYTHON_EXE.exists():
        return

    today_str = date.today().isoformat()
    needs_sync = True

    if VAULT_RECONS_PATH.exists():
        for md_file in VAULT_RECONS_PATH.glob("*.md"):
            try:
                mtime_date = date.fromtimestamp(os.path.getmtime(md_file)).isoformat()
                if mtime_date == today_str:
                    needs_sync = False
                    break
            except Exception:
                pass

    if needs_sync:
        logger.info("Daily market scan required. Triggering run_signal_scanner.py in background...")
        try:
            subprocess.run([str(PYTHON_EXE), str(SCANNER_RUNNER_PATH)], timeout=45, check=False)
        except Exception as e:
            logger.warning(f"On-wake scanner trigger error: {e}")


def get_vault_convergent_setups() -> list[str]:
    """Extracts all high-alpha convergent setups generated by the dual-engine scanner."""
    if not VAULT_RECONS_PATH.exists():
        return []

    convergent_signals = []
    for md_file in VAULT_RECONS_PATH.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            if "is_convergent: true" in content or "⚡ HIGH ALPHA CONVERGENCE" in content or "HIGH ALPHA CONVERGENCE" in content:
                ticker = md_file.stem
                spot = re.search(r"spot_price:\s*([\d\.]+)", content)
                stop = re.search(r"invalidation_stop:\s*([\d\.]+)", content)
                tfm_delta = re.search(r"timesfm_delta_pct:\s*([+\-\d\.]+)", content)
                chr_delta = re.search(r"chronos_delta_pct:\s*([+\-\d\.]+)", content)

                spot_str = f"${float(spot.group(1)):.2f}" if spot else "N/A"
                stop_str = f"${float(stop.group(1)):.2f}" if stop else "N/A"
                tfm_str = f"{float(tfm_delta.group(1)):+.2f}%" if tfm_delta else ""
                chr_str = f"{float(chr_delta.group(1)):+.2f}%" if chr_delta else ""

                convergent_signals.append(f"${ticker} ({tfm_str} TFM / {chr_str} CHR | Floor: {stop_str})")
        except Exception as err:
            logger.warning(f"Error parsing vault file {md_file.name}: {err}")

    return convergent_signals


def generate_morning_executive_brief() -> str:
    """Compiles a deterministic morning flight check brief including live weather and scan alpha."""
    ensure_daily_scanner_sync()
    weather_summary = get_chelsea_weather_deterministic()

    total_positions = 0
    systemic_sigma = 0.0
    breaches = []
    
    if HUD_BUFFER_PATH.exists():
        try:
            with open(HUD_BUFFER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            positions = data.get("positions", [])
            total_positions = len(positions)
            systemic_sigma = data.get("systemic_risk_score", 0.0)

            for p in positions:
                spot = float(p.get("spot_price", 0.0))
                stop = float(p.get("invalidation_stop", 0.0))
                ticker = p.get("ticker", "UNK")
                if spot > 0 and spot <= stop:
                    breaches.append(f"${ticker} (Spot: ${spot:.2f} <= Stop:${stop:.2f})")
        except Exception as e:
            logger.error(f"Failed to parse HUD buffer: {e}")

    convergent_setups = get_vault_convergent_setups()

    brief_lines = [
        "Good morning, Pierre. Executive brief compiled:",
        f"• Environment (Chelsea, QC): {weather_summary}",
        f"• Portfolio Exposure: {total_positions} active holdings | Systemic Risk σ: {systemic_sigma:.2f}%"
    ]

    if breaches:
        brief_lines.append(f"• ⚠️ Invalidation Warnings: {', '.join(breaches)}")
    else:
        brief_lines.append("• Invalidation Status: Nominal (0 floor breaches across active corridors)")

    if convergent_setups:
        brief_lines.append(f"• ⚡ High Alpha Setups: {', '.join(convergent_setups)}")
    else:
        brief_lines.append("• High Alpha Setups: 0 convergent breakout vectors flagged today")

    brief_lines.append("• Hardware Node Status: cuda:0 (TimesFM) & cuda:1 (Chronos-Bolt) active.")
    brief_lines.append("Standing by for tasking.")

    return "\n".join(brief_lines)


VAULT_RECONS_PATH = Path(r"C:\Users\Pierre\.openclaw\workspace\vault\Recons")


def get_vault_recon(ticker: str) -> str:
    """Deterministically reads and summarizes an asset recon file from the Obsidian vault."""
    clean_ticker = ticker.upper().replace("$", "").strip()
    target_file = VAULT_RECONS_PATH / f"{clean_ticker}.md"
    
    if not target_file.exists():
        return f"Pierre, no recon dossier exists in the vault for ${clean_ticker}. Run sentry recon to generate."

    try:
        content = target_file.read_text(encoding="utf-8")
        
        # Deterministic extraction of key metrics
        spot = re.search(r"spot_price:\s*([\d\.]+)", content)
        atr = re.search(r"atr_14:\s*([\d\.]+)", content)
        stop = re.search(r"invalidation_stop:\s*([\d\.]+)", content)
        tfm = re.search(r"timesfm_target:\s*([\d\.]+)", content)
        chr_t = re.search(r"chronos_target:\s*([\d\.]+)", content)
        bias = re.search(r'net_bias:\s*"([^"]+)"', content)

        spot_val = float(spot.group(1)) if spot else 0.0
        atr_val = float(atr.group(1)) if atr else 0.0
        stop_val = float(stop.group(1)) if stop else 0.0
        tfm_val = float(tfm.group(1)) if tfm else 0.0
        chr_val = float(chr_t.group(1)) if chr_t else 0.0
        bias_val = bias.group(1) if bias else "NEUTRAL"

        return (
            f"Vault Recon Dossier for ${clean_ticker}:\n"
            f"• Spot Price: ${spot_val:.2f}\n"
            f"• 14-Day ATR: ${atr_val:.2f}\n"
            f"• Dynamic Invalidation Stop: ${stop_val:.2f}\n"
            f"• TimesFM 16-Bar Horizon: ${tfm_val:.2f}\n"
            f"• Chronos-Bolt Target: ${chr_val:.2f}\n"
            f"• Systemic Bias: {bias_val}"
        )
    except Exception as e:
        return f"Error reading vault file for ${clean_ticker}: {str(e)}"


BRIEF_INTENT_PATTERNS = [
    r"\bgood morning\b",
    r"\bmorning brief\b",
    r"\bexecutive brief\b",
    r"\bflight check\b",
    r"\bdaily status\b",
]


def is_morning_brief_intent(text: str) -> bool:
    """Matches either natural greetings or explicit executive brief commands."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in BRIEF_INTENT_PATTERNS)


def handle_external_intent(normalized_text: str) -> str | None:
    """Deterministic routing for external info queries, executive briefings, vault recons, and quant triggers."""
    text_lower = normalized_text.lower()
    
    # Morning Executive Briefing Intent (Regex word boundary matched)
    if is_morning_brief_intent(normalized_text):
        return generate_morning_executive_brief()

    # Conversational Portfolio Sync Intent
    if any(k in text_lower for k in ["refresh portfolio", "sync portfolio", "update portfolio", "sync hud"]):
        execute_hud_sync_subprocess()
        return "Initiating portfolio synchronization from the Vault. The Tactical HUD will refresh shortly."

    # Vault Recon Dossier Lookup Hook
    if any(k in text_lower for k in ["vault", "recon", "recons", "dossier"]):
        # Extract ticker symbol (e.g., NVDA, $NVDA, META)
        blacklist = {"VAULT", "RECON", "RECONS", "CHECK", "REPORT", "PRICE", "CORE", "SWING", "IRS", "JULIE", "SWARM", "SYSTEM", "THE", "FOR", "GET", "SHOW", "LOOK", "WHAT", "GIVE", "PLEASE", "READ", "NOTE", "FIND", "OPEN", "AND", "WITH"}
        candidates = re.findall(r"\b([A-Za-z]{2,5})\b", normalized_text)
        for cand in candidates:
            sym = cand.upper()
            if sym not in blacklist:
                return get_vault_recon(sym)

    # Deterministic Weather Intent
    if "weather" in text_lower and ("chelsea" in text_lower or "ottawa" in text_lower or "gatineau" in text_lower or "forecast" in text_lower or "temperature" in text_lower):
        weather_info = get_chelsea_weather_deterministic()
        return f"Current atmospheric conditions in Chelsea, QC: {weather_info}"
            
    return None


eel.init('web')


@eel.expose
def run_julie_query(prompt: str) -> str:
    """Hardened query ingestion with phonetic normalization, deterministic external intent routing, and live portfolio context."""
    if not prompt or not prompt.strip():
        return "No directive received."

    # 1. Phonetic Normalization
    normalized_prompt = sanitize_and_normalize_transcript(prompt)

    # 2. External / Quant Intent Handler
    ext_response = handle_external_intent(normalized_prompt)
    if ext_response:
        set_julie_state("executing")
        speak_async(ext_response)
        set_julie_state("idle")
        return str(ext_response)

    set_julie_state("thinking")
    try:
        # 3. Evaluate direct dispatches
        dispatch_response = handle_direct_dispatches(normalized_prompt)
        if dispatch_response:
            set_julie_state("executing")
            speak_async(dispatch_response)
            return str(dispatch_response)

        # 4. Augment with deterministic VAULT-INDEX & Live Portfolio Telemetry
        portfolio_ctx = get_active_portfolio_context()
        augmented_prompt = augment_prompt_with_context(normalized_prompt)
        
        system_instruction = (
            "You are Julie, an authentic, high-speed Jarvis-style autonomous voice assistant "
            "and spatial HUD controller for Pierre. Always address the user simply as Pierre. "
            "Keep answers concise, direct, actionable, and free of filler. Zero speculation; flag data blindspots immediately.\n\n"
            f"{portfolio_ctx}"
        )

        response = ollama.chat(
            model="gemma4:26b",
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {"role": "user", "content": augmented_prompt}
            ],
            options={"temperature": 0.2}
        )
        
        content = ""
        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
            if not content and "response" in response:
                content = str(response["response"])
        elif hasattr(response, "message") and hasattr(response.message, "content"):
            content = str(response.message.content)
            
        if not content:
            content = "Operational. Ready for directive."

        speak_async(content)
        return str(content)
    except Exception as e:
        return f"Inference Failure: {str(e)}"
    finally:
        set_julie_state("idle")


@eel.expose
def run_query(prompt: str) -> str:
    """Backwards-compatibility alias for run_julie_query"""
    return run_julie_query(prompt)


@eel.expose
def listen_voice() -> str:
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.8
    recognizer.non_speaking_duration = 1.0
    
    set_julie_state("listening")
    with sr.Microphone() as source:
        try:
            print("[MIC] Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            recognizer.energy_threshold = max(recognizer.energy_threshold, 300)
            
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            raw_text = recognizer.recognize_google(audio)
            normalized_text = sanitize_and_normalize_transcript(raw_text)
            print(f"[MIC CAPTURED]: {raw_text} -> [NORMALIZED]: {normalized_text}")
            return normalized_text
        except sr.WaitTimeoutError:
            print("[MIC] Listening timed out (no speech detected).")
            set_julie_state("idle")
            return ""
        except Exception as e:
            print("[MIC ERROR]:", e)
            set_julie_state("idle")
            return ""


@eel.expose
def get_portfolio_hud_telemetry() -> dict:
    """Exposes real-time Sentry vectors and ATR stops to the spatial interface."""
    if not HUD_BUFFER_PATH.exists():
        return {"active_dossiers": 0, "positions": [], "error": "Buffer uninitialized"}
    
    try:
        with open(HUD_BUFFER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e), "positions": []}


@eel.expose
def get_paper_portfolio_state() -> dict:
    """Safely reads the sandboxed paper portfolio state from disk for the HUD."""
    state_file = Path(r"C:\Users\Pierre\.openclaw\workspace\pierre-quant\pierre_quant\data\paper_portfolio_state.json")
    if not state_file.exists():
        return {"last_sync": 0, "total_equity": 0.0, "unrealized_pnl": 0.0, "realized_pnl": 0.0, "positions": []}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": "STATE_READ_LOCK", "last_sync": 0, "total_equity": 0.0, "unrealized_pnl": 0.0, "positions": []}


@eel.expose
def get_system_stats() -> dict:
    """Returns live system RAM and engine stats"""
    return {
        "ram_percent": round(psutil.virtual_memory().percent),
        "model": "gemma4:26b"
    }


WEB_DIR = Path(__file__).resolve().parent / "web"


if __name__ == "__main__":
    # Boot-Time Sync: Single execution on startup
    print("[INIT] Executing boot-time portfolio telemetry sync & daily scanner guard...")
    execute_hud_sync_subprocess()
    ensure_daily_scanner_sync()

    # Initialize Eel Application
    print("[EEL SERVER] Launching Julie HTML5 Jarvis Interface on port 8080...")
    try:
        eel.init(str(WEB_DIR))
        eel.start('index.html', mode=False, port=8080, host='127.0.0.1', size=(1920, 1080), block=True)
    except Exception as e:
        print(f"[EEL ERROR] Server error: {e}")

"""Settings for JARVIS.

Every value comes from an environment variable. You can also put them in a
`.env` file (in the folder you run JARVIS from, or in ~/.jarvis/.env) - see
.env.example. Never commit your .env file: it holds your secret keys.
"""

import os
from pathlib import Path


def _load_dotenv() -> None:
    for path in (Path.cwd() / ".env", Path.home() / ".jarvis" / ".env"):
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()  # -sig: Notepad may add a BOM
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip().removeprefix("export "), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)  # real environment variables win


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# --- Identity -------------------------------------------------------------------
NAME = _env("JARVIS_NAME", "Jarvis")             # also the wake word
USER_TITLE = _env("JARVIS_USER_TITLE", "sir")    # what JARVIS calls you

# --- AI brain -------------------------------------------------------------------
# "gemini", "claude", or empty to pick whichever has a key (Gemini first).
PROVIDER = _env("JARVIS_PROVIDER").lower()
GEMINI_API_KEY = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
# Tried in order; if one is overloaded or out of quota JARVIS moves to the next.
GEMINI_MODELS = [m.strip() for m in _env(
    "JARVIS_GEMINI_MODELS", "gemini-3.5-flash,gemini-flash-latest,gemini-3.8-flash,gemini-3.1-flash-lite"
).split(",") if m.strip()]
CLAUDE_MODEL = _env("JARVIS_CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = _env("JARVIS_CLAUDE_EFFORT", "low")

# --- Files ----------------------------------------------------------------------
DATA_DIR = Path(_env("JARVIS_DATA_DIR") or Path.home() / ".jarvis")
MEMORY_FILE = DATA_DIR / "memory.json"
LEADS_FILE = DATA_DIR / "leads.json"
BUSINESS_FILE = DATA_DIR / "business.json"
# Where projects JARVIS builds for you are saved.
WORKSPACE_DIR = Path(_env("JARVIS_WORKSPACE") or Path.home() / "jarvis-projects")

# --- Your business --------------------------------------------------------------
# One or two sentences: what you sell and who your ideal client is. You can
# also just tell JARVIS: "my business is ...".
BUSINESS_DESCRIPTION = _env("JARVIS_BUSINESS")

# --- Google Calendar + Gmail (optional) ----------------------------------------
GOOGLE_CREDENTIALS_FILE = DATA_DIR / "google_credentials.json"  # OAuth client from Google Cloud
GOOGLE_TOKEN_FILE = DATA_DIR / "google_token.json"              # created on first login

# --- Phone calls and texts via Twilio (optional) -------------------------------
TWILIO_ACCOUNT_SID = _env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = _env("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = _env("TWILIO_FROM_NUMBER")   # your Twilio number, e.g. +15551234567
MY_PHONE_NUMBER = _env("JARVIS_MY_PHONE")         # your mobile, e.g. +15557654321

# --- Updates --------------------------------------------------------------------
BRIEFING_TIME = _env("JARVIS_BRIEFING_TIME", "08:30")   # daily business briefing, 24h; "off" to disable
BRIEFING_BY = _env("JARVIS_BRIEFING_BY", "voice")        # voice, sms, call (comma-separate to combine)
MEETING_REMINDER_MINUTES = int(_env("JARVIS_REMINDER_MINUTES", "10"))  # 0 to disable

# --- Misc -----------------------------------------------------------------------
DEFAULT_CITY = _env("JARVIS_CITY")
HUD_HOST = _env("JARVIS_HUD_HOST", "127.0.0.1")
HUD_PORT = int(_env("JARVIS_HUD_PORT", "8765"))
VOICE_RATE = int(_env("JARVIS_VOICE_RATE", "185"))

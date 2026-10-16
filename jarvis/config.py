"""Settings for JARVIS. Every value can be overridden with an environment variable."""

import os
from pathlib import Path

# Name the assistant answers to (the wake word) and what it calls you.
NAME = os.environ.get("JARVIS_NAME", "Jarvis")
USER_TITLE = os.environ.get("JARVIS_USER_TITLE", "sir")

# Claude model behind general conversation. Commands JARVIS knows locally
# (time, weather, opening sites...) never call the API.
MODEL = os.environ.get("JARVIS_MODEL", "claude-opus-5-5")
# Low effort keeps spoken replies quick; raise to "medium"/"high" for harder questions.
EFFORT = os.environ.get("JARVIS_EFFORT", "low")

# Where notes ("remember that...") are stored between runs.
DATA_DIR = Path(os.environ.get("JARVIS_DATA_DIR", Path.home() / ".jarvis"))
MEMORY_FILE = DATA_DIR / "memory.json"

# Default city for weather when none is spoken. Empty = let wttr.in guess from your IP.
DEFAULT_CITY = os.environ.get("JARVIS_CITY", "")

# Web HUD server.
HUD_HOST = os.environ.get("JARVIS_HUD_HOST", "127.0.0.1")
HUD_PORT = int(os.environ.get("JARVIS_HUD_PORT", "8765"))

# Text-to-speech speaking rate (words per minute) for terminal voice mode.
VOICE_RATE = int(os.environ.get("JARVIS_VOICE_RATE", "185"))

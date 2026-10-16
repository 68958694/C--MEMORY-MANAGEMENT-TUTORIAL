"""Things JARVIS can do on your computer.

Each skill is a plain function returning a sentence to speak. `handle_local`
matches common voice commands directly (fast, works offline, free); `TOOLS`
(in tools.py) exposes the same skills to the AI so it can use them for
anything phrased differently.
"""

import json
import platform
import random
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime

from jarvis import config, memory

SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "maps": "https://maps.google.com",
    "amazon": "https://www.amazon.com",
}

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, walks up to two tables and asks: may I join you?",
    "Why did the C programmer get kicked out of school? He kept forgetting to free his memory.",
    "I asked the Wi-Fi for a joke, but the connection was too weak to deliver the punchline.",
]

_HTTP_HEADERS = {"User-Agent": "JARVIS-assistant/1.0"}


def _fetch(url: str, timeout: float = 8.0) -> bytes:
    req = urllib.request.Request(url, headers=_HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# --------------------------------------------------------------------------- skills


def tell_time() -> str:
    return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}, {config.USER_TITLE}."


def tell_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


def open_website(target: str) -> str:
    target = target.strip().lower().rstrip(".")
    url = SITES.get(target)
    if url is None:
        if re.fullmatch(r"[\w-]+(\.[\w-]+)+(/\S*)?", target):
            url = target if target.startswith("http") else f"https://{target}"
        else:
            return google_search(target)
    webbrowser.open(url)
    return f"Opening {target}."


def google_search(query: str) -> str:
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
    return f"Here's what I found for {query} on Google."


def youtube_search(query: str) -> str:
    webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query))
    return f"Playing {query} on YouTube."


def wikipedia_summary(topic: str) -> str:
    title = urllib.parse.quote(topic.strip().replace(" ", "_"))
    try:
        data = json.loads(_fetch(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"))
    except Exception:
        return f"I couldn't find {topic} on Wikipedia."
    extract = data.get("extract", "")
    if not extract:
        return f"I couldn't find {topic} on Wikipedia."
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    return " ".join(sentences[:2])


def weather(city: str = "") -> str:
    city = city.strip() or config.DEFAULT_CITY
    try:
        report = _fetch(f"https://wttr.in/{urllib.parse.quote(city)}?format=%l:+%C,+%t,+feels+like+%f")
        text = report.decode("utf-8").strip()
    except Exception:
        return "I can't reach the weather service right now."
    return text.replace("+", "plus ").replace("°C", " degrees Celsius").replace("°F", " degrees Fahrenheit")


def system_status() -> str:
    try:
        import psutil
    except ImportError:
        return f"Running {platform.system()} {platform.release()} on Python {platform.python_version()}."
    parts = [
        f"CPU at {psutil.cpu_percent(interval=0.5):.0f} percent",
        f"memory at {psutil.virtual_memory().percent:.0f} percent",
    ]
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None:
        parts.append(f"battery at {battery.percent:.0f} percent{' and charging' if battery.power_plugged else ''}")
    return "All systems online. " + ", ".join(parts) + "."


def open_app(name: str) -> str:
    name = name.strip()
    try:
        if sys.platform.startswith("win"):
            # `start` resolves names like "notepad", "calc", "spotify" through the shell.
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            exe = shutil.which(name) or shutil.which(name.lower().replace(" ", "-"))
            if exe is None:
                return f"I couldn't find an application called {name}."
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return f"I couldn't open {name}."
    return f"Opening {name}."


def open_path(path) -> None:
    """Open a file or folder with the system's default app."""
    if sys.platform.startswith("win"):
        import os
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remember_note(note: str) -> str:
    memory.remember(note)
    return "Noted. I'll remember that."


def recall_notes() -> str:
    notes = memory.recall()
    if not notes:
        return "You haven't asked me to remember anything yet."
    return "You asked me to remember: " + "; ".join(notes) + "."


def tell_joke() -> str:
    return random.choice(JOKES)


# --------------------------------------------------------------------------- local command router

# (pattern, handler) pairs tried in order. Named groups become handler arguments.
_COMMANDS = [
    (r"\b(what(?:'s| is) the time|what time is it|current time)\b", lambda m: tell_time()),
    (r"\b(what(?:'s| is) the date|what day is (?:it|today)|today'?s date)\b", lambda m: tell_date()),
    (r"^(?:play|youtube)\s+(?P<q>.+?)(?:\s+on youtube)?$", lambda m: youtube_search(m["q"])),
    (r"^(?:search|google)\s+(?:for\s+)?(?P<q>.+?)(?:\s+on google)?$", lambda m: google_search(m["q"])),
    (r"^(?:who|what) (?:is|was|are) (?P<q>.+)$", lambda m: _lookup(m["q"])),
    (r"^(?:wikipedia|tell me about)\s+(?P<q>.+)$", lambda m: wikipedia_summary(m["q"])),
    (r"\bweather(?: in| for| at)?\s*(?P<city>[a-z .'-]*)$", lambda m: weather(m["city"])),
    (r"^open\s+(?P<t>.+)$", lambda m: _open_anything(m["t"])),
    (r"^(?:launch|start)\s+(?P<t>.+)$", lambda m: open_app(m["t"])),
    (r"\b(system status|status report|how(?:'s| is) (?:my|the) (?:system|computer|pc))\b",
     lambda m: system_status()),
    (r"^remember(?: that)?\s+(?P<n>.+)$", lambda m: remember_note(m["n"])),
    (r"\bwhat do you remember\b|\bwhat did i (?:ask|tell) you to remember\b", lambda m: recall_notes()),
    (r"\b(tell me a joke|make me laugh|joke)\b", lambda m: tell_joke()),
]


def _open_anything(target: str) -> str:
    t = target.strip().lower()
    if t in SITES or "." in t:
        return open_website(t)
    return open_app(target)


def _lookup(topic: str) -> str | None:
    # "who is X" goes to Wikipedia only when X looks like a topic, not a
    # conversational question like "what is your name" or "what is 2 plus 2".
    if re.search(r"\b(you|your|my|me|i|this|that|it)\b|\d", topic, re.IGNORECASE):
        return None
    return wikipedia_summary(topic)


def handle_local(text: str) -> str | None:
    """Return a reply if `text` is a built-in command, else None (hand it to the AI)."""
    cleaned = text.strip().rstrip("?.!")
    for pattern, handler in _COMMANDS:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            reply = handler(m)
            if reply is not None:
                return reply
    return None

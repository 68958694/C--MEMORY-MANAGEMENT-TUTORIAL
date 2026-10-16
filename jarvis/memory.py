"""Long-term memory: a small JSON file of notes JARVIS keeps between runs."""

import json
from datetime import datetime

from jarvis import config


def _load() -> list[dict]:
    try:
        return json.loads(config.MEMORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(notes: list[dict]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.MEMORY_FILE.write_text(json.dumps(notes, indent=2), encoding="utf-8")


def remember(text: str) -> None:
    notes = _load()
    notes.append({"text": text.strip(), "saved": datetime.now().isoformat(timespec="seconds")})
    _save(notes)


def recall() -> list[str]:
    return [n["text"] for n in _load()]


def forget_all() -> int:
    count = len(_load())
    _save([])
    return count

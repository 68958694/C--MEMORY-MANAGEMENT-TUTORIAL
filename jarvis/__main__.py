"""Start JARVIS.

    python -m jarvis            # voice mode: say "Jarvis, what's the time?"
    python -m jarvis --text     # type instead of speaking
    python -m jarvis --hud      # Iron Man style web interface in your browser
    python -m jarvis --google-login   # connect Google Calendar + Gmail (one time)
"""

import argparse
import os
import re
import sys
from datetime import datetime

from jarvis import config
from jarvis.brain import Brain
from jarvis.briefing import Scheduler
from jarvis.voice import Voice

BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
   Just A Rather Very Intelligent System
"""

EXIT_WORDS = re.compile(r"\b(goodbye|good bye|exit|quit|shut ?down|go to sleep|power off)\b")


def greeting() -> str:
    hour = datetime.now().hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    return f"Good {part}, {config.USER_TITLE}. {config.NAME} online and at your service."


def strip_wake_word(text: str) -> str | None:
    """Return the command after the wake word, "" for the bare wake word, None if absent."""
    m = re.search(rf"\b(?:hey |ok |okay )?{re.escape(config.NAME.lower())}\b[,!.]?\s*(.*)", text.lower())
    return m.group(1).strip() if m else None


def run_text(brain: Brain, voice: Voice) -> None:
    voice.say(greeting())
    while True:
        try:
            text = input("\033[93mYOU:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if EXIT_WORDS.search(text.lower()):
            break
        voice.say(brain.respond(text))
    voice.say(f"Goodbye, {config.USER_TITLE}.")


def run_voice(brain: Brain, voice: Voice, wake_word: bool) -> None:
    try:
        from jarvis.voice import Ears
        ears = Ears()
    except Exception as exc:
        print(f"[ears] Microphone unavailable ({exc}). Falling back to text mode.\n"
              "       Install it with: pip install SpeechRecognition pyaudio")
        return run_text(brain, voice)

    voice.say(greeting())
    hint = f'Say "{config.NAME}" followed by a command.' if wake_word else "I'm listening."
    print(f"[ears] {hint} Say \"goodbye\" or press Ctrl+C to stop.")
    try:
        while True:
            heard = ears.listen()
            if not heard:
                continue
            print(f"\033[93mYOU:\033[0m {heard}")
            command = heard
            if wake_word:
                command = strip_wake_word(heard)
                if command is None:
                    continue  # not talking to JARVIS
                if command == "":
                    voice.say(f"Yes, {config.USER_TITLE}?")
                    command = ears.listen(timeout=6)
                    if not command:
                        continue
                    print(f"\033[93mYOU:\033[0m {command}")
            if EXIT_WORDS.search(command.lower()):
                break
            voice.say(brain.respond(command))
    except KeyboardInterrupt:
        print()
    voice.say(f"Goodbye, {config.USER_TITLE}.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jarvis", description="Your personal J.A.R.V.I.S. assistant.")
    parser.add_argument("--text", action="store_true", help="type commands instead of speaking")
    parser.add_argument("--hud", action="store_true", help="open the web HUD interface")
    parser.add_argument("--no-wake", action="store_true", help="respond to everything, no wake word needed")
    parser.add_argument("--mute", action="store_true", help="print replies without speaking them")
    parser.add_argument("--google-login", action="store_true", help="connect Google Calendar and Gmail")
    parser.add_argument("--no-updates", action="store_true", help="no daily briefing or meeting reminders")
    args = parser.parse_args(argv)

    if sys.platform.startswith("win"):
        os.system("")  # enable ANSI colours in the Windows console

    if args.google_login:
        from jarvis import google_services
        from jarvis.errors import SetupNeeded
        try:
            google_services.login()
            print("Google Calendar and Gmail are connected.")
        except SetupNeeded as exc:
            print(exc)
        return

    print(f"\033[96m{BANNER}\033[0m")
    brain = Brain()
    if brain.backend:
        print(f"[brain] AI core: {brain.ai_name}")
    else:
        print(f"[brain] AI core offline: {brain.error or 'no API key found.'}\n"
              "        Built-in commands still work. Add GEMINI_API_KEY to your .env file to enable the AI.")

    if args.hud:
        from jarvis.hud import serve
        return serve(brain, start_updates=not args.no_updates)

    voice = Voice(speak_aloud=not args.mute)
    if not args.no_updates:
        Scheduler(announce=voice.say).start()
    if args.text:
        run_text(brain, voice)
    else:
        run_voice(brain, voice, wake_word=not args.no_wake)


if __name__ == "__main__":
    main()

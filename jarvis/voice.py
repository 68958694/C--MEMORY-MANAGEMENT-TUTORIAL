"""Speech in and out for terminal mode.

Speech recognition uses the `SpeechRecognition` package (Google's free web
recognizer) and text-to-speech uses `pyttsx3` (offline, uses your OS voices).
If either is missing, JARVIS falls back to typing / printing.
"""

import threading

from jarvis import config


class Voice:
    def __init__(self, speak_aloud: bool = True):
        self.lock = threading.Lock()  # replies and background updates may speak at once
        self.engine = None
        if speak_aloud:
            try:
                import pyttsx3

                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", config.VOICE_RATE)
                # Prefer a British male voice if one is installed, for the JARVIS feel.
                for v in self.engine.getProperty("voices"):
                    label = f"{v.name} {v.id}".lower()
                    if any(k in label for k in ("george", "daniel", "en-gb", "en_gb", "british")):
                        self.engine.setProperty("voice", v.id)
                        break
            except Exception as exc:  # no TTS driver on this machine
                print(f"[voice] Text-to-speech unavailable ({exc}); replies will be printed only.")
                self.engine = None

    def say(self, text: str) -> None:
        with self.lock:
            print(f"\033[96m{config.NAME.upper()}:\033[0m {text}")
            if self.engine is not None:
                self.engine.say(text)
                self.engine.runAndWait()


class Ears:
    """Listens on the microphone and returns what was said as text."""

    def __init__(self):
        import speech_recognition as sr

        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()
        with self.mic as source:
            print("[ears] Calibrating for background noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self, timeout: float | None = None, phrase_limit: float = 12) -> str:
        """Return the recognised phrase, or "" if nothing intelligible was heard."""
        with self.mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except self.sr.WaitTimeoutError:
                return ""
        try:
            return self.recognizer.recognize_google(audio)
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as exc:
            print(f"[ears] Speech service unavailable: {exc}")
            return ""

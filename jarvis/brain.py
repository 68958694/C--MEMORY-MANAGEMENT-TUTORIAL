"""JARVIS's brain: instant built-in commands first, the AI (with tools) for everything else."""

import re
import threading
from datetime import datetime

from jarvis import briefing, config, google_services, leads, llm, memory, skills
from jarvis.errors import SetupNeeded

SYSTEM_PROMPT = f"""You are {config.NAME}, a personal AI assistant modelled on Tony Stark's J.A.R.V.I.S.:
calm, witty, loyal and very competent, with a dry British sense of humour. You address
the user as "{config.USER_TITLE}". You are also their business assistant.

Your replies are read aloud by a text-to-speech voice, so:
- Keep them short: one to three sentences unless the user asks for detail.
- Use plain spoken sentences. No markdown, bullet points, code blocks, emoji or URLs.

You run on the user's own computer and have tools to: open websites and apps, search, check
the weather, build and edit software projects, manage their Google Calendar, check Gmail, call
or text their phone, give business briefings, find potential clients, manage their client list,
and draft outreach emails. Use a tool whenever it fits instead of telling the user how to do
it themselves. After using a tool, briefly confirm what happened.

Rules:
- Coding: when asked to build something, call build_project with a detailed spec that expands
  on what the user said. Say what you built, not the code itself.
- Before scheduling a meeting or inviting people, confirm title, date, time and attendees,
  unless the user already gave all of them. Work out dates from the timestamp on each message.
- Only call or text the user when they ask, or when an update is urgent.
- Never invent clients, contacts or facts about businesses; use find_clients.
- If a tool says something is "not set up yet", tell the user what to set up in one sentence."""

# Business commands answered instantly without the AI (they still need their integration set up).
_BUSINESS_COMMANDS = [
    (r"\b(business (update|briefing|report)|morning (briefing|report)|brief me|daily briefing)\b",
     lambda m: briefing.business_briefing()),
    (r"\b(what'?s on my (calendar|schedule)|my (meetings|schedule|calendar) (for )?today|"
     r"(any|do i have) meetings( today)?)\b", lambda m: google_services.list_meetings(1)),
    (r"\b(check|read) (my )?(e-?mails?|inbox)\b|\bunread e-?mails?\b", lambda m: google_services.check_email(5)),
    (r"\b(show|list|read) (me )?(my )?(leads|clients|pipeline|prospects)\b|\bmy (client list|pipeline)\b",
     lambda m: leads.list_leads("")),
]


class Brain:
    def __init__(self):
        self.lock = threading.Lock()  # one conversation; the HUD and scheduler share it
        self.error = ""
        try:
            self.backend = llm.create_backend(_system_prompt())
        except llm.AIError as exc:
            self.backend, self.error = None, str(exc)

    @property
    def ai_name(self) -> str:
        return self.backend.name if self.backend else ""

    def respond(self, text: str) -> str:
        text = text.strip()
        if not text:
            return f"Yes, {config.USER_TITLE}?"
        with self.lock:
            try:
                reply = skills.handle_local(text) or _business_local(text)
                if reply is not None:
                    return reply
                if self.backend is None:
                    return ("I don't have a built-in command for that, and my AI core is offline. "
                            + (self.error or "Add a GEMINI_API_KEY to your .env file to enable it."))
                stamp = datetime.now().strftime("%A %d %B %Y, %I:%M %p")
                return self.backend.chat(f"[{stamp}] {text}") or f"Done, {config.USER_TITLE}."
            except SetupNeeded as exc:
                return f"That isn't set up yet. {exc}"
            except llm.AIError as exc:
                return str(exc)


def _business_local(text: str) -> str | None:
    cleaned = text.strip().rstrip("?.!")
    for pattern, handler in _BUSINESS_COMMANDS:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            return handler(m)
    return None


def _system_prompt() -> str:
    prompt = SYSTEM_PROMPT
    profile = leads.business_profile()
    if profile:
        prompt += f"\n\nThe user's business: {profile}"
    else:
        prompt += ("\n\nYou don't know the user's business yet. When it becomes relevant, ask what they sell "
                   "and who their ideal clients are, then save it with set_business_profile.")
    notes = memory.recall()
    if notes:
        prompt += "\n\nThings the user asked you to remember:\n" + "\n".join(f"- {n}" for n in notes)
    return prompt

"""Business updates: a spoken briefing, plus a background scheduler that delivers it
every morning and reminds you before meetings (by voice, text message or phone call)."""

import threading
import time
from datetime import date, datetime

from jarvis import config, google_services, leads, llm, memory, phone, skills


def gather() -> list[str]:
    """Collect the raw facts for a briefing. Each source is skipped if it isn't set up."""
    facts = [skills.tell_date(), skills.tell_time()]
    weather = skills.weather("")
    if "can't reach" not in weather:
        facts.append(f"Weather: {weather}")

    if google_services.is_authorized():
        try:
            facts.append("Calendar: " + google_services.list_meetings(1))
            facts.append("Email: " + google_services.check_email(5))
        except Exception as exc:
            facts.append(f"Calendar/email unavailable: {exc}")
    else:
        facts.append("Calendar and email are not connected yet.")

    pipeline = leads.all_leads()
    if pipeline:
        counts = {s: sum(1 for l in pipeline if l["status"] == s) for s in leads.STATUSES}
        facts.append("Client pipeline: " + ", ".join(f"{n} {s}" for s, n in counts.items() if n))
        fresh = [l["name"] for l in pipeline if l["status"] == "new"][:5]
        if fresh:
            facts.append("Leads not yet contacted: " + ", ".join(fresh))
    else:
        facts.append("Client pipeline: empty (ask me to find clients).")

    notes = memory.recall()
    if notes:
        facts.append("Notes: " + "; ".join(notes[-5:]))
    return facts


def business_briefing() -> str:
    facts = gather()
    if not llm.available():
        return " ".join(facts)
    try:
        return llm.generate(
            f"You are {config.NAME}, a witty, efficient personal assistant. Turn these facts into a spoken "
            f"business briefing for your boss (address them as {config.USER_TITLE}). 4 to 7 short sentences, "
            f"most important first, end with one concrete suggestion for today. Plain spoken text only, "
            f"no markdown or lists.\n\n" + "\n".join(f"- {f}" for f in facts))
    except llm.AIError:
        return " ".join(facts)


class Scheduler(threading.Thread):
    """Checks every 30 seconds for the daily briefing time and upcoming meetings.

    `announce(text)` is called to speak/show updates in whatever interface is running.
    """

    def __init__(self, announce):
        super().__init__(daemon=True, name="jarvis-scheduler")
        self.announce = announce
        self.briefed_on: date | None = None
        self.reminded: set[str] = set()
        channels = {c.strip() for c in config.BRIEFING_BY.lower().split(",")}
        self.by_sms = "sms" in channels and phone.is_configured()
        self.by_call = "call" in channels and phone.is_configured()

    def run(self):
        while True:
            try:
                self.tick(datetime.now())
            except Exception as exc:  # never let the background thread die
                print(f"[scheduler] {exc}")
            time.sleep(30)

    def tick(self, now: datetime) -> None:
        if config.BRIEFING_TIME.lower() != "off" and self.briefed_on != now.date():
            hour, minute = (int(x) for x in config.BRIEFING_TIME.split(":"))
            if (now.hour, now.minute) >= (hour, minute):
                self.briefed_on = now.date()
                # Don't fire a stale briefing if JARVIS was started late in the day.
                if (now.hour * 60 + now.minute) - (hour * 60 + minute) <= 60:
                    self.deliver(business_briefing())

        if config.MEETING_REMINDER_MINUTES > 0 and google_services.is_authorized():
            for event in google_services.upcoming_events(config.MEETING_REMINDER_MINUTES / 60):
                if event["id"] in self.reminded or "dateTime" not in event["start"]:
                    continue
                self.reminded.add(event["id"])
                start = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
                minutes = max(1, round((start - now.astimezone()).total_seconds() / 60))
                text = (f"Reminder: {event.get('summary', 'a meeting')} starts in {minutes} "
                        f"minute{'s' if minutes != 1 else ''}.")
                if event.get("hangoutLink"):
                    text += " It has a Google Meet link."
                self.deliver(text, call=False)

    def deliver(self, text: str, call: bool = True) -> None:
        self.announce(text)
        try:
            if self.by_call and call:
                phone.call_me(text)
            elif self.by_sms or (self.by_call and not call):
                phone.text_me(text)
        except Exception as exc:
            print(f"[scheduler] Couldn't reach your phone: {exc}")

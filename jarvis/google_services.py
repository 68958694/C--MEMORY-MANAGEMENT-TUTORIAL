"""Google Calendar (meetings) and Gmail (unread mail).

One-time setup (README has screenshots-level detail):
  1. In Google Cloud Console, enable the Google Calendar API and Gmail API.
  2. Create an OAuth client ID of type "Desktop app" and download the JSON.
  3. Save it as ~/.jarvis/google_credentials.json
  4. Run: python -m jarvis --google-login   (a browser window asks you to allow access)

Gmail access is read-only: JARVIS can tell you about new mail but cannot send it.
"""

import uuid
from datetime import datetime, timedelta

from jarvis import config
from jarvis.errors import SetupNeeded

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_services: dict = {}


def is_authorized() -> bool:
    """True once the user has logged in (safe to use from background reminders)."""
    return config.GOOGLE_TOKEN_FILE.exists()


def login() -> None:
    """Run the browser sign-in (or refresh) and save the token."""
    _credentials(interactive=True)


def _credentials(interactive: bool = True):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SetupNeeded("Google packages are missing. Run: pip install google-api-python-client google-auth-oauthlib")

    creds = None
    if config.GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not config.GOOGLE_CREDENTIALS_FILE.exists():
            raise SetupNeeded(
                f"Google Calendar isn't connected. Download an OAuth 'Desktop app' client from Google Cloud "
                f"Console, save it as {config.GOOGLE_CREDENTIALS_FILE}, then run: python -m jarvis --google-login")
        if not interactive:
            raise SetupNeeded("Google sign-in is needed. Run: python -m jarvis --google-login")
        flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service(name: str, version: str):
    if name not in _services:
        from googleapiclient.discovery import build
        _services[name] = build(name, version, credentials=_credentials(), cache_discovery=False)
    return _services[name]


def _local_tz():
    return datetime.now().astimezone().tzinfo


def _parse_start(start: str) -> datetime:
    try:
        dt = datetime.fromisoformat(start.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"I couldn't understand the start time '{start}'. Use a format like 2026-10-20T15:00.")
    return dt if dt.tzinfo else dt.replace(tzinfo=_local_tz())


def _spoken_time(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


# --------------------------------------------------------------------------- calendar


def upcoming_events(hours: float) -> list[dict]:
    """Raw events starting between now and `hours` from now."""
    now = datetime.now(_local_tz())
    result = _service("calendar", "v3").events().list(
        calendarId="primary", timeMin=now.isoformat(), timeMax=(now + timedelta(hours=hours)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    return result.get("items", [])


def list_meetings(days: int = 1) -> str:
    days = max(1, int(days))
    now = datetime.now(_local_tz())
    end_of_range = (now + timedelta(days=days - 1)).replace(hour=23, minute=59, second=59)
    events = upcoming_events((end_of_range - now).total_seconds() / 3600)
    when = "today" if days == 1 else f"in the next {days} days"
    if not events:
        return f"You have no more meetings {when}."
    lines = []
    for e in events:
        start = e["start"].get("dateTime")
        if start:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(_local_tz())
            day = "" if days == 1 else dt.strftime("%A ")
            lines.append(f"{day}{_spoken_time(dt)}: {e.get('summary', 'Untitled')}")
        else:
            lines.append(f"all day: {e.get('summary', 'Untitled')}")
    return f"You have {len(events)} meeting{'s' if len(events) != 1 else ''} {when}. " + "; ".join(lines) + "."


def schedule_meeting(title: str, start: str, duration_minutes: int = 30, attendees: str = "",
                     description: str = "", video_call: bool = True) -> str:
    begin = _parse_start(start)
    end = begin + timedelta(minutes=int(duration_minutes) or 30)
    emails = [a.strip() for a in attendees.replace(";", ",").split(",") if "@" in a]
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": begin.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "attendees": [{"email": e} for e in emails],
    }
    if video_call:
        event["conferenceData"] = {"createRequest": {
            "requestId": uuid.uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    created = _service("calendar", "v3").events().insert(
        calendarId="primary", body=event, conferenceDataVersion=1 if video_call else 0,
        sendUpdates="all" if emails else "none",
    ).execute()
    when = begin.strftime("%A %B %d at ") + _spoken_time(begin)
    msg = f"Scheduled '{title}' for {when}"
    if emails:
        msg += f", and sent invites to {', '.join(emails)}"
    if created.get("hangoutLink"):
        msg += ". A Google Meet link is attached"
    return msg + "."


# --------------------------------------------------------------------------- gmail


def unread_emails(max_results: int = 5) -> list[dict]:
    gmail = _service("gmail", "v1")
    listing = gmail.users().messages().list(
        userId="me", q="is:unread category:primary newer_than:3d", maxResults=int(max_results)).execute()
    mails = []
    for ref in listing.get("messages", []):
        msg = gmail.users().messages().get(userId="me", id=ref["id"], format="metadata",
                                           metadataHeaders=["From", "Subject"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("From", "someone").split("<")[0].strip().strip('"') or "someone"
        mails.append({"from": sender, "subject": headers.get("Subject", "(no subject)"),
                      "snippet": msg.get("snippet", "")})
    return mails


def check_email(max_results: int = 5) -> str:
    mails = unread_emails(max_results)
    if not mails:
        return "No new unread emails in your primary inbox."
    items = "; ".join(f"from {m['from']}: {m['subject']}" for m in mails)
    return f"You have {len(mails)} recent unread email{'s' if len(mails) != 1 else ''}. {items}."

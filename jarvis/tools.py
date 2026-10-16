"""Every action the AI may take, as plain Python functions.

The Gemini SDK reads each function's name, type hints and docstring directly. For
Claude, `claude_schemas()` builds the equivalent JSON schemas. To give JARVIS a
new ability, write a function here and add it to ALL.
"""

import functools
import inspect

from jarvis import builder, briefing, google_services, leads, phone, skills
from jarvis.errors import SetupNeeded

def _tool(func):
    """Turn setup errors into plain answers the AI can relay."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SetupNeeded as exc:
            return f"Not set up yet: {exc}"
    return wrapper


# --------------------------------------------------------------------------- everyday


@_tool
def get_time() -> str:
    """Get the current local time."""
    return skills.tell_time()


@_tool
def get_date() -> str:
    """Get today's date."""
    return skills.tell_date()


@_tool
def open_website(target: str) -> str:
    """Open a website in the user's browser. `target` is a site name (youtube, gmail, github...) or a domain like example.com."""
    return skills.open_website(target)


@_tool
def google_search(query: str) -> str:
    """Open a Google search for `query` in the user's browser."""
    return skills.google_search(query)


@_tool
def play_on_youtube(query: str) -> str:
    """Play a song or video: opens a YouTube search for `query` in the browser."""
    return skills.youtube_search(query)


@_tool
def wikipedia_summary(topic: str) -> str:
    """Get a two-sentence Wikipedia summary of a topic."""
    return skills.wikipedia_summary(topic)


@_tool
def get_weather(city: str = "") -> str:
    """Get the current weather. Leave `city` empty for the user's own location."""
    return skills.weather(city)


@_tool
def system_status() -> str:
    """Report CPU, memory and battery usage of the user's computer."""
    return skills.system_status()


@_tool
def open_app(name: str) -> str:
    """Launch a desktop application on the user's computer, e.g. 'notepad', 'spotify', 'calculator'."""
    return skills.open_app(name)


@_tool
def remember_note(note: str) -> str:
    """Save a note to long-term memory when the user asks you to remember something."""
    return skills.remember_note(note)


@_tool
def recall_notes() -> str:
    """Read back everything the user asked you to remember."""
    return skills.recall_notes()


# --------------------------------------------------------------------------- coding


@_tool
def build_project(name: str, request: str) -> str:
    """Write a complete new software project (website, script, app, tool...) on the user's computer and open it.
    `name` is a short project name; `request` describes in detail what to build, including any features,
    style and technology the user asked for."""
    return builder.build_project(name, request)


@_tool
def improve_project(name: str, change_request: str) -> str:
    """Change an existing project JARVIS built: add features, fix bugs, restyle. `name` is the project name."""
    return builder.improve_project(name, change_request)


@_tool
def list_projects() -> str:
    """List the projects JARVIS has built."""
    return builder.list_projects()


@_tool
def open_project(name: str) -> str:
    """Open a project JARVIS built (its web page, or its folder)."""
    return builder.open_project(name)


# --------------------------------------------------------------------------- calendar and email


@_tool
def list_meetings(days: int = 1) -> str:
    """List meetings on the user's Google Calendar for the next `days` days (1 = today)."""
    return google_services.list_meetings(days)


@_tool
def schedule_meeting(title: str, start: str, duration_minutes: int = 30, attendees: str = "",
                     description: str = "", video_call: bool = True) -> str:
    """Create a Google Calendar event and email invites to attendees. Only call this after the user confirmed
    the title, time and attendees. `start` is local time in ISO format, e.g. 2026-10-20T15:00.
    `attendees` is a comma-separated list of email addresses. `video_call` adds a Google Meet link."""
    return google_services.schedule_meeting(title, start, duration_minutes, attendees, description, video_call)


@_tool
def check_email(max_results: int = 5) -> str:
    """Summarise the user's latest unread Gmail messages (sender and subject)."""
    return google_services.check_email(max_results)


# --------------------------------------------------------------------------- phone


@_tool
def call_me(message: str) -> str:
    """Phone the user's mobile and read `message` aloud. Use for urgent updates or when asked to call."""
    return phone.call_me(message)


@_tool
def text_me(message: str) -> str:
    """Send an SMS text message to the user's mobile."""
    return phone.text_me(message)


# --------------------------------------------------------------------------- business


@_tool
def set_business_profile(description: str) -> str:
    """Save what the user's business sells and who its ideal clients are. Used to find and qualify clients."""
    return leads.set_business_profile(description)


@_tool
def business_briefing() -> str:
    """Give an update on the user's business: today's meetings, unread email, client pipeline and notes."""
    return briefing.business_briefing()


@_tool
def find_clients(criteria: str, location: str = "", count: int = 5) -> str:
    """Find real potential clients (businesses) for the user's business and save them to the client list.
    `criteria` describes the kind of client, e.g. 'dental clinics' or 'restaurants without online ordering'.
    `location` is a city or region."""
    return leads.find_clients(criteria, location, count)


@_tool
def list_clients(status: str = "") -> str:
    """Read out the saved client/lead list. Optional `status` filter: new, contacted, meeting, won, lost."""
    return leads.list_leads(status)


@_tool
def update_client(name: str, status: str = "", note: str = "") -> str:
    """Update a saved lead: set `status` (new, contacted, meeting, won, lost) and/or add a `note`."""
    return leads.update_lead(name, status, note)


@_tool
def draft_outreach_email(client_name: str) -> str:
    """Write a short personalised outreach email to a saved lead and open it in the user's mail app for review.
    Never sends anything by itself."""
    return leads.draft_outreach(client_name)


@_tool
def export_clients() -> str:
    """Export the client list to a CSV spreadsheet and open it."""
    return leads.export_csv()


ALL = [
    get_time, get_date, open_website, google_search, play_on_youtube, wikipedia_summary, get_weather,
    system_status, open_app, remember_note, recall_notes,
    build_project, improve_project, list_projects, open_project,
    list_meetings, schedule_meeting, check_email,
    call_me, text_me,
    set_business_profile, business_briefing, find_clients, list_clients, update_client,
    draft_outreach_email, export_clients,
]
_BY_NAME = {f.__name__: f for f in ALL}


def run(name: str, args: dict) -> tuple[str, bool]:
    """Run a tool by name. Returns (output, is_error)."""
    func = _BY_NAME.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        return str(func(**(args or {}))), False
    except Exception as exc:
        return f"Error: {exc}", True


_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def claude_schemas() -> list[dict]:
    schemas = []
    for func in ALL:
        props, required = {}, []
        for p in inspect.signature(func).parameters.values():
            props[p.name] = {"type": _JSON_TYPES.get(p.annotation, "string")}
            if p.default is inspect.Parameter.empty:
                required.append(p.name)
        schemas.append({
            "name": func.__name__,
            "description": inspect.cleandoc(func.__doc__ or ""),
            "input_schema": {"type": "object", "properties": props, "required": required,
                             "additionalProperties": False},
        })
    return schemas

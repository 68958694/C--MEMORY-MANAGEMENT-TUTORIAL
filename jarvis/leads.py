"""Finding clients: search for real businesses that fit your business, and keep a simple client list.

Where leads come from:
  1. Live web search through the AI (Gemini with Google Search, or Claude web search).
     For Gemini this needs billing enabled on your API key; free keys get "quota exceeded".
  2. Otherwise OpenStreetMap (free): real local businesses with address, and often
     website and phone. Best for local clients ("dentists in Austin").

The list is stored in ~/.jarvis/leads.json. JARVIS drafts outreach emails and
opens them in your mail app, but never sends anything itself.
"""

import csv
import json
import time
import urllib.parse
import webbrowser
from datetime import date

from jarvis import config, llm, skills

STATUSES = ("new", "contacted", "meeting", "won", "lost")
_UA = {"User-Agent": "JARVIS-personal-assistant/1.0 (lead finder)"}


# --------------------------------------------------------------------------- storage


def _load() -> list[dict]:
    try:
        return json.loads(config.LEADS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(leads: list[dict]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.LEADS_FILE.write_text(json.dumps(leads, indent=2), encoding="utf-8")


def all_leads() -> list[dict]:
    return _load()


def business_profile() -> str:
    try:
        saved = json.loads(config.BUSINESS_FILE.read_text(encoding="utf-8")).get("description", "")
    except (FileNotFoundError, json.JSONDecodeError):
        saved = ""
    return saved or config.BUSINESS_DESCRIPTION


def set_business_profile(description: str) -> str:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.BUSINESS_FILE.write_text(json.dumps({"description": description.strip()}, indent=2), encoding="utf-8")
    return "Got it. I'll use that to find and qualify clients for you."


def _find(leads: list[dict], name: str) -> dict | None:
    name = name.strip().lower()
    exact = [l for l in leads if l["name"].lower() == name]
    partial = [l for l in leads if name in l["name"].lower() or l["name"].lower() in name]
    return (exact or partial or [None])[0]


# --------------------------------------------------------------------------- finding


def _clean(lead: dict, source: str) -> dict | None:
    if not isinstance(lead, dict) or not str(lead.get("name", "")).strip():
        return None
    return {
        "name": str(lead["name"]).strip(),
        "website": str(lead.get("website") or "").strip(),
        "phone": str(lead.get("phone") or "").strip(),
        "email": str(lead.get("email") or "").strip(),
        "location": str(lead.get("location") or "").strip(),
        "why_fit": str(lead.get("why_fit") or "").strip(),
        "source": source,
        "status": "new",
        "found": date.today().isoformat(),
        "notes": [],
    }


def _search_web(criteria: str, location: str, count: int, profile: str) -> list[dict] | None:
    prompt = f"""Find {count} real businesses that are good potential clients for this business:
{profile or "(no business description given; judge fit from the criteria alone)"}

Looking for: {criteria}{f" in {location}" if location else ""}

Use web search. Only include businesses you actually found in the search results - never invent one.
For each, give its name, website, phone, public contact email (only if published; otherwise empty),
location, and one sentence on why it fits.

Reply with only a JSON array of objects with keys: name, website, phone, email, location, why_fit."""
    text = llm.search(prompt)
    if text is None:
        return None
    try:
        data = llm.extract_json(text)
    except llm.AIError:
        return None
    if isinstance(data, dict):
        data = data.get("leads") or data.get("businesses") or []
    return [l for l in (_clean(d, "web search") for d in data) if l] if isinstance(data, list) else None


def _nominatim(query: str) -> list[dict]:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "extratags": 1, "limit": 40})
    try:
        return json.loads(skills._fetch(url, timeout=15)) or []
    except Exception:
        return []


def _search_osm(criteria: str, location: str, count: int, profile: str) -> list[dict]:
    queries = [f"{criteria} in {location}" if location else criteria]
    if llm.available():
        try:
            data = llm.generate_json(
                f"Turn this lead search into up to 3 OpenStreetMap search queries of the form "
                f"'<type of business> in <city>', using common place types (dentist, restaurant, gym, "
                f"law firm, hotel, car repair...).\nLooking for: {criteria}\nLocation: {location or 'not given'}\n"
                f'Reply with JSON: {{"queries": ["..."]}}')
            queries = [q for q in data.get("queries", []) if isinstance(q, str)][:3] or queries
        except (llm.AIError, AttributeError):
            pass

    found, seen = [], set()
    for i, q in enumerate(queries):
        if i:
            time.sleep(1.1)  # OpenStreetMap's usage policy: max one request per second
        for place in _nominatim(q):
            tags = place.get("extratags") or {}
            name = place.get("name") or tags.get("name")
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            found.append(_clean({
                "name": name,
                "website": tags.get("website") or tags.get("contact:website"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "email": tags.get("email") or tags.get("contact:email"),
                "location": ", ".join(place.get("display_name", "").split(", ")[:4]),
            }, "OpenStreetMap"))

    if len(found) > count and llm.available():
        listing = "\n".join(f"{i}. {l['name']} - {l['location']} - website: {l['website'] or 'none'}"
                            for i, l in enumerate(found))
        try:
            picks = llm.generate_json(
                f"My business: {profile or 'not described'}\nI'm looking for: {criteria}\n\n"
                f"Pick the {count} best potential clients from this list and say in one sentence why each fits:\n"
                f'{listing}\n\nReply with JSON: [{{"index": 0, "why_fit": "..."}}]')
            chosen = []
            for p in picks:
                idx = p.get("index") if isinstance(p, dict) else None
                if isinstance(idx, int) and 0 <= idx < len(found):
                    found[idx]["why_fit"] = str(p.get("why_fit", ""))
                    chosen.append(found[idx])
            if chosen:
                return chosen[:count]
        except (llm.AIError, AttributeError, TypeError):
            pass
    return found[:count]


def find_clients(criteria: str, location: str = "", count: int = 5) -> str:
    count = max(1, min(int(count or 5), 20))
    profile = business_profile()
    results = _search_web(criteria, location, count, profile)
    if not results:
        results = _search_osm(criteria, location, count, profile)
    if not results:
        return ("I couldn't find matching businesses. Try a simpler type of business and a city, "
                "for example: find dental clinics in Austin.")

    leads = _load()
    known = {l["name"].lower() for l in leads}
    new = [l for l in results if l["name"].lower() not in known]
    leads.extend(new)
    _save(leads)
    if not new:
        return "Everyone I found is already on your client list."
    names = ", ".join(l["name"] for l in new[:6])
    more = f" and {len(new) - 6} more" if len(new) > 6 else ""
    hint = "" if profile else " Tip: tell me what your business does so I can pick better matches."
    return (f"I found {len(new)} potential clients: {names}{more}. They're saved in your client list. "
            f"Shall I draft an outreach email to any of them?{hint}")


# --------------------------------------------------------------------------- managing


def list_leads(status: str = "") -> str:
    leads = _load()
    status = status.strip().lower()
    if status:
        leads = [l for l in leads if l["status"] == status]
    if not leads:
        return f"No {status + ' ' if status else ''}clients on your list yet. Ask me to find some."
    counts = {s: sum(1 for l in _load() if l["status"] == s) for s in STATUSES}
    summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    shown = "; ".join(f"{l['name']} ({l['status']})" for l in leads[-10:])
    return f"Your pipeline: {summary}. {'Latest' if len(leads) > 10 else 'Clients'}: {shown}."


def update_lead(name: str, status: str = "", note: str = "") -> str:
    leads = _load()
    lead = _find(leads, name)
    if lead is None:
        return f"I couldn't find {name} on your client list."
    changes = []
    status = status.strip().lower()
    if status:
        if status not in STATUSES:
            return f"Status must be one of: {', '.join(STATUSES)}."
        lead["status"] = status
        changes.append(f"marked as {status}")
    if note.strip():
        lead.setdefault("notes", []).append(f"{date.today().isoformat()}: {note.strip()}")
        changes.append("note added")
    _save(leads)
    return f"{lead['name']}: {' and '.join(changes) or 'no changes'}."


def draft_outreach(client_name: str) -> str:
    leads = _load()
    lead = _find(leads, client_name)
    if lead is None:
        return f"I couldn't find {client_name} on your client list."
    profile = business_profile()
    if not profile:
        return "First tell me what your business offers, so the email can pitch it properly."
    data = llm.generate_json(
        f"Write a short, friendly, non-pushy cold outreach email.\nFrom: a business that {profile}\n"
        f"To: {lead['name']} ({lead['location']}). Why they might need us: {lead['why_fit'] or 'unknown'}.\n"
        f"Under 120 words, one clear call to action (a short call), no fake claims, sign off as [Your name].\n"
        f'Reply with JSON: {{"subject": "...", "body": "..."}}')
    if not isinstance(data, dict) or not data.get("body"):
        return "The AI didn't produce an email draft. Please try again."
    subject, body = str(data.get("subject", "")), str(data["body"])
    lead["draft"] = {"subject": subject, "body": body}
    _save(leads)

    if lead["email"]:
        webbrowser.open(f"mailto:{lead['email']}?" + urllib.parse.urlencode(
            {"subject": subject, "body": body}, quote_via=urllib.parse.quote))
        return f"I've drafted an email to {lead['name']} and opened it in your mail app for you to review. Subject: {subject}."
    if lead["website"]:
        webbrowser.open(lead["website"] if lead["website"].startswith("http") else "https://" + lead["website"])
        return (f"I drafted the email, subject '{subject}', but {lead['name']} has no public email listed. "
                f"I've opened their website so you can find a contact form. The draft is saved in your client list.")
    return f"I drafted the email, subject '{subject}', and saved it. {lead['name']} has no email or website on record."


def export_csv() -> str:
    leads = _load()
    if not leads:
        return "Your client list is empty."
    config.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    path = config.WORKSPACE_DIR / "clients.csv"
    fields = ["name", "status", "website", "phone", "email", "location", "why_fit", "source", "found", "notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for l in leads:
            writer.writerow({**l, "notes": " | ".join(l.get("notes", []))})
    skills.open_path(path)
    return f"Exported {len(leads)} clients to {path}."

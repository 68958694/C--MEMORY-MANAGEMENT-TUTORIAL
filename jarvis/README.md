# J.A.R.V.I.S. — your personal AI and business assistant

*Just A Rather Very Intelligent System.* Talk to it and it talks back. It can:

- **Code for you:** "Build me a landing page for my bakery" writes the whole project to `~/jarvis-projects/` and opens it. "Make it dark themed" edits it.
- **Schedule meetings:** "Schedule a call with sam@acme.com Friday at 3pm" creates a Google Calendar event with a Meet link and emails the invite.
- **Call and text you:** it phones your mobile and reads updates aloud, or sends an SMS (through Twilio).
- **Keep you updated:** a daily business briefing (meetings, unread email, client pipeline) and reminders before every meeting, by voice, text or phone call.
- **Find clients:** "Find 10 dental clinics in Austin" finds real businesses, saves them to your client list, and drafts personalised outreach emails for you to review and send.
- Everyday tasks: open websites and apps, play music on YouTube, weather, Wikipedia, notes, system status.

It runs on **Google Gemini** by default, or on Claude if you prefer.

![JARVIS HUD](docs/hud.png)

---

## 1. Install

You need **Python 3.10+**. From the repository root (the folder that contains `jarvis/`):

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r jarvis/requirements.txt
```

## 2. Add your API key (keep it secret)

Copy `jarvis/.env.example` to a file called **`.env` in the repository root**, and paste your Gemini key:

```
GEMINI_API_KEY=your-key-here
```

`.env` is git-ignored so your key is never committed. **Never paste keys into code, chats or screenshots.** If a key leaks, delete it at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and create a new one.

> **Free vs paid Gemini keys:** free keys have small daily limits per model. JARVIS automatically
> switches to the next model when one runs out, but heavy use (building projects, finding clients) uses
> them up quickly. Live **Google Search** for finding clients only works once billing is enabled on the
> key. Until then JARVIS finds local businesses through OpenStreetMap instead.

## 3. Run

| Mode | Command |
|---|---|
| **Web HUD** (recommended) | `python -m jarvis --hud` then click the arc reactor (or press Space) and speak. Use Chrome or Edge. |
| **Voice** in the terminal | `python -m jarvis` then say *"Jarvis, …"* |
| **Text** | `python -m jarvis --text` |

Flags: `--no-wake` (no need to say "Jarvis"), `--mute` (don't speak replies), `--no-updates` (no briefings or reminders).

**First thing to say:** *"My business is a web design agency. Our ideal clients are local businesses with outdated websites."* JARVIS saves this and uses it to find and pitch clients.

---

## 4. Optional: connect Google Calendar + Gmail (meetings, reminders, email updates)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project.
2. **APIs & Services → Library:** enable **Google Calendar API** and **Gmail API**.
3. **APIs & Services → OAuth consent screen:** choose *External*, fill in the app name, and add your own Google account under **Test users**.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID → Desktop app.** Download the JSON.
5. Save it as `~/.jarvis/google_credentials.json` (Windows: `C:\Users\<you>\.jarvis\google_credentials.json`).
6. Run `python -m jarvis --google-login` and allow access in the browser window.

JARVIS can create calendar events and **read** Gmail. It cannot send or delete email.

## 5. Optional: phone calls and text messages (Twilio)

1. Sign up at [twilio.com](https://www.twilio.com) and get a phone number. On a trial account, also verify your own mobile number under *Verified Caller IDs*.
2. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxx
   TWILIO_FROM_NUMBER=+15551234567
   JARVIS_MY_PHONE=+15557654321
   ```
3. To get your daily briefing as a phone call or text, set `JARVIS_BRIEFING_BY=call` or `sms` (or `voice,sms`).

Calls and texts cost a few cents each on Twilio.

---

## What you can say

| Say | JARVIS does |
|---|---|
| "Build me a portfolio website with a contact form" | Writes the project, opens it in your browser |
| "Add a dark mode to the portfolio" / "Fix the menu on mobile" | Edits the existing project |
| "What projects do you have?" / "Open the tip calculator" | Lists / opens projects |
| "What's on my calendar today?" | Reads today's meetings |
| "Schedule a 30 minute call with sam@acme.com tomorrow at 3pm" | Confirms, then books it with a Meet link and sends the invite |
| "Check my email" | Reads sender and subject of recent unread mail |
| "Business update" / "Brief me" | Briefing: meetings, email, pipeline, suggestions |
| "Call me with the briefing" / "Text me my meetings" | Phones or texts you |
| "Find 10 restaurants in Lagos that could use a website" | Finds real businesses, saves them as leads |
| "Show my clients" / "Mark Smile Dental as contacted" | Manages your pipeline (new, contacted, meeting, won, lost) |
| "Draft an email to Smile Dental" | Writes the email and opens it in your mail app. **You** press send |
| "Export my clients" | Saves `clients.csv` and opens it in Excel/Sheets |
| "Open YouTube", "Play lo-fi beats", "Weather in London", "Who is Ada Lovelace?" | Everyday stuff |
| "Remember that the invoice is due Friday" / "What do you remember?" | Notes |

## Safety by design

- JARVIS **writes** code but never **runs** it by itself. You decide what executes on your computer.
- It **drafts** outreach emails but never sends them. Cold-email rules (CAN-SPAM, GDPR) are your call.
- It confirms meeting details before sending invites, and only calls or texts **you**.
- The web HUD only accepts requests from your own computer.

## How it works

```
 you speak ──► speech-to-text ──► Brain
                                   ├─ built-in command? (time, open site, briefing...) ─► instant answer
                                   └─ otherwise ─► Gemini, with 27 tools ─► builds, books, calls, finds clients...
 you hear ◄── text-to-speech ◄──── reply
 background: Scheduler ─► 8:30 daily briefing + meeting reminders ─► voice / SMS / call
```

| File | Role |
|---|---|
| `__main__.py` | Startup, wake word, voice/text loops |
| `brain.py` | Routes requests; JARVIS's personality and rules |
| `llm.py` | Gemini and Claude backends, model fallback |
| `tools.py` | Every action the AI can take (add your own here) |
| `builder.py` | Writes and edits coding projects |
| `google_services.py` | Google Calendar and Gmail |
| `phone.py` | Twilio calls and texts |
| `leads.py` | Finding clients, client list, outreach drafts |
| `briefing.py` | Business briefing and the background scheduler |
| `skills.py` | Everyday skills and instant voice commands |
| `hud.py`, `hud.html` | The web HUD |
| `voice.py`, `memory.py`, `config.py` | Voice I/O, notes, settings |

Your data lives in `~/.jarvis/` (notes, client list, business profile, Google login) and your projects in `~/jarvis-projects/`.

## Settings

All settings are in `.env` (see `.env.example`) or environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | | Your Gemini key |
| `JARVIS_GEMINI_MODELS` | `gemini-3.5-flash,gemini-flash-latest,gemini-3.8-flash,gemini-3.1-flash-lite` | Models to try, in order |
| `JARVIS_PROVIDER` | auto | `gemini` or `claude` |
| `JARVIS_NAME` / `JARVIS_USER_TITLE` | `Jarvis` / `sir` | Its name (wake word) and what it calls you |
| `JARVIS_BUSINESS` | | Your business description |
| `JARVIS_BRIEFING_TIME` / `JARVIS_BRIEFING_BY` | `08:30` / `voice` | Daily briefing time and channel(s) |
| `JARVIS_REMINDER_MINUTES` | `10` | Meeting reminder lead time (0 = off) |
| `JARVIS_WORKSPACE` | `~/jarvis-projects` | Where projects are built |
| `JARVIS_CITY` | auto | Default weather city |
| `JARVIS_HUD_PORT` | `8765` | Web HUD port |

## Troubleshooting

- **"I've hit the Gemini usage limit"**: your free key's daily quota is used up. Wait, or enable billing on the key in Google AI Studio.
- **"Gemini is overloaded"**: Google's servers are busy; try again in a minute.
- **Voice input does nothing in the HUD**: use Chrome or Edge and allow microphone access.
- **`pyaudio` won't install** (terminal voice mode only): Windows `pip install pipwin && pipwin install pyaudio`; macOS `brew install portaudio`; Linux `sudo apt install portaudio19-dev espeak`. Or just use `--hud`.
- **Google login says "access blocked"**: add your Google account as a *Test user* on the OAuth consent screen.

## Tests

```bash
python -m unittest discover -s jarvis/tests -t .
```

They run offline with no keys: the AI, browser, Google, Twilio and maps are all faked.

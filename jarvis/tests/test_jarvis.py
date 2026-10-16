"""Offline tests: no microphone, network, browser, phone or API key needed.

Run from the repository root:  python -m unittest discover -s jarvis/tests -t .
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from jarvis import briefing, builder, config, google_services, leads, llm, phone, skills, tools
from jarvis.__main__ import strip_wake_word
from jarvis.brain import Brain
from jarvis.errors import SetupNeeded


class IsolatedTest(unittest.TestCase):
    """Points JARVIS's data and workspace folders at a temp dir and stubs the browser."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        for name, value in {"DATA_DIR": tmp / "data", "MEMORY_FILE": tmp / "data/memory.json",
                            "LEADS_FILE": tmp / "data/leads.json", "BUSINESS_FILE": tmp / "data/business.json",
                            "WORKSPACE_DIR": tmp / "ws", "GOOGLE_TOKEN_FILE": tmp / "data/token.json",
                            "GOOGLE_CREDENTIALS_FILE": tmp / "data/creds.json", "BUSINESS_DESCRIPTION": ""}.items():
            mock.patch.object(config, name, value).start()
        self.browser = mock.patch("webbrowser.open").start()
        self.opened = mock.patch.object(skills, "open_path").start()
        mock.patch.object(llm, "_active", None).start()
        self.addCleanup(mock.patch.stopall)


def fake_ai(*replies):
    """Install a fake AI backend whose generate() returns `replies` in order."""
    backend = mock.MagicMock()
    backend.generate.side_effect = [r if isinstance(r, str) else json.dumps(r) for r in replies]
    backend.search.return_value = None
    llm._active = backend
    return backend


# --------------------------------------------------------------------------- everyday skills


class LocalCommandTests(IsolatedTest):
    def test_time_and_date(self):
        self.assertIn("It's", skills.handle_local("what time is it?"))
        self.assertIn("Today is", skills.handle_local("What's the date"))

    def test_open_sites(self):
        self.assertEqual(skills.handle_local("open youtube"), "Opening youtube.")
        self.browser.assert_called_with("https://www.youtube.com")
        skills.handle_local("open example.com")
        self.browser.assert_called_with("https://example.com")

    def test_play_and_search(self):
        skills.handle_local("play believer by imagine dragons")
        self.assertIn("search_query=believer+by+imagine+dragons", self.browser.call_args[0][0])
        skills.handle_local("search for python tutorials")
        self.assertIn("q=python+tutorials", self.browser.call_args[0][0])

    def test_wikipedia(self):
        with mock.patch.object(skills, "_fetch", return_value=b'{"extract": "Tesla was an inventor. He was born in 1856. More."}'):
            self.assertEqual(skills.handle_local("who is nikola tesla"), "Tesla was an inventor. He was born in 1856.")

    def test_conversational_questions_go_to_ai(self):
        for text in ("what is your name", "what is 2 plus 2", "write me a poem about the ocean"):
            self.assertIsNone(skills.handle_local(text))

    def test_weather(self):
        with mock.patch.object(skills, "_fetch", return_value="London: Sunny, +18°C".encode()):
            self.assertIn("18 degrees Celsius", skills.handle_local("what's the weather in london"))

    def test_memory_keeps_case(self):
        skills.handle_local("remember that I parked on level 3")
        self.assertIn("I parked on level 3", skills.handle_local("what do you remember?"))

    def test_wake_word(self):
        self.assertEqual(strip_wake_word("Jarvis, open YouTube"), "open youtube")
        self.assertEqual(strip_wake_word("hey jarvis what time is it"), "what time is it")
        self.assertEqual(strip_wake_word("Jarvis"), "")
        self.assertIsNone(strip_wake_word("open youtube"))


# --------------------------------------------------------------------------- tools and AI plumbing


class ToolTests(IsolatedTest):
    def test_every_tool_has_docs_and_schema(self):
        schemas = tools.claude_schemas()
        self.assertEqual(len(schemas), len(tools.ALL))
        for s in schemas:
            self.assertTrue(s["description"], s["name"])
        meeting = next(s for s in schemas if s["name"] == "schedule_meeting")
        self.assertEqual(meeting["input_schema"]["required"], ["title", "start"])
        self.assertEqual(meeting["input_schema"]["properties"]["video_call"]["type"], "boolean")

    def test_run(self):
        self.assertEqual(tools.run("open_website", {"target": "github"}), ("Opening github.", False))
        self.assertTrue(tools.run("nope", {})[1])
        self.assertTrue(tools.run("get_weather", {"bogus": 1})[1])  # bad arguments -> error, no crash

    def test_setup_needed_becomes_answer(self):
        with mock.patch.object(phone, "is_configured", return_value=False):
            output, is_error = tools.run("call_me", {"message": "hi"})
        self.assertFalse(is_error)
        self.assertIn("Not set up yet", output)

    def test_extract_json(self):
        self.assertEqual(llm.extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(llm.extract_json('Sure!\n```json\n[{"a": 1}]\n```'), [{"a": 1}])
        self.assertEqual(llm.extract_json('Here: {"a": [1, 2]} hope that helps'), {"a": [1, 2]})
        with self.assertRaises(llm.AIError):
            llm.extract_json("no json here")


# --------------------------------------------------------------------------- coding


class BuilderTests(IsolatedTest):
    def test_build_project_writes_and_opens(self):
        fake_ai({"summary": "A tip calculator.", "run": "Open index.html.",
                 "files": [{"path": "index.html", "content": "<h1>Tips</h1>"},
                           {"path": "js/app.js", "content": "console.log(1)"}]})
        reply = builder.build_project("Tip Calculator", "a tip calculator")
        root = config.WORKSPACE_DIR / "tip-calculator"
        self.assertEqual((root / "js/app.js").read_text(), "console.log(1)")
        self.assertIn("2 files", reply)
        self.assertTrue(self.browser.call_args[0][0].startswith("file:"))

    def test_refuses_paths_outside_project(self):
        fake_ai({"files": [{"path": "../../evil.txt", "content": "x"}]})
        with self.assertRaises(ValueError):
            builder.build_project("p", "x")
        self.assertFalse((config.WORKSPACE_DIR / "evil.txt").exists())

    def test_improve_sends_existing_code(self):
        root = config.WORKSPACE_DIR / "site"
        root.mkdir(parents=True)
        (root / "index.html").write_text("<p>old</p>")
        ai = fake_ai({"summary": "Dark theme.", "files": [{"path": "index.html", "content": "<p>new</p>"}]})
        builder.improve_project("site", "make it dark")
        self.assertIn("<p>old</p>", ai.generate.call_args[0][0])
        self.assertEqual((root / "index.html").read_text(), "<p>new</p>")
        self.assertIn("site", builder.list_projects())

    def test_needs_ai(self):
        with self.assertRaises(llm.AIError):
            builder.build_project("x", "y")


# --------------------------------------------------------------------------- clients


OSM_RESULTS = [
    {"name": "Smile Dental", "display_name": "Smile Dental, 1 Main St, Austin, Texas, USA",
     "extratags": {"website": "https://smile.example", "email": "hi@smile.example"}},
    {"name": "Bright Teeth", "display_name": "Bright Teeth, 2 Oak Ave, Austin, Texas, USA",
     "extratags": {"contact:phone": "+1 512 555 0100"}},
    {"display_name": "unnamed place"},
]


class LeadTests(IsolatedTest):
    def test_find_clients_from_openstreetmap_without_ai(self):
        with mock.patch.object(leads, "_nominatim", return_value=OSM_RESULTS) as osm:
            reply = leads.find_clients("dentist", "Austin", 5)
        osm.assert_called_once_with("dentist in Austin")
        self.assertIn("Smile Dental", reply)
        saved = leads.all_leads()
        self.assertEqual([l["name"] for l in saved], ["Smile Dental", "Bright Teeth"])
        self.assertEqual(saved[1]["phone"], "+1 512 555 0100")
        # Running again doesn't duplicate.
        with mock.patch.object(leads, "_nominatim", return_value=OSM_RESULTS):
            self.assertIn("already on your client list", leads.find_clients("dentist", "Austin"))

    def test_find_clients_prefers_web_search(self):
        ai = fake_ai()
        ai.search.return_value = '```json\n[{"name": "Acme Co", "website": "acme.example", "why_fit": "Old site."}]\n```'
        with mock.patch.object(leads, "_nominatim") as osm:
            reply = leads.find_clients("companies with outdated websites", "Leeds", 3)
        osm.assert_not_called()
        self.assertIn("Acme Co", reply)
        self.assertEqual(leads.all_leads()[0]["source"], "web search")

    def test_ai_picks_best_osm_matches(self):
        fake_ai({"queries": ["dentist in Austin"]}, [{"index": 1, "why_fit": "No website yet."}])
        leads.set_business_profile("We build websites for local businesses.")
        with mock.patch.object(leads, "_nominatim", return_value=OSM_RESULTS):
            leads.find_clients("dentists", "Austin", 1)
        saved = leads.all_leads()
        self.assertEqual([(l["name"], l["why_fit"]) for l in saved], [("Bright Teeth", "No website yet.")])

    def test_pipeline_management(self):
        with mock.patch.object(leads, "_nominatim", return_value=OSM_RESULTS):
            leads.find_clients("dentist", "Austin")
        self.assertIn("marked as contacted", leads.update_lead("smile", "contacted", "Left voicemail"))
        self.assertIn("1 new, 1 contacted", leads.list_leads())
        self.assertIn("Smile Dental", leads.list_leads("contacted"))
        self.assertIn("must be one of", leads.update_lead("smile", "maybe"))
        self.assertIn("couldn't find", leads.update_lead("nobody", "won"))
        leads.export_csv()
        csv_text = (config.WORKSPACE_DIR / "clients.csv").read_text()
        self.assertIn("Left voicemail", csv_text)

    def test_draft_outreach_opens_mail_app(self):
        with mock.patch.object(leads, "_nominatim", return_value=OSM_RESULTS):
            leads.find_clients("dentist", "Austin")
        self.assertIn("what your business offers", leads.draft_outreach("Smile Dental"))
        leads.set_business_profile("We build websites.")
        fake_ai({"subject": "Quick idea", "body": "Hi there, ..."})
        reply = leads.draft_outreach("Smile Dental")
        self.assertIn("opened it in your mail app", reply)
        self.assertTrue(self.browser.call_args[0][0].startswith("mailto:hi@smile.example?subject=Quick%20idea"))


# --------------------------------------------------------------------------- calendar, phone, updates


class CalendarTests(IsolatedTest):
    def test_not_connected(self):
        with self.assertRaises(SetupNeeded):
            google_services.list_meetings()

    def test_schedule_meeting_builds_event(self):
        service = mock.MagicMock()
        service.events().insert().execute.return_value = {"hangoutLink": "https://meet.google.com/x"}
        with mock.patch.object(google_services, "_service", return_value=service):
            reply = google_services.schedule_meeting("Kickoff", "2026-10-20T15:00", 45, "a@x.com, b@y.com")
        kwargs = service.events().insert.call_args.kwargs
        body = kwargs["body"]
        start = datetime.fromisoformat(body["start"]["dateTime"])
        self.assertEqual((start.hour, start.minute), (15, 0))
        self.assertIsNotNone(start.tzinfo)
        self.assertEqual(datetime.fromisoformat(body["end"]["dateTime"]) - start, timedelta(minutes=45))
        self.assertEqual(body["attendees"], [{"email": "a@x.com"}, {"email": "b@y.com"}])
        self.assertEqual(kwargs["sendUpdates"], "all")
        self.assertIn("sent invites to a@x.com, b@y.com", reply)
        self.assertIn("Google Meet", reply)

    def test_bad_start_time(self):
        with mock.patch.object(google_services, "_service"), self.assertRaises(ValueError):
            google_services.schedule_meeting("x", "next tuesday-ish")


class PhoneTests(IsolatedTest):
    def test_call_escapes_message(self):
        client = mock.MagicMock()
        with mock.patch.object(phone, "is_configured", return_value=True), \
                mock.patch.object(phone, "_client", return_value=client):
            phone.call_me("Sales < target & rising")
        twiml = client.calls.create.call_args.kwargs["twiml"]
        self.assertIn("Sales &lt; target &amp; rising", twiml)


class SchedulerTests(IsolatedTest):
    def test_daily_briefing_once_and_reminders(self):
        heard = []
        sched = briefing.Scheduler(announce=heard.append)
        now = datetime(2026, 10, 19, 8, 31)
        with mock.patch.object(config, "BRIEFING_TIME", "08:30"), \
                mock.patch.object(briefing, "business_briefing", return_value="Morning report."), \
                mock.patch.object(google_services, "is_authorized", return_value=False):
            sched.tick(now)
            sched.tick(now + timedelta(minutes=1))
        self.assertEqual(heard, ["Morning report."])

        soon = (datetime.now().astimezone() + timedelta(minutes=8)).isoformat()
        event = {"id": "e1", "summary": "Client call", "start": {"dateTime": soon}}
        with mock.patch.object(google_services, "is_authorized", return_value=True), \
                mock.patch.object(google_services, "upcoming_events", return_value=[event]):
            sched.tick(datetime.now())
            sched.tick(datetime.now())
        self.assertEqual(len(heard), 2)
        self.assertRegex(heard[1], r"Reminder: Client call starts in [78] minutes")

    def test_late_start_skips_stale_briefing(self):
        heard = []
        with mock.patch.object(config, "BRIEFING_TIME", "08:30"), \
                mock.patch.object(google_services, "is_authorized", return_value=False):
            briefing.Scheduler(announce=heard.append).tick(datetime(2026, 10, 19, 15, 0))
        self.assertEqual(heard, [])

    def test_briefing_without_ai(self):
        with mock.patch.object(skills, "_fetch", side_effect=OSError):
            text = briefing.business_briefing()
        self.assertIn("Today is", text)
        self.assertIn("Calendar and email are not connected", text)


# --------------------------------------------------------------------------- the brain


def _content(*parts):
    from google.genai import types
    return types.Content(role="model", parts=list(parts))


class BrainTests(IsolatedTest):
    def test_offline(self):
        with mock.patch.object(llm, "create_backend", return_value=None):
            brain = Brain()
        self.assertIn("offline", brain.respond("write me a poem"))
        self.assertIn("It's", brain.respond("what time is it"))
        self.assertIn("not connected", brain.respond("business update"))
        self.assertIn("isn't set up yet", brain.respond("what's on my calendar today"))

    def test_gemini_tool_loop(self):
        from google.genai import types
        with mock.patch.object(config, "GEMINI_API_KEY", "test-key"), mock.patch.object(config, "PROVIDER", "gemini"):
            brain = Brain()
        backend = brain.backend
        call = types.Part.from_function_call(name="open_website", args={"target": "github"})
        responses = [
            SimpleNamespace(candidates=[SimpleNamespace(content=_content(call))],
                            function_calls=[call.function_call], text=None),
            SimpleNamespace(candidates=[SimpleNamespace(content=_content(types.Part.from_text(text="GitHub is open.")))],
                            function_calls=None, text="GitHub is open."),
        ]
        with mock.patch.object(backend.client.models, "generate_content", side_effect=responses) as gen:
            self.assertEqual(brain.respond("pull up my code site"), "GitHub is open.")
        self.browser.assert_called_with("https://github.com")
        self.assertEqual(gen.call_count, 2)
        roles = [c.role for c in backend.history]
        self.assertEqual(roles, ["user", "model", "user", "model"])
        self.assertEqual(backend.history[2].parts[0].function_response.response, {"result": "Opening github."})

    def test_gemini_falls_back_to_next_model(self):
        from google.genai import errors
        with mock.patch.object(config, "GEMINI_API_KEY", "test-key"), mock.patch.object(config, "PROVIDER", "gemini"):
            brain = Brain()
        backend = brain.backend
        overloaded = errors.ServerError(503, {"error": {"message": "busy"}})
        ok = SimpleNamespace(text="Hello", candidates=[])
        with mock.patch.object(backend.client.models, "generate_content", side_effect=[overloaded, ok]) as gen:
            self.assertEqual(llm.generate("hi"), "Hello")
        self.assertEqual([c.kwargs["model"] for c in gen.call_args_list], config.GEMINI_MODELS[:2])
        self.assertEqual(backend.preferred, 1)

    def test_gemini_failed_turn_is_rolled_back(self):
        from google.genai import errors
        with mock.patch.object(config, "GEMINI_API_KEY", "test-key"), mock.patch.object(config, "PROVIDER", "gemini"):
            brain = Brain()
        quota = errors.ClientError(429, {"error": {"message": "quota"}})
        with mock.patch.object(brain.backend.client.models, "generate_content", side_effect=quota):
            self.assertIn("usage limit", brain.respond("tell me something interesting"))
        self.assertEqual(brain.backend.history, [])


if __name__ == "__main__":
    unittest.main()

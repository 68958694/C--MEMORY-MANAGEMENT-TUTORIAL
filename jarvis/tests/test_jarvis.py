"""Offline tests: no microphone, network, browser or API key needed.

Run from the repository root:  python -m unittest discover -s jarvis/tests -t .
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from jarvis import config, skills
from jarvis.__main__ import strip_wake_word
from jarvis.brain import Brain


class LocalCommandTests(unittest.TestCase):
    def setUp(self):
        self.browser = mock.patch("webbrowser.open").start()
        tmp = Path(tempfile.mkdtemp())
        mock.patch.object(config, "DATA_DIR", tmp).start()
        mock.patch.object(config, "MEMORY_FILE", tmp / "memory.json").start()
        self.addCleanup(mock.patch.stopall)

    def test_time_and_date(self):
        self.assertIn("It's", skills.handle_local("what time is it?"))
        self.assertIn("Today is", skills.handle_local("What's the date"))

    def test_open_known_site(self):
        self.assertEqual(skills.handle_local("open youtube"), "Opening youtube.")
        self.browser.assert_called_once_with("https://www.youtube.com")

    def test_open_domain(self):
        skills.handle_local("open example.com")
        self.browser.assert_called_once_with("https://example.com")

    def test_play_on_youtube(self):
        reply = skills.handle_local("play believer by imagine dragons")
        self.assertIn("YouTube", reply)
        self.assertIn("search_query=believer+by+imagine+dragons", self.browser.call_args[0][0])

    def test_google_search(self):
        skills.handle_local("search for python tutorials")
        self.assertIn("q=python+tutorials", self.browser.call_args[0][0])

    def test_wikipedia(self):
        with mock.patch.object(skills, "_fetch", return_value=b'{"extract": "Tesla was an inventor. He was born in 1856. More."}'):
            self.assertEqual(skills.handle_local("who is nikola tesla"),
                             "Tesla was an inventor. He was born in 1856.")

    def test_conversational_questions_go_to_claude(self):
        self.assertIsNone(skills.handle_local("what is your name"))
        self.assertIsNone(skills.handle_local("what is 2 plus 2"))
        self.assertIsNone(skills.handle_local("write me a poem about the ocean"))

    def test_weather(self):
        with mock.patch.object(skills, "_fetch", return_value="London: Sunny, +18°C, feels like +17°C".encode()) as f:
            reply = skills.handle_local("what's the weather in london")
        self.assertIn("/London?", f.call_args[0][0].title())
        self.assertIn("18 degrees Celsius", reply)

    def test_memory_round_trip(self):
        self.assertIn("haven't", skills.handle_local("what do you remember"))
        skills.handle_local("remember that I parked on level 3")
        self.assertIn("I parked on level 3", skills.handle_local("what do you remember?"))

    def test_joke(self):
        self.assertIn(skills.handle_local("tell me a joke"), skills.JOKES)

    def test_tools_match_functions(self):
        for tool in skills.TOOLS:
            self.assertIn(tool["name"], skills._TOOL_FUNCS)
        self.assertIn("Opening", skills.run_tool("open_website", {"target": "github"}))


class WakeWordTests(unittest.TestCase):
    def test_strip_wake_word(self):
        self.assertEqual(strip_wake_word("Jarvis, open YouTube"), "open youtube")
        self.assertEqual(strip_wake_word("hey jarvis what time is it"), "what time is it")
        self.assertEqual(strip_wake_word("Jarvis"), "")
        self.assertIsNone(strip_wake_word("open youtube"))


def _block(**kw):
    return SimpleNamespace(**kw)


class BrainTests(unittest.TestCase):
    def setUp(self):
        mock.patch("webbrowser.open").start()
        self.addCleanup(mock.patch.stopall)

    def test_offline_brain(self):
        brain = Brain(use_claude=False)
        self.assertIn("offline", brain.respond("write me a poem"))
        self.assertIn("It's", brain.respond("what time is it"))

    def test_claude_tool_loop(self):
        brain = Brain(use_claude=True)
        tool_call = SimpleNamespace(stop_reason="tool_use", content=[
            _block(type="tool_use", id="t1", name="open_website", input={"target": "github"})])
        final = SimpleNamespace(stop_reason="end_turn", content=[
            _block(type="text", text="GitHub is open, sir.")])
        client = mock.MagicMock()
        client.beta.messages.create.side_effect = [tool_call, final]
        brain._client = client

        self.assertEqual(brain.respond("pull up my code hosting site"), "GitHub is open, sir.")
        tool_result = brain.history[2]["content"][0]
        self.assertEqual(tool_result["tool_use_id"], "t1")
        self.assertEqual(tool_result["content"], "Opening github.")
        self.assertEqual([m["role"] for m in brain.history], ["user", "assistant", "user", "assistant"])

    def test_failed_request_is_rolled_back(self):
        import anthropic

        brain = Brain(use_claude=True)
        client = mock.MagicMock()
        client.beta.messages.create.side_effect = anthropic.APIConnectionError(
            request=mock.MagicMock())
        brain._client = client
        self.assertIn("internet", brain.respond("tell me something interesting"))
        self.assertEqual(brain.history, [])


if __name__ == "__main__":
    unittest.main()

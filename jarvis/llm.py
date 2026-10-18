"""The AI models behind JARVIS: Google Gemini (default) or Anthropic Claude.

Both backends offer the same three things:
  chat(text)                         - conversation with memory, can call JARVIS's tools
  generate(prompt, json_mode=False)  - one-off request (writing code, emails, briefings)
  search(prompt)                     - answer using live web search, or None if unavailable

Other modules use the module-level `generate()` / `search()` / `available()`
helpers, which go to whichever backend the Brain activated.
"""

import json
import re

from jarvis import config, tools

_active = None  # the backend the Brain is using


class AIError(Exception):
    """A failure worth saying out loud (no key, quota, outage...)."""


def available() -> bool:
    return _active is not None


def generate(prompt: str, json_mode: bool = False) -> str:
    if _active is None:
        raise AIError("My AI core is offline, so I can't do that. Add a GEMINI_API_KEY to enable it.")
    return _active.generate(prompt, json_mode=json_mode)


def generate_json(prompt: str):
    return extract_json(generate(prompt, json_mode=True))


def search(prompt: str) -> str | None:
    return _active.search(prompt) if _active is not None else None


def extract_json(text: str):
    """Parse JSON from a model reply, tolerating ```json fences or chatter around it."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if starts:
        start = min(starts)
        end = max(text.rfind("}"), text.rfind("]"))
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise AIError("The AI returned something I couldn't read. Please try again.")


def create_backend(system_prompt: str):
    """Pick and activate a backend from config. Returns None when no key is configured."""
    global _active
    provider = config.PROVIDER
    if not provider:
        provider = "gemini" if config.GEMINI_API_KEY else "claude" if _has_claude_credentials() else ""
    if provider == "gemini":
        _active = GeminiBackend(system_prompt)
    elif provider == "claude":
        _active = ClaudeBackend(system_prompt)
    else:
        _active = None
    return _active


def _has_claude_credentials() -> bool:
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


# =============================================================================== Gemini


class GeminiBackend:
    name = "Gemini"

    def __init__(self, system_prompt: str):
        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:
            raise AIError("The Gemini package is missing. Run: pip install google-genai") from exc
        if not config.GEMINI_API_KEY:
            raise AIError("GEMINI_API_KEY is not set.")
        if "paste-your" in config.GEMINI_API_KEY or " " in config.GEMINI_API_KEY:
            raise AIError("The GEMINI_API_KEY line in your .env file still has the placeholder text or a space in it. "
                          "Paste your real key right after the equals sign, save, and restart me.")
        self.types, self.errors = types, errors
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.models = config.GEMINI_MODELS
        self.preferred = 0       # index of the last model that worked
        self.history: list = []  # the conversation, as Gemini Content objects
        self.search_ok = True
        self.chat_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools.ALL,
            # We run tools ourselves so a failed request can be retried without repeating actions.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def _generate(self, contents, cfg, fallback: bool = True):
        """One request, moving down the model list if a model is overloaded or out of quota."""
        order = self.models[self.preferred:] + self.models[:self.preferred]
        last = None
        for model in order if fallback else order[:1]:
            try:
                response = self.client.models.generate_content(model=model, contents=contents, config=cfg)
                self.preferred = self.models.index(model)
                return response
            except self.errors.APIError as exc:
                last = exc
                # Overloaded (503), out of quota for this model (429), or retired (404): try the next.
                if exc.code not in (429, 500, 503, 404):
                    break
        raise _gemini_error(last)

    def chat(self, text: str) -> str:
        types = self.types
        turn_start = len(self.history)
        self.history.append(types.Content(role="user", parts=[types.Part.from_text(text=text)]))
        try:
            for _ in range(15):  # tool-use rounds
                response = self._generate(self.history, self.chat_config)
                if not response.candidates or response.candidates[0].content is None:
                    del self.history[turn_start:]
                    return f"I'm afraid I can't help with that one, {config.USER_TITLE}."
                self.history.append(response.candidates[0].content)
                calls = response.function_calls
                if not calls:
                    return (response.text or "").strip()
                parts = []
                for call in calls:
                    output, is_error = tools.run(call.name, dict(call.args or {}))
                    parts.append(types.Part.from_function_response(
                        name=call.name, response={"error": output} if is_error else {"result": output}))
                self.history.append(types.Content(role="user", parts=parts))
            return f"That took more steps than expected, {config.USER_TITLE}."
        except AIError:
            if len(self.history) > turn_start + 1:
                # Tools already ran: keep their results so the next message has context,
                # and close the turn so the conversation stays valid.
                self.history.append(types.Content(role="model", parts=[types.Part.from_text(
                    text="(I was interrupted before I could reply.)")]))
            else:
                del self.history[turn_start:]
            raise

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        cfg = self.types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
        return (self._generate(prompt, cfg).text or "").strip()

    def search(self, prompt: str) -> str | None:
        """Answer with Google Search grounding. Needs billing enabled on the API key."""
        if not self.search_ok:
            return None
        types = self.types
        cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        try:
            response = self._generate(prompt, cfg, fallback=False)
        except AIError:
            # Free-tier keys get "quota exceeded" for search grounding; don't waste calls retrying.
            self.search_ok = False
            return None
        return (response.text or "").strip()


def _gemini_error(exc) -> AIError:
    code = getattr(exc, "code", None)
    if code == 429:
        return AIError("I've hit the Gemini usage limit for now. Give me a minute, or enable billing on your key.")
    if code in (500, 503):
        return AIError("Gemini is overloaded right now. Please try again in a moment.")
    if code in (401, 403):
        return AIError("Gemini rejected the API key. Please check GEMINI_API_KEY.")
    if code == 400 and "API key not valid" in str(getattr(exc, "message", "") or exc):
        return AIError("Google says the Gemini API key is not valid. Copy a fresh key from "
                       "aistudio.google.com/apikey into the GEMINI_API_KEY line of your .env file, then restart me.")
    if code == 400:
        return AIError(f"Gemini couldn't process that request: {getattr(exc, 'message', exc)}")
    if isinstance(exc, AIError):
        return exc
    return AIError(f"My AI core had a problem: {exc}")


# =============================================================================== Claude


class ClaudeBackend:
    name = "Claude"

    def __init__(self, system_prompt: str):
        try:
            import anthropic
        except ImportError as exc:
            raise AIError("The Anthropic package is missing. Run: pip install anthropic") from exc
        self.anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.system = system_prompt
        self.history: list = []  # appended to only, so the model keeps full context
        self.schemas = tools.claude_schemas()

    def _create(self, **kwargs):
        try:
            return self.client.beta.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=16000,
                output_config={"effort": config.CLAUDE_EFFORT},
                # If the model declines a request, the API retries it on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                **kwargs,
            )
        except self.anthropic.AuthenticationError as exc:
            raise AIError("Claude rejected the API key. Please check ANTHROPIC_API_KEY.") from exc
        except self.anthropic.RateLimitError as exc:
            raise AIError("I'm being rate limited at the moment. Give me a few seconds.") from exc
        except self.anthropic.APIConnectionError as exc:
            raise AIError("I can't reach my AI core. Please check your internet connection.") from exc
        except self.anthropic.APIStatusError as exc:
            raise AIError(f"My AI core returned an error, status {exc.status_code}.") from exc

    def chat(self, text: str) -> str:
        turn_start = len(self.history)
        self.history.append({"role": "user", "content": text})
        try:
            for _ in range(10):  # tool-use rounds
                response = self._create(system=self.system, messages=self.history, tools=self.schemas,
                                        cache_control={"type": "ephemeral"})
                self.history.append({"role": "assistant", "content": response.content})
                if response.stop_reason == "refusal":
                    return f"I'm afraid I can't help with that one, {config.USER_TITLE}."
                if response.stop_reason != "tool_use":
                    return _text(response.content)
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        output, is_error = tools.run(block.name, block.input)
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": output, "is_error": is_error})
                self.history.append({"role": "user", "content": results})
            return f"That took more steps than expected, {config.USER_TITLE}."
        except AIError:
            # Drop the failed turn so a dangling message doesn't break later requests.
            del self.history[turn_start:]
            raise

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        if json_mode:
            prompt += "\n\nRespond with only valid JSON, no other text."
        response = self._create(messages=[{"role": "user", "content": prompt}])
        return _text(response.content)

    def search(self, prompt: str) -> str | None:
        messages = [{"role": "user", "content": prompt}]
        web = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
        for _ in range(5):
            response = self._create(messages=messages, tools=web)
            if response.stop_reason != "pause_turn":
                return _text(response.content)
            messages.append({"role": "assistant", "content": response.content})
        return _text(response.content)


def _text(content) -> str:
    return " ".join(b.text for b in content if b.type == "text").strip()

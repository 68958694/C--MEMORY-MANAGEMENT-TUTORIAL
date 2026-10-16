"""JARVIS's brain: built-in commands first, Claude (with tools) for everything else."""

from datetime import datetime

import anthropic

from jarvis import config, memory, skills

SYSTEM_PROMPT = f"""You are {config.NAME}, a personal AI assistant modelled on Tony Stark's J.A.R.V.I.S.:
calm, witty, loyal and very competent, with a dry British sense of humour. You address
the user as "{config.USER_TITLE}".

Your replies are read aloud by a text-to-speech voice, so:
- Keep them short: one to three sentences unless the user asks for detail.
- Use plain spoken sentences. No markdown, bullet points, code blocks, emoji or URLs.

You run on the user's own computer and have tools to open websites and apps, search,
check the weather, report system status, and save or recall notes. Use a tool whenever
it fits the request instead of telling the user how to do it themselves. After using a
tool, briefly confirm what you did."""


def _system_prompt() -> str:
    notes = memory.recall()
    prompt = SYSTEM_PROMPT
    if notes:
        prompt += "\n\nThings the user asked you to remember:\n" + "\n".join(f"- {n}" for n in notes)
    return prompt


class Brain:
    def __init__(self, use_claude: bool = True):
        self.use_claude = use_claude
        self._client: anthropic.Anthropic | None = None
        # Full conversation, appended to only (never edited) so Claude keeps context.
        self.history: list = []
        # Fixed for the session so the prompt prefix stays cacheable.
        self.system = _system_prompt()

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def respond(self, text: str) -> str:
        text = text.strip()
        if not text:
            return f"Yes, {config.USER_TITLE}?"

        reply = skills.handle_local(text)
        if reply is not None:
            return reply

        if not self.use_claude:
            return ("I don't have a built-in command for that, and my AI core is offline. "
                    "Set an Anthropic API key to enable conversation.")
        return self._ask_claude(text)

    def _ask_claude(self, text: str) -> str:
        turn_start = len(self.history)
        stamp = datetime.now().strftime("%A %d %B %Y, %I:%M %p")
        self.history.append({"role": "user", "content": f"[{stamp}] {text}"})
        try:
            return self._run_turn()
        except Exception as exc:
            # Drop the failed turn so a dangling user message or unanswered
            # tool call doesn't break every request after it.
            del self.history[turn_start:]
            return _error_reply(exc)

    def _run_turn(self) -> str:
        # Loop while Claude is calling tools; at most a few rounds per request.
        for _ in range(6):
            response = self.client.beta.messages.create(
                model=config.MODEL,
                max_tokens=16000,
                system=self.system,
                messages=self.history,
                tools=skills.TOOLS,
                output_config={"effort": config.EFFORT},
                # If the model declines a request, the API retries it on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                cache_control={"type": "ephemeral"},
            )
            # Keep every block (thinking included) so the next turn has full context.
            self.history.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return f"I'm afraid I can't help with that one, {config.USER_TITLE}."
            if response.stop_reason != "tool_use":
                return _spoken_text(response.content) or f"Done, {config.USER_TITLE}."

            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    output, is_error = skills.run_tool(block.name, block.input), False
                except Exception as exc:  # report tool failures back to Claude
                    output, is_error = f"Error: {exc}", True
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})
            self.history.append({"role": "user", "content": results})
        return f"That took more steps than expected, {config.USER_TITLE}. Shall I try again?"


def _error_reply(exc: Exception) -> str:
    if isinstance(exc, anthropic.AuthenticationError):
        return "My AI core rejected the API key. Please check your ANTHROPIC_API_KEY."
    if isinstance(exc, anthropic.RateLimitError):
        return "I'm being rate limited at the moment. Give me a few seconds."
    if isinstance(exc, anthropic.APIConnectionError):
        return "I can't reach my AI core. Please check your internet connection."
    if isinstance(exc, anthropic.APIStatusError):
        return f"My AI core returned an error, status {exc.status_code}."
    if isinstance(exc, TypeError) and "auth" in str(exc).lower():
        # The SDK raises this when no API key or login is configured.
        return "I need an Anthropic API key for that. Set ANTHROPIC_API_KEY and restart me."
    raise exc


def _spoken_text(content) -> str:
    return " ".join(b.text for b in content if b.type == "text").strip()


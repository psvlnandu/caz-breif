"""Thin wrapper around the Claude API shared by every pipeline step."""

import json

import anthropic

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


class Refused(RuntimeError):
    pass


def call(model: str, system: str, messages: list, *, effort: str = "medium",
         tools: list | None = None, schema: dict | None = None, max_tokens: int = 16000):
    """One request with server-side refusal fallback; resumes server-tool turns that pause."""
    extra = {}
    if tools:
        extra["tools"] = tools
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    original = list(messages)
    for _ in range(6):
        response = _client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config=output_config,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **extra,
        )
        if response.stop_reason == "refusal":
            raise Refused(f"request declined: {response.stop_details}")
        if response.stop_reason != "pause_turn":
            break
        # Long web-search turn paused server-side: hand it back to continue.
        messages = original + [{"role": "assistant", "content": response.content}]

    text = "".join(b.text for b in response.content if b.type == "text")
    return json.loads(text) if schema else text

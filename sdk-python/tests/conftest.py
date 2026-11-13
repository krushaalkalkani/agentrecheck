from __future__ import annotations

import json
from types import SimpleNamespace as NS

import pytest


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test gets its own trace dir and no cloud/judge credentials."""
    monkeypatch.setenv("AGENTRECHECK_DIR", str(tmp_path / ".agentrecheck"))
    monkeypatch.setenv("COLUMNS", "200")
    for var in (
        "AGENTRECHECK_API_KEY",
        "AGENTRECHECK_API_URL",
        "AGENTRECHECK_JUDGE_MODEL",
        "AGENTRECHECK_DISABLED",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_STEP_SUMMARY",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


class FakeCompletions:
    """Mimics ``client.chat.completions`` with scripted responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def chat_response(content=None, tool_calls=None, model="gpt-4o-mini", usage=(100, 20)):
    calls = [
        NS(id=f"call_{i}", function=NS(name=name, arguments=json.dumps(args)))
        for i, (name, args) in enumerate(tool_calls or [])
    ]
    return NS(
        model=model,
        choices=[NS(message=NS(content=content, tool_calls=calls or None))],
        usage=NS(prompt_tokens=usage[0], completion_tokens=usage[1]),
    )


def fake_openai(responses):
    return NS(chat=NS(completions=FakeCompletions(responses)))

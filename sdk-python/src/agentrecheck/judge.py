"""Optional LLM-as-judge. Uses the user's own API key and provider SDK."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from pydantic import BaseModel

SYSTEM_PROMPT = (
    "You are a strict evaluator of AI agent outputs. You are given the agent's input, "
    "its final output, and a rubric. Score how well the output satisfies the rubric from "
    "0.0 (fails completely) to 1.0 (fully satisfies). Respond with only a JSON object: "
    '{"score": <number between 0 and 1>, "reasoning": "<one or two sentences>"}'
)

DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-opus-5-5"}


class JudgeError(Exception):
    pass


class JudgeResult(BaseModel):
    score: float
    reasoning: str = ""


class Judge(Protocol):
    def score(self, *, rubric: str, input: Any, output: Any) -> JudgeResult: ...


def build_prompt(rubric: str, input: Any, output: Any) -> str:
    def text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, indent=2, default=str)

    return (
        f"<rubric>\n{rubric}\n</rubric>\n\n"
        f"<agent_input>\n{text(input)}\n</agent_input>\n\n"
        f"<agent_output>\n{text(output)}\n</agent_output>"
    )


def parse_judgement(text: str) -> JudgeResult:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise JudgeError(f"Judge did not return JSON: {text[:200]!r}")
    try:
        data = json.loads(match.group(0))
        score = float(data["score"])
    except (ValueError, KeyError, TypeError) as exc:
        raise JudgeError(f"Could not parse judge response: {text[:200]!r}") from exc
    return JudgeResult(score=max(0.0, min(1.0, score)), reasoning=str(data.get("reasoning", "")))


class OpenAIJudge:
    def __init__(self, model: str = DEFAULT_MODELS["openai"], client: Any = None) -> None:
        self.model = model
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise JudgeError(
                    "Install the judge extra: pip install 'agentrecheck[openai]'"
                ) from exc
            client = OpenAI()
        self._client = client

    def score(self, *, rubric: str, input: Any, output: Any) -> JudgeResult:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(rubric, input, output)},
            ],
        )
        return parse_judgement(response.choices[0].message.content or "")


class AnthropicJudge:
    def __init__(self, model: str = DEFAULT_MODELS["anthropic"], client: Any = None) -> None:
        self.model = model
        if client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise JudgeError(
                    "Install the judge extra: pip install 'agentrecheck[anthropic]'"
                ) from exc
            client = Anthropic()
        self._client = client

    def score(self, *, rubric: str, input: Any, output: Any) -> JudgeResult:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_prompt(rubric, input, output)}],
        )
        if getattr(response, "stop_reason", None) == "refusal":
            raise JudgeError("The judge model declined to evaluate this output.")
        text = "".join(
            getattr(block, "text", "")
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        return parse_judgement(text)


def judge_from_env(spec: str | None = None) -> Judge | None:
    """Build a judge from ``<provider>:<model>`` or from whichever API key is set.

    Returns None when no key is available, in which case judge checks are skipped.
    """
    spec = spec or os.environ.get("AGENTRECHECK_JUDGE_MODEL")
    explicit = bool(spec)
    if spec:
        provider, _, model = spec.partition(":")
    elif os.environ.get("OPENAI_API_KEY"):
        provider, model = "openai", ""
    elif os.environ.get("ANTHROPIC_API_KEY"):
        provider, model = "anthropic", ""
    else:
        return None

    if provider not in DEFAULT_MODELS:
        raise JudgeError(
            f"Unknown judge provider '{provider}'. Use 'openai:<model>' or 'anthropic:<model>'."
        )
    key_var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(key_var):
        return None
    judge_cls = OpenAIJudge if provider == "openai" else AnthropicJudge
    try:
        return judge_cls(model or DEFAULT_MODELS[provider])
    except JudgeError:
        # A key happens to be in the environment but the provider SDK is not
        # installed. Only treat that as an error when a judge was asked for.
        if explicit:
            raise
        return None

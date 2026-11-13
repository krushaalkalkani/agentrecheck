from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from agentrecheck import storage
from agentrecheck.assertions import evaluate, is_subsequence, judge_score
from agentrecheck.judge import (
    AnthropicJudge,
    JudgeError,
    JudgeResult,
    OpenAIJudge,
    judge_from_env,
    parse_judgement,
)
from agentrecheck.models import Case, LLMStep, ToolStep, Trace
from agentrecheck.snapshot import snapshot_trace


def make_trace(
    tools=(
        ("lookup_order", {"order_id": "A100"}),
        ("issue_refund", {"order_id": "A100", "amount": 49.5}),
    ),
    output="Your refund has been issued.",
    cost_tokens=(1000, 100),
):
    tr = Trace(name="agent", input={"args": ["refund A100"], "kwargs": {}}, output=output)
    tr.add(
        LLMStep(
            model="gpt-4o-mini",
            input_tokens=cost_tokens[0],
            output_tokens=cost_tokens[1],
            cost_usd=0.00021,
        )
    )
    for name, args in tools:
        tr.add(ToolStep(name=name, args=args, result="ok"))
    tr.latency_ms = 800
    return tr


def case_with(assertions: dict) -> Case:
    return Case.model_validate({"id": "c", "assertions": assertions})


def statuses(checks):
    return {c.name: c.status for c in checks}


def test_sequence_exact_and_subset():
    tr = make_trace()
    exact = case_with({"tools": {"sequence": ["lookup_order", "issue_refund"]}})
    assert [c.status for c in evaluate(exact, tr)] == ["pass"]

    wrong = case_with({"tools": {"sequence": ["issue_refund"]}})
    [check] = evaluate(wrong, tr)
    assert check.status == "fail" and "lookup_order" in check.message

    subset = case_with({"tools": {"sequence": ["issue_refund"], "mode": "subset"}})
    assert evaluate(subset, tr)[0].status == "pass"

    out_of_order = case_with(
        {"tools": {"sequence": ["issue_refund", "lookup_order"], "mode": "subset"}}
    )
    assert evaluate(out_of_order, tr)[0].status == "fail"
    assert is_subsequence([], ["a"]) and not is_subsequence(["a", "a"], ["a"])


def test_tool_args_exact_regex_schema():
    tr = make_trace()
    case = case_with(
        {
            "tools": {
                "args": [
                    {"tool": "lookup_order", "exact": {"order_id": "A100"}},
                    {"tool": "issue_refund", "regex": {"order_id": "^A\\d+$", "amount": "^49"}},
                    {
                        "tool": "issue_refund",
                        "json_schema": {
                            "type": "object",
                            "required": ["order_id", "amount"],
                            "properties": {"amount": {"type": "number", "maximum": 100}},
                        },
                    },
                ]
            }
        }
    )
    assert set(statuses(evaluate(case, tr)).values()) == {"pass"}

    bad = case_with(
        {
            "tools": {
                "args": [
                    {"tool": "lookup_order", "exact": {"order_id": "B2"}},
                    {"tool": "issue_refund", "regex": {"order_id": "^B", "reason": "x"}},
                    {
                        "tool": "issue_refund",
                        "json_schema": {"properties": {"amount": {"maximum": 10}}},
                    },
                    {"tool": "issue_refund", "index": 1, "exact": {}},
                    {"tool": "lookup_order", "json_schema": {"type": "nonsense"}},
                ]
            }
        }
    )
    checks = evaluate(bad, tr)
    assert [c.status for c in checks] == ["fail"] * 5
    assert "missing arg 'reason'" in checks[1].message
    assert "called 1 time(s)" in checks[3].message


def test_output_checks():
    tr = make_trace()
    case = case_with(
        {
            "output": {
                "contains": ["REFUND"],
                "not_contains": ["sorry"],
                "regex": "refund has been \\w+",
            }
        }
    )
    assert set(statuses(evaluate(case, tr)).values()) == {"pass"}
    bad = case_with(
        {"output": {"contains": ["tracking"], "not_contains": ["refund"], "regex": "^$"}}
    )
    assert [c.status for c in evaluate(bad, tr)] == ["fail", "fail", "fail"]
    # Non-string outputs are JSON-encoded before matching.
    tr.output = {"status": "refunded"}
    assert evaluate(case_with({"output": {"contains": ["refunded"]}}), tr)[0].status == "pass"


def test_budgets():
    tr = make_trace()
    ok = case_with({"budgets": {"max_cost_usd": 0.001, "max_latency_ms": 1000, "max_steps": 3}})
    assert set(statuses(evaluate(ok, tr)).values()) == {"pass"}
    over = case_with({"budgets": {"max_cost_usd": 0.0001, "max_latency_ms": 100, "max_steps": 2}})
    assert [c.status for c in evaluate(over, tr)] == ["fail", "fail", "fail"]


class FixedJudge:
    def __init__(self, score=0.9, exc=None):
        self._score, self._exc = score, exc

    def score(self, *, rubric, input, output):
        if self._exc:
            raise self._exc
        return JudgeResult(score=self._score, reasoning="looks right")


def test_judge_pass_fail_skip_error():
    tr = make_trace()
    case = case_with({"output": {"judge": {"rubric": "Confirms the refund.", "min_score": 0.8}}})

    [skipped] = evaluate(case, tr, judge=None)
    assert skipped.status == "skip"

    passed = evaluate(case, tr, judge=FixedJudge(0.9))
    assert passed[0].status == "pass" and judge_score(passed) == pytest.approx(0.9)

    assert evaluate(case, tr, judge=FixedJudge(0.5))[0].status == "fail"
    errored = evaluate(case, tr, judge=FixedJudge(exc=RuntimeError("timeout")))
    assert errored[0].status == "fail" and "judge error" in errored[0].message
    assert judge_score(errored) is None


def test_parse_judgement():
    assert parse_judgement('Sure: {"score": 1.7, "reasoning": "great"}').score == 1.0
    with pytest.raises(JudgeError):
        parse_judgement("no json here")
    with pytest.raises(JudgeError):
        parse_judgement('{"reasoning": "missing score"}')


def test_openai_and_anthropic_judges_with_injected_clients():
    oa = NS(
        chat=NS(
            completions=NS(
                create=lambda **kw: NS(
                    choices=[NS(message=NS(content='{"score": 0.8, "reasoning": "ok"}'))]
                )
            )
        )
    )
    assert OpenAIJudge(client=oa).score(rubric="r", input="i", output={"a": 1}).score == 0.8

    def anthropic_client(stop_reason="end_turn"):
        return NS(
            messages=NS(
                create=lambda **kw: NS(
                    stop_reason=stop_reason,
                    content=[NS(type="thinking"), NS(type="text", text='{"score": 0.25}')],
                )
            )
        )

    assert (
        AnthropicJudge(client=anthropic_client()).score(rubric="r", input="i", output="o").score
        == 0.25
    )
    with pytest.raises(JudgeError, match="declined"):
        AnthropicJudge(client=anthropic_client("refusal")).score(rubric="r", input="i", output="o")


def test_judge_from_env(monkeypatch):
    assert judge_from_env() is None
    assert judge_from_env("openai:gpt-4o-mini") is None  # spec set but no key: skip
    with pytest.raises(JudgeError, match="Unknown judge provider"):
        judge_from_env("llama:local")


def test_snapshot_roundtrip(tmp_path):
    tr = make_trace()
    case = snapshot_trace(tr, case_id="refund", name="Refund flow")
    assert case.input.args == ["refund A100"]
    assert case.baseline.tool_sequence == ["lookup_order", "issue_refund"]
    assert case.baseline.steps == 3
    assert case.assertions.tools.sequence == ["lookup_order", "issue_refund"]
    assert case.assertions.budgets.max_steps == 6
    assert case.assertions.budgets.max_cost_usd == pytest.approx(0.00042)

    path = storage.save_case(case, tmp_path / "cases")
    [loaded] = storage.load_cases(tmp_path / "cases")
    assert loaded == case and path.name == "refund.yaml"
    assert set(statuses(evaluate(loaded, tr)).values()) == {"pass"}

    # Raw (non args/kwargs) inputs become a single positional arg.
    plain = snapshot_trace(Trace(name="My Agent", input="hello"))
    assert plain.input.args == ["hello"] and plain.id.startswith("my_agent_")
    assert snapshot_trace(Trace(name="x")).input.args == []


def test_storage_load_trace_variants():
    with pytest.raises(storage.NotFoundError):
        storage.load_trace("latest")
    a, b = (
        Trace(id="tr_aaa111", started_at="2026-01-01"),
        Trace(id="tr_aab222", started_at="2026-01-02"),
    )
    storage.save_trace(a)
    storage.save_trace(b)
    assert storage.load_trace("latest").id == "tr_aab222"
    assert storage.load_trace("tr_aaa").id == "tr_aaa111"
    with pytest.raises(storage.NotFoundError, match="ambiguous"):
        storage.load_trace("tr_aa")
    with pytest.raises(storage.NotFoundError, match="No trace"):
        storage.load_trace("zzz")


def test_judge_missing_sdk_skips_unless_explicit(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_sdk(name, *args, **kwargs):
        if name in ("openai", "anthropic"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_sdk)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert judge_from_env() is None
    with pytest.raises(JudgeError, match="agentrecheck\\[anthropic\\]"):
        judge_from_env("anthropic:claude-opus-5-5")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert judge_from_env() is None
    with pytest.raises(JudgeError, match="agentrecheck\\[openai\\]"):
        judge_from_env("openai:gpt-4o-mini")

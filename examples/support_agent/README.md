# Example: support agent

A small OpenAI tool-calling agent with three tools (`lookup_order`, `issue_refund`,
`search_kb`) and five AgentRecheck test cases.

It runs **offline by default**: without `OPENAI_API_KEY` the agent uses a
deterministic stand-in for the OpenAI client (`mock_llm.py`), so everything
below works with no key and no cost.

```bash
pip install -e ../../sdk-python        # or: pip install agentrecheck
python agent.py "Where is my order A1002?"
agentrecheck traces                     # the run you just recorded
agentrecheck run                        # 5/5 pass
```

## See a regression get caught

`prompts/v2.txt` is a "simplified" system prompt. It reads fine, but it drops
the rule that the agent must look up an order before refunding it.

```bash
SUPPORT_AGENT_PROMPT=v2 agentrecheck run
```

`refund_outside_window` fails: the agent now refunds a 92-day-old order without
checking it. The command exits with code 1, which is what fails your CI job.

```
✗ refund_outside_window  Refund request outside the 30-day window
  ✗ tools.sequence (exact): expected ['lookup_order'], got ['issue_refund']
  ✗ output.contains['30-day']: not found in output
  ✗ output.not_contains['has been issued']: found in output
  tool sequence (baseline → current):
    - lookup_order
    + issue_refund
```

Two other cases show `Tools: changed` but still pass, because they use
`mode: subset` and only require that `issue_refund` happens.

## Use a real model

```bash
pip install openai
export OPENAI_API_KEY=...
agentrecheck run
```

With a key set, `refund_eligible` also runs its LLM-as-judge rubric.

## Files

| File | What it is |
| --- | --- |
| `agent.py` | The agent loop, decorated with `@trace` |
| `tools.py` | Three tools, decorated with `@tool` |
| `mock_llm.py` | Offline stand-in for the OpenAI client |
| `prompts/` | `v1.txt` (good) and `v2.txt` (regressed) |
| `agentrecheck.yaml` | Config: entrypoint and thresholds |
| `agentrecheck_cases/` | The five test cases |

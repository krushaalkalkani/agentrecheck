# Launch kit

Drafts, written to be edited. Everything below describes what v0.1.0 actually does. Before
posting, replace `<REPO_URL>` and `<SITE_URL>`, and re-read each claim against the current build.

Do not post numbers (users, stars, benchmarks) until you have real ones.

---

## Show HN

**Title** (80 char limit):

> Show HN: AgentRecheck – regression tests for tool-calling AI agents, run in CI

**Body:**

Hi HN,

I kept breaking my own agents. I'd tidy a system prompt or bump a model version, everything would
look fine in a quick manual test, and a week later I'd find the agent had stopped calling a tool it
used to call, or was taking twice as many steps. Nothing errors when that happens. The agent just
does a slightly different, slightly worse thing.

AgentRecheck is my attempt at the boring fix: treat agent behaviour like any other thing you don't
want to regress, and check it in CI.

How it works:

1. Add a decorator to your agent. It records each run as a trace: input, every LLM call (model,
   prompt, output, tokens, cost, latency), every tool call (name, args, result), final output.
2. `agentrecheck snapshot <trace_id>` turns a recorded run into a YAML test case with the baseline
   captured.
3. `agentrecheck run` replays every case against your current code, diffs it against the baseline,
   and exits non-zero on a regression.

Assertions are plain YAML: expected tool sequence (exact, or an ordered subset), tool arguments
(exact / regex / JSON Schema), final output (contains / regex / optional LLM-as-judge with a
rubric), and budgets for cost, latency, and step count.

The repo has an example support agent with five cases. One of them catches a "simplified" prompt
that quietly drops the rule to look up an order before refunding it. It runs offline with a
scripted stand-in for the model, so you can see a caught regression without an API key:

    cd examples/support_agent
    agentrecheck run                           # 5/5
    SUPPORT_AGENT_PROMPT=v2 agentrecheck run   # 4/5, exit 1

Things I'd like to be upfront about:

- It's an early MVP. Python only. Adapters for the OpenAI and Anthropic SDKs, plus manual
  `record_llm_call` / `record_tool_call` for everything else. Streaming responses pass through but
  aren't captured yet.
- Replays call your real agent, so they call your real model. Agents are non-deterministic, which
  is why the assertions are about structure (which tools, what args, what budget) rather than
  exact output text. For fuzzy checks there's the LLM judge, which runs on your own key.
- The SDK and CLI are MIT and work entirely locally. There's an optional dashboard (trace
  timeline, run history, cost/latency trends) that I'd eventually like to charge teams for.

Repo: <REPO_URL>
Site and docs: <SITE_URL>

I'd really like feedback on the assertion format, and on what you'd need before trusting this in
a real pipeline. What does your agent testing look like today?

---

## X / Twitter thread (5 posts)

**1/**
You changed your agent's prompt.

Did it get worse?

Most teams find out from a user. I built AgentRecheck so the pull request finds out first.

CI/CD for AI agents. Open source. 🧵

**2/**
Agents don't crash when they regress. They quietly:

– skip a tool call they used to make
– take 6 steps instead of 3
– cost 2x after a model bump

Unit tests don't see it. Pasting prompts into a playground doesn't scale.

**3/**
How it works:

① `@trace` your agent → records every LLM + tool call
② `agentrecheck snapshot <id>` → that run becomes a test case
③ `agentrecheck run` in CI → replays every case, diffs vs baseline, exits 1 on regression

[attach: terminal screenshot of a failing run with the tool-sequence diff]

**4/**
Assertions are plain YAML:

– tool sequence (exact or ordered subset)
– tool args (exact / regex / JSON Schema)
– output (contains / regex / LLM-as-judge on your own key)
– budgets: max cost, latency, steps

[attach: screenshot of a case file]

**5/**
Python, MIT licensed, works with the OpenAI and Anthropic SDKs.

The example agent runs offline, so you can watch it catch a regression in about a minute, no API
key needed.

Repo: <REPO_URL>
Docs: <SITE_URL>/docs

It's early. Tell me what's missing.

---

## Product Hunt

**Name:** AgentRecheck

**Tagline** (60 char limit):

> CI/CD for AI agents: catch regressions before they ship

**Description** (260 char limit):

> AgentRecheck records your AI agent's runs, turns them into test cases, and replays them on every
> pull request. If a prompt or model change makes the agent call the wrong tools, answer worse, or
> cost more, the build fails. Open-source Python SDK.

**Topics:** Developer Tools, Artificial Intelligence, Open Source, Testing

**First comment (maker):**

Hi everyone 👋

I built AgentRecheck after shipping one too many "small prompt tweaks" that changed how my agent
behaved in ways I didn't notice until later.

The idea is simple: record a real run, snapshot it into a test, replay it in CI. You assert on the
things that matter for agents, which tools were called, with what arguments, within what budget,
rather than on exact output text.

What's here today: a Python SDK and CLI (MIT), adapters for the OpenAI and Anthropic SDKs, a GitHub
Action, and an optional dashboard with a trace timeline and run history. The Free plan covers one
project and 1,000 traces a month. Pro is not open yet; there's a waitlist on the site.

It's an early release and I'm here all day. I'd love to hear how you test agents now and what
would make this useful for you.

---

## 10 places to share

Read each community's self-promotion rules first. Lead with the problem and the example, not the
product.

1. **Hacker News** — Show HN (draft above). Weekday morning US Eastern; stay in the thread.
2. **X / Twitter** — the thread above, with the failing-run screenshot as the first image.
3. **Product Hunt** — launch on a separate day from HN so you can be present for both.
4. **r/LocalLLaMA** — frame as "how I test tool-calling agents"; the offline example fits well.
5. **r/MachineLearning** — `[P]` project post. Keep it technical; expect questions about
   non-determinism.
6. **r/LLMDevs** and **r/AI_Agents** — practitioner audiences; ask how they test today.
7. **LangChain and LlamaIndex community Discords / forums** — show-and-tell channels. Note that
   framework-specific adapters aren't built yet and ask who wants one.
8. **OpenAI Developer Community forum** and **Anthropic's developer Discord** — the project-showcase
   areas, with the provider-specific adapter snippet.
9. **dev.to / Hashnode** — a longer write-up: "The prompt change that broke our refund flow, and
   the test that would have caught it", walking through the example.
10. **LinkedIn + AI-engineering newsletters** — a short post for your own network, then pitch the
    write-up to newsletters that cover agent tooling (e.g. Latent Space, TLDR AI, Ben's Bites).

### Assets to prepare before launch day

- [ ] Terminal screenshot or short GIF of `SUPPORT_AGENT_PROMPT=v2 agentrecheck run` failing
- [ ] Dashboard screenshots: run history with the red run, the run detail diff, a trace timeline
- [ ] Public repo with README, LICENSE, and the example working from a clean clone
- [ ] Package published to PyPI so `pip install agentrecheck` is true
- [ ] Deployed site with the waitlist form writing to the production database

import Link from "next/link";

import { CodeBlock, GITHUB_URL, SiteFooter, SiteHeader } from "@/components/site";
import { buttonVariants } from "@/components/ui/button";
import { WaitlistForm } from "@/components/waitlist-form";
import { cn } from "@/lib/utils";

const PROBLEMS = [
  {
    title: "A prompt tweak drops a tool call",
    body: "You tidy the system prompt. The agent stops verifying orders before refunding them. Nothing errors, nothing alerts.",
  },
  {
    title: "A model upgrade doubles your cost",
    body: "The new model takes six steps where the old one took three. You notice when the invoice arrives.",
  },
  {
    title: "You test by hand, so you test five things",
    body: "Pasting prompts into a playground doesn't scale past a handful of cases, and nobody reruns them on the next change.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Trace",
    body: "Add one decorator. AgentRecheck records the input, every LLM call, every tool call, tokens, cost, latency, and the final output.",
    code: `@trace
def run_agent(message: str) -> str:
    ...`,
  },
  {
    step: "02",
    title: "Snapshot",
    body: "Turn any recorded run into a test case. The baseline is captured for you; add assertions in plain YAML.",
    code: `$ agentrecheck snapshot latest \\
    --id refund_outside_window`,
  },
  {
    step: "03",
    title: "Run in CI",
    body: "Replay every case against the current code on each pull request. A regression exits non-zero and fails the check.",
    code: `$ agentrecheck run
4/5 passed · 1 regression(s)`,
  },
];

const PYTHON_SNIPPET = `from openai import OpenAI
from agentrecheck import trace, tool, wrap_openai

client = wrap_openai(OpenAI())   # records every LLM call

@tool                            # records every tool call
def lookup_order(order_id: str) -> dict:
    return db.orders.get(order_id)

@trace                           # records the whole run
def run_agent(message: str) -> str:
    ...`;

const YAML_SNIPPET = `id: refund_outside_window
input:
  args: ["Please refund order A1003"]
assertions:
  tools:
    sequence: [lookup_order]     # must check, must not refund
    mode: exact
  output:
    contains: ["30-day"]
    not_contains: ["has been issued"]
    judge:
      rubric: Politely declines and explains the policy.
      min_score: 0.7
  budgets:
    max_cost_usd: 0.01
    max_steps: 4`;

function Terminal() {
  const row = "grid grid-cols-[1fr_3.5rem_4.5rem_6rem] gap-x-4";
  const cases: [string, "PASS" | "FAIL", string, string][] = [
    ["order_status", "PASS", "same", "$0.00011"],
    ["password_reset", "PASS", "same", "$0.00012"],
    ["refund_eligible", "PASS", "changed", "$0.00011"],
    ["refund_outside_window", "FAIL", "changed", "$0.00011"],
    ["refund_with_question", "PASS", "changed", "$0.00020"],
  ];
  return (
    <div className="overflow-hidden rounded-xl border bg-card text-left shadow-2xl shadow-black/40">
      <div className="flex items-center gap-1.5 border-b px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-muted-foreground/30" />
        <span className="size-2.5 rounded-full bg-muted-foreground/30" />
        <span className="size-2.5 rounded-full bg-muted-foreground/30" />
        <span className="ml-3 font-mono text-xs text-muted-foreground">
          pull request #218 · simplify-prompt
        </span>
      </div>
      <div className="overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed">
        <div className="min-w-[30rem]">
          <p>
            <span className="text-brand">$</span> agentrecheck run
          </p>
          <div className={cn(row, "mt-3 text-muted-foreground")}>
            <span>Case</span>
            <span>Result</span>
            <span>Tools</span>
            <span className="text-right">Cost</span>
          </div>
          {cases.map(([name, result, tools, cost]) => (
            <div key={name} className={row}>
              <span>{name}</span>
              <span className={result === "PASS" ? "text-pass" : "text-fail"}>{result}</span>
              <span className={tools === "changed" ? "text-warn" : "text-muted-foreground"}>{tools}</span>
              <span className="text-right text-muted-foreground">{cost}</span>
            </div>
          ))}
          <p className="mt-4 text-fail">✗ refund_outside_window</p>
          <p className="pl-4 text-muted-foreground">
            tools.sequence (exact): expected [&apos;lookup_order&apos;], got [&apos;issue_refund&apos;]
          </p>
          <p className="pl-4 text-fail">- lookup_order</p>
          <p className="pl-4 text-pass">+ issue_refund</p>
          <p className="mt-3">
            <span className="text-fail">4/5 passed · 1 regression(s) detected.</span>{" "}
            <span className="text-muted-foreground">exit 1</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function Check() {
  return (
    <svg viewBox="0 0 16 16" className="mt-0.5 size-4 shrink-0 text-brand" fill="none" aria-hidden>
      <path d="m3.5 8.5 3 3 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export default function LandingPage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="bg-grid pointer-events-none absolute inset-0" aria-hidden />
          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:py-28">
            <div>
              <p className="mb-5 inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs text-muted-foreground">
                <span className="size-1.5 rounded-full bg-brand" />
                Open-source Python SDK · OpenAI + Anthropic
              </p>
              <h1 className="text-5xl font-semibold tracking-tight text-balance sm:text-6xl">
                CI/CD for <span className="text-brand">AI agents</span>
              </h1>
              <p className="mt-5 max-w-xl text-lg text-pretty text-muted-foreground">
                You changed a prompt. Did the agent get worse? AgentRecheck records real agent runs,
                turns them into tests, and replays them on every pull request, so regressions fail the
                build instead of reaching your users.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link href="/docs" className={cn(buttonVariants({ size: "lg" }), "h-10 px-5")}>
                  Get started in 5 minutes
                </Link>
                <a
                  href={GITHUB_URL}
                  className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-5")}
                >
                  View on GitHub
                </a>
              </div>
              <p className="mt-6 font-mono text-sm text-muted-foreground">
                <span className="text-brand">$</span> pip install agentrecheck
              </p>
            </div>
            <Terminal />
          </div>
        </section>

        {/* Problem */}
        <section className="border-t">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-balance">
              Agents don&apos;t crash when they get worse. They just quietly do the wrong thing.
            </h2>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Every prompt edit, model swap, and tool change can alter which tools your agent calls,
              in what order, and at what cost. Unit tests don&apos;t see it. Manual testing can&apos;t
              keep up.
            </p>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {PROBLEMS.map((problem) => (
                <div key={problem.title} className="rounded-xl border bg-card p-5">
                  <h3 className="font-medium">{problem.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{problem.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="border-t">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="text-3xl font-semibold tracking-tight">How it works</h2>
            <p className="mt-3 text-muted-foreground">Three steps, no new test framework to learn.</p>
            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {STEPS.map((item) => (
                <li key={item.step} className="flex flex-col rounded-xl border bg-card p-5">
                  <span className="font-mono text-xs text-brand">{item.step}</span>
                  <h3 className="mt-2 text-lg font-medium">{item.title}</h3>
                  <p className="mt-2 flex-1 text-sm text-muted-foreground">{item.body}</p>
                  <pre className="mt-4 overflow-x-auto rounded-lg bg-background p-3 font-mono text-xs leading-relaxed">
                    {item.code}
                  </pre>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Code */}
        <section className="border-t">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="text-3xl font-semibold tracking-tight">Instrument once. Assert in YAML.</h2>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Check the tool sequence, the arguments, the final answer, and the budget. LLM-as-judge is
              optional and runs on your own API key.
            </p>
            <div className="mt-10 grid gap-4 lg:grid-cols-2">
              <CodeBlock title="agent.py">{PYTHON_SNIPPET}</CodeBlock>
              <CodeBlock title="agentrecheck_cases/refund_outside_window.yaml">{YAML_SNIPPET}</CodeBlock>
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="scroll-mt-16 border-t">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="text-3xl font-semibold tracking-tight">Pricing</h2>
            <p className="mt-3 text-muted-foreground">
              The SDK and CLI are open source and run entirely on your machine. The dashboard is
              optional.
            </p>
            <div className="mt-10 grid max-w-4xl gap-4 md:grid-cols-2">
              <div className="flex flex-col rounded-xl border bg-card p-6">
                <h3 className="font-medium">Free</h3>
                <p className="mt-3 text-4xl font-semibold tracking-tight">
                  $0<span className="text-base font-normal text-muted-foreground"> / month</span>
                </p>
                <ul className="mt-6 flex-1 space-y-3 text-sm">
                  {[
                    "1 project",
                    "1,000 traces per month",
                    "Unlimited local test runs",
                    "Trace explorer and run history",
                  ].map((feature) => (
                    <li key={feature} className="flex gap-2">
                      <Check />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/login"
                  className={cn(buttonVariants({ variant: "outline", size: "lg" }), "mt-8 h-9")}
                >
                  Start free
                </Link>
              </div>

              <div className="flex flex-col rounded-xl border border-brand/40 bg-card p-6">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Pro</h3>
                  <span className="rounded-full border border-brand/40 bg-brand/10 px-2 py-0.5 font-mono text-[11px] text-brand">
                    coming soon
                  </span>
                </div>
                <p className="mt-3 text-4xl font-semibold tracking-tight">
                  $49<span className="text-base font-normal text-muted-foreground"> / month</span>
                </p>
                <ul className="mt-6 flex-1 space-y-3 text-sm">
                  {["Unlimited projects", "50,000 traces per month", "Team seats", "Everything in Free"].map(
                    (feature) => (
                      <li key={feature} className="flex gap-2">
                        <Check />
                        {feature}
                      </li>
                    ),
                  )}
                </ul>
                <div className="mt-8">
                  <p className="mb-2 text-sm text-muted-foreground">
                    Get an email when Pro opens:
                  </p>
                  <WaitlistForm />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Closing CTA */}
        <section className="border-t">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 py-16 sm:px-6 md:flex-row md:items-center">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Know before you merge.
              </h2>
              <p className="mt-2 text-muted-foreground">
                Add a decorator, snapshot a run, and wire one command into CI.
              </p>
            </div>
            <div className="flex gap-3">
              <Link href="/docs" className={cn(buttonVariants({ size: "lg" }), "h-10 px-5")}>
                Read the quickstart
              </Link>
              <a
                href={GITHUB_URL}
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-5")}
              >
                GitHub
              </a>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

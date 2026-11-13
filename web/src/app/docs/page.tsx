import type { Metadata } from "next";

import { CodeBlock, GITHUB_URL, SiteFooter, SiteHeader } from "@/components/site";

export const metadata: Metadata = {
  title: "Docs",
  description: "Quickstart and reference for the AgentRecheck SDK, CLI, and API.",
};

const SECTIONS = [
  ["quickstart", "5-minute quickstart"],
  ["tracing", "Tracing"],
  ["cases", "Test cases"],
  ["assertions", "Assertions"],
  ["cli", "CLI"],
  ["ci", "CI"],
  ["dashboard", "Dashboard and API"],
  ["judge", "LLM-as-judge"],
] as const;

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 space-y-4 border-t pt-10 first:border-0 first:pt-0">
      <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

const P = ({ children }: { children: React.ReactNode }) => (
  <p className="leading-relaxed text-muted-foreground">{children}</p>
);
const C = ({ children }: { children: React.ReactNode }) => (
  <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em] text-foreground">{children}</code>
);

function Rows({ rows }: { rows: [string, string][] }) {
  return (
    <div className="overflow-hidden rounded-xl border">
      <table className="w-full text-sm">
        <tbody className="divide-y">
          {rows.map(([key, value]) => (
            <tr key={key}>
              <td className="w-2/5 bg-card px-4 py-2.5 align-top font-mono text-xs">{key}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DocsPage() {
  return (
    <>
      <SiteHeader />
      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <nav className="hidden lg:block" aria-label="Docs sections">
          <ul className="sticky top-20 space-y-1 text-sm">
            {SECTIONS.map(([id, label]) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  className="block rounded-md px-2 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {label}
                </a>
              </li>
            ))}
            <li className="pt-3">
              <a href={GITHUB_URL} className="block px-2 py-1.5 text-muted-foreground hover:text-foreground">
                GitHub →
              </a>
            </li>
          </ul>
        </nav>

        <main className="min-w-0 max-w-3xl space-y-10">
          <header>
            <h1 className="text-4xl font-semibold tracking-tight">Documentation</h1>
            <p className="mt-3 text-lg text-muted-foreground">
              Record agent runs, snapshot them into test cases, and replay them in CI.
            </p>
          </header>

          <Section id="quickstart" title="5-minute quickstart">
            <P>1. Install the SDK (Python 3.11+).</P>
            <CodeBlock title="shell">pip install agentrecheck</CodeBlock>
            <P>
              2. Instrument your agent. <C>@trace</C> records the run, <C>@tool</C> records tool calls,
              and <C>wrap_openai</C> / <C>wrap_anthropic</C> record LLM calls.
            </P>
            <CodeBlock title="agent.py">{`from openai import OpenAI
from agentrecheck import trace, tool, wrap_openai

client = wrap_openai(OpenAI())

@tool
def lookup_order(order_id: str) -> dict:
    ...

@trace
def run_agent(message: str) -> str:
    ...  # your existing agent loop, unchanged`}</CodeBlock>
            <P>3. Create the config, run the agent once, and snapshot that run into a test case.</P>
            <CodeBlock title="shell">{`agentrecheck init --entrypoint agent:run_agent
python agent.py "Where is my order A1002?"
agentrecheck traces                       # see what was recorded
agentrecheck snapshot latest --id order_status`}</CodeBlock>
            <P>
              4. Replay. Every case runs against your current code and is compared to its baseline.
              The exit code is non-zero if anything regressed.
            </P>
            <CodeBlock title="shell">agentrecheck run</CodeBlock>
            <P>
              Want to see a caught regression first? The repository includes{" "}
              <C>examples/support_agent</C>, which runs offline with no API key.
            </P>
          </Section>

          <Section id="tracing" title="Tracing">
            <P>
              A trace is one agent run: its input, every LLM call (model, prompt, output, tokens,
              latency, cost), every tool call (name, arguments, result, error), and the final output.
              Traces are saved as JSON under <C>.agentrecheck/traces/</C>.
            </P>
            <Rows
              rows={[
                ["@trace / @trace(name=...)", "Record each call of a sync or async function as a trace."],
                ["with start_trace(name):", "Context-manager form for code you can't decorate."],
                ["@tool", "Record each call of a function as a tool step, with bound arguments."],
                ["wrap_openai(client)", "Chat Completions and Responses APIs, sync and async."],
                ["wrap_anthropic(client)", "Messages API, sync and async."],
                ["wrap(client)", "Auto-detect the provider."],
                ["record_llm_call(...) / record_tool_call(...)", "Record a step by hand for any other provider or framework."],
                ["register_adapter(name, detect, wrap)", "Plug in your own client adapter."],
                ["register_price(model, in, out)", "Set or override per-million-token prices used for cost."],
              ]}
            />
            <P>
              Streaming responses are passed through untouched and noted on the step, but their
              content is not captured yet. Set <C>AGENTRECHECK_DISABLED=1</C> to turn recording off.
            </P>
          </Section>

          <Section id="cases" title="Test cases">
            <P>
              <C>agentrecheck snapshot &lt;trace_id&gt;</C> writes a YAML file to{" "}
              <C>agentrecheck_cases/</C>. It contains the input to replay, the baseline (tool
              sequence, cost, latency, steps, output), and starter assertions. Commit these files.
            </P>
            <CodeBlock title="agentrecheck_cases/refund_outside_window.yaml">{`id: refund_outside_window
name: Refund request outside the 30-day window
input:
  args: ["Please refund order A1003, I changed my mind."]
  kwargs: {}
baseline:
  tool_sequence: [lookup_order]
  cost_usd: 0.0001197
  latency_ms: 48.0
  steps: 3
assertions:
  tools:
    sequence: [lookup_order]
    mode: exact
  output:
    contains: ["30-day"]
    not_contains: ["has been issued"]
  budgets:
    max_steps: 4`}</CodeBlock>
          </Section>

          <Section id="assertions" title="Assertions">
            <Rows
              rows={[
                ["tools.sequence + mode: exact", "The executed tools must equal the list exactly."],
                ["tools.sequence + mode: subset", "The listed tools must all appear, in order. Other calls are allowed in between."],
                ["tools.args[].exact", "A tool call's arguments must equal this object."],
                ["tools.args[].regex", "Per-argument regular expressions, e.g. order_id: \"^A\\d+$\"."],
                ["tools.args[].json_schema", "Validate the arguments against a JSON Schema."],
                ["tools.args[].index", "Which call of that tool to check (0 = first)."],
                ["output.contains / not_contains", "Case-insensitive substrings of the final output."],
                ["output.regex", "A regular expression the final output must match."],
                ["output.judge", "LLM-as-judge: a rubric and a min_score between 0 and 1."],
                ["budgets.max_cost_usd / max_latency_ms / max_steps", "Hard ceilings for the run."],
              ]}
            />
            <P>
              Separately from assertions, each run is compared to its baseline. A cost increase above{" "}
              <C>regression.max_cost_increase_pct</C> (default 25%) fails the case. Latency regression
              is off by default because CI timing is noisy; set <C>max_latency_increase_pct</C> to
              enable it.
            </P>
          </Section>

          <Section id="cli" title="CLI">
            <Rows
              rows={[
                ["agentrecheck init", "Create agentrecheck.yaml and the cases directory."],
                ["agentrecheck traces", "List locally recorded traces."],
                ["agentrecheck show <id|latest>", "Print a trace's step-by-step timeline."],
                ["agentrecheck snapshot <id|latest>", "Turn a trace into a test case. Flags: --id, --name, --mode, --force."],
                ["agentrecheck run", "Replay all cases. Flags: --case, --entrypoint, --json-out, --markdown-out, --no-upload."],
                ["agentrecheck upload <id|latest|all>", "Send local traces to the dashboard."],
              ]}
            />
            <P>
              Exit codes: <C>0</C> all cases passed, <C>1</C> at least one regression, <C>2</C>{" "}
              configuration error.
            </P>
          </Section>

          <Section id="ci" title="CI">
            <P>
              Any CI system works: install your dependencies and run <C>agentrecheck run</C>. On
              GitHub Actions the pass/fail table and diffs are also written to the job summary.
            </P>
            <CodeBlock title=".github/workflows/agentrecheck.yml">{`name: AgentRecheck
on: [pull_request]
jobs:
  agent-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install agentrecheck -r requirements.txt
      - run: agentrecheck run
        env:
          OPENAI_API_KEY: \${{ secrets.OPENAI_API_KEY }}
          AGENTRECHECK_API_KEY: \${{ secrets.AGENTRECHECK_API_KEY }}
          AGENTRECHECK_API_URL: \${{ vars.AGENTRECHECK_API_URL }}`}</CodeBlock>
          </Section>

          <Section id="dashboard" title="Dashboard and API">
            <P>
              The dashboard is optional. Create a project to get an API key, then set two environment
              variables. Traces upload as each run finishes; <C>agentrecheck run</C> uploads its
              results with diffs.
            </P>
            <CodeBlock title="shell">{`export AGENTRECHECK_API_KEY=ark_...
export AGENTRECHECK_API_URL=https://your-deployment.example.com`}</CodeBlock>
            <P>
              Every endpoint authenticates with <C>Authorization: Bearer &lt;project api key&gt;</C>.
            </P>
            <Rows
              rows={[
                ["POST /api/traces", "Ingest one trace, or { traces: [...] } (max 100)."],
                ["GET /api/traces?limit=50", "Recent traces."],
                ["GET /api/traces/:id", "One trace with all steps."],
                ["POST /api/runs", "Upload a test run."],
                ["GET /api/runs?limit=50", "Recent runs with pass/fail counts."],
                ["GET /api/runs/:id", "One run with per-case checks and diffs."],
              ]}
            />
          </Section>

          <Section id="judge" title="LLM-as-judge">
            <P>
              Judge checks are optional and run on your own key. Install the extra for your provider
              and set its key. Without a key, judge checks are reported as skipped, never failed.
            </P>
            <CodeBlock title="shell">{`pip install "agentrecheck[openai]"      # or "agentrecheck[anthropic]"
export OPENAI_API_KEY=...               # or ANTHROPIC_API_KEY`}</CodeBlock>
            <P>
              Pick the model with <C>judge_model: openai:gpt-4o-mini</C> in{" "}
              <C>agentrecheck.yaml</C>, or the <C>AGENTRECHECK_JUDGE_MODEL</C> environment variable.
            </P>
          </Section>
        </main>
      </div>
      <SiteFooter />
    </>
  );
}

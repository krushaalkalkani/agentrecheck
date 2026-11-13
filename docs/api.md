# REST API

Base URL: wherever the web app is deployed, for example `http://localhost:3000`.

## Authentication

Every endpoint except `/api/waitlist` needs a project API key:

```
Authorization: Bearer ark_...
```

Keys are created with the project and can be regenerated under **Settings**. Only a SHA-256 hash is
stored, so a key is shown exactly once. A missing or wrong key returns `401`.

The dashboard itself can also call the `GET` endpoints with a signed-in session and
`?project_id=<uuid>`.

## Errors

```json
{ "error": "Invalid payload.", "details": [{ "path": "steps.0.type", "message": "Invalid input" }] }
```

| Status | When |
| --- | --- |
| `400` | Body is not valid JSON |
| `401` | Missing or invalid API key |
| `404` | Trace or run not found in this project |
| `422` | Body failed validation |
| `429` | Free plan trace limit reached (1,000 per month) |

## Traces

### `POST /api/traces`

Body: one trace, or `{ "traces": [...] }` with up to 100. Re-sending a trace id is a no-op.

```json
{
  "id": "tr_e8006f1d2c3b",
  "name": "support_agent",
  "input": { "args": ["Where is my order A1002?"], "kwargs": {} },
  "output": "Order A1002 is in transit.",
  "error": null,
  "started_at": "2026-11-13T05:37:29.123456+00:00",
  "latency_ms": 812.5,
  "metadata": {},
  "steps": [
    {
      "type": "llm",
      "index": 0,
      "provider": "openai",
      "model": "gpt-4o-mini",
      "input": [{ "role": "user", "content": "Where is my order A1002?" }],
      "output": null,
      "tool_calls": [{ "id": "call_0", "name": "lookup_order", "arguments": { "order_id": "A1002" } }],
      "input_tokens": 400,
      "output_tokens": 20,
      "cost_usd": 0.000072,
      "latency_ms": 400,
      "started_at": "2026-11-13T05:37:29.200000+00:00",
      "error": null
    },
    {
      "type": "tool",
      "index": 1,
      "name": "lookup_order",
      "args": { "order_id": "A1002" },
      "result": { "status": "in transit" },
      "error": null,
      "latency_ms": 30,
      "started_at": "2026-11-13T05:37:29.600000+00:00"
    }
  ]
}
```

Response: `{ "ids": ["tr_e8006f1d2c3b"], "url": "<dashboard url>" }`

Totals (cost, tokens, call counts, tool sequence) are computed on the server from `steps`.

### `GET /api/traces?limit=50`

Recent traces, newest first, without step payloads. `limit` is capped at 200.

### `GET /api/traces/:id`

One trace with all steps. `:id` is either the SDK trace id (`tr_...`) or the server uuid.

## Test runs

### `POST /api/runs`

The payload `agentrecheck run` produces (`RunResult.to_payload()` in the SDK):

```json
{
  "id": "run_bdc484f28050",
  "started_at": "2026-11-13T06:10:46.160000+00:00",
  "duration_ms": 378.5,
  "git_sha": "64c208f",
  "git_branch": "main",
  "results": [
    {
      "case_id": "refund_outside_window",
      "name": "Refund request outside the 30-day window",
      "status": "fail",
      "error": null,
      "checks": [
        { "name": "tools.sequence (exact)", "status": "fail", "message": "expected ['lookup_order'], got ['issue_refund']" }
      ],
      "diff": {
        "baseline_tools": ["lookup_order"],
        "actual_tools": ["issue_refund"],
        "tools_changed": true,
        "baseline_cost_usd": 0.0001197,
        "cost_usd": 0.00011,
        "baseline_latency_ms": 48.0,
        "latency_ms": 51.2,
        "baseline_steps": 3,
        "steps": 3,
        "judge_score": null
      },
      "trace": { "...": "same shape as POST /api/traces" }
    }
  ]
}
```

Response: `{ "id": "<uuid>", "url": "<dashboard url of the run>" }`

Re-sending a run id replaces the stored run. Traces embedded in a run are stored with the run and
do not count toward the monthly trace limit.

### `GET /api/runs?limit=50`

Recent runs with pass/fail counts, cost, and average latency.

### `GET /api/runs/:id`

One run with per-case checks, diffs, and traces. `:id` is the SDK run id or the server uuid.

## Waitlist

### `POST /api/waitlist`

No authentication. Body: `{ "email": "you@company.com" }`. Idempotent per email.

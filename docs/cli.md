# CLI reference

```
agentrecheck [COMMAND]
```

| Command | Description |
| --- | --- |
| `init` | Create `agentrecheck.yaml` and `agentrecheck_cases/` |
| `traces` | List locally recorded traces, newest first |
| `show <trace>` | Print a trace's step-by-step timeline |
| `snapshot <trace>` | Turn a trace into a test case |
| `run` | Replay all cases against the current code |
| `upload <trace>` | Send local traces to the dashboard |
| `version` | Print the installed version |

`<trace>` is a trace id, a unique prefix of one, or `latest`. `upload` also accepts `all`.

## `init`

| Option | Default | |
| --- | --- | --- |
| `--entrypoint` | `agent:run_agent` | `module:function` that `run` will call |
| `--project` | `my-agent` | Project name |

## `snapshot`

| Option | Default | |
| --- | --- | --- |
| `--id` | derived from the trace | Case id, also the file name |
| `--name` | derived from the trace | Human-readable name |
| `--mode` | `exact` | Tool sequence mode: `exact` or `subset` |
| `--config` | `agentrecheck.yaml` | Config file |
| `--force` | off | Overwrite an existing case file |

## `run`

| Option | Default | |
| --- | --- | --- |
| `--config` | `agentrecheck.yaml` | Config file |
| `--case`, `-c` | all | Only run these case ids (repeatable) |
| `--entrypoint` | from config | Override the entrypoint |
| `--json-out PATH` | | Write the full result as JSON |
| `--markdown-out PATH` | | Write a markdown summary |
| `--upload / --no-upload` | upload | Upload results when `AGENTRECHECK_API_KEY` and `AGENTRECHECK_API_URL` are set |

Each run is also saved to `.agentrecheck/runs/<run_id>.json`. When `GITHUB_STEP_SUMMARY` is set, the
markdown summary is appended to it.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Every case passed |
| `1` | At least one case failed or errored |
| `2` | Configuration problem: no entrypoint, no cases, bad arguments |

An upload failure prints a warning and does not change the exit code.

"""Local storage: traces as JSON, test cases as YAML."""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from .models import Case, RunResult, Trace

DEFAULT_DIR = ".agentrecheck"


class NotFoundError(Exception):
    pass


def base_dir() -> Path:
    return Path(os.environ.get("AGENTRECHECK_DIR", DEFAULT_DIR))


def traces_dir(root: Path | None = None) -> Path:
    return (root or base_dir()) / "traces"


def save_trace(trace: Trace, root: Path | None = None) -> Path:
    directory = traces_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{trace.id}.json"
    path.write_text(json.dumps(trace.to_payload(), indent=2, default=str))
    return path


def list_traces(root: Path | None = None) -> list[Trace]:
    """All local traces, newest first."""
    directory = traces_dir(root)
    if not directory.exists():
        return []
    traces = [Trace.model_validate_json(p.read_text()) for p in directory.glob("*.json")]
    return sorted(traces, key=lambda t: t.started_at, reverse=True)


def load_trace(trace_id: str, root: Path | None = None) -> Trace:
    """Load a trace by id, unique id prefix, or the literal ``latest``."""
    traces = list_traces(root)
    if trace_id == "latest":
        if not traces:
            raise NotFoundError("No traces recorded yet.")
        return traces[0]
    matches = [t for t in traces if t.id == trace_id] or [
        t for t in traces if t.id.startswith(trace_id)
    ]
    if not matches:
        raise NotFoundError(f"No trace matching '{trace_id}' in {traces_dir(root)}")
    if len(matches) > 1:
        raise NotFoundError(f"'{trace_id}' is ambiguous ({len(matches)} traces match).")
    return matches[0]


def save_case(case: Case, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{case.id}.yaml"
    data = case.model_dump(mode="json", exclude_none=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))
    return path


def load_case(path: Path) -> Case:
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault("id", path.stem)
    return Case.model_validate(data)


def load_cases(directory: Path) -> list[Case]:
    if not directory.exists():
        return []
    paths = sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")])
    return [load_case(p) for p in paths]


def save_run(run: RunResult, root: Path | None = None) -> Path:
    directory = (root or base_dir()) / "runs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run.id}.json"
    path.write_text(json.dumps(run.to_payload(), indent=2, default=str))
    return path

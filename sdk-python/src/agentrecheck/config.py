"""Project configuration (``agentrecheck.yaml``)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_NAME = "agentrecheck.yaml"

CONFIG_TEMPLATE = """\
# AgentRecheck configuration
project: {project}

# The function `agentrecheck run` calls for every test case: "module:function".
# It is imported relative to this file's directory.
entrypoint: {entrypoint}

# Where test cases (YAML) live.
cases_dir: agentrecheck_cases

regression:
  # Fail a case when cost rises more than this % over its baseline. null disables.
  max_cost_increase_pct: 25
  # Latency is noisy in CI, so this is off by default.
  max_latency_increase_pct: null

# Optional LLM-as-judge model, "<provider>:<model>". Uses your own API key
# (OPENAI_API_KEY or ANTHROPIC_API_KEY). Judge checks are skipped without one.
# judge_model: openai:gpt-4o-mini
"""


class RegressionConfig(BaseModel):
    max_cost_increase_pct: float | None = 25.0
    max_latency_increase_pct: float | None = None


class Config(BaseModel):
    project: str | None = None
    entrypoint: str | None = None
    cases_dir: str = "agentrecheck_cases"
    regression: RegressionConfig = Field(default_factory=RegressionConfig)
    judge_model: str | None = None
    # Directory the config was loaded from; paths and imports resolve against it.
    root: Path = Field(default_factory=Path.cwd, exclude=True)

    @property
    def cases_path(self) -> Path:
        return self.root / self.cases_dir


def load_config(path: Path | None = None) -> Config:
    """Load the config file. A missing file yields defaults rooted at the cwd."""
    path = path or Path(DEFAULT_CONFIG_NAME)
    if not path.exists():
        return Config(root=Path.cwd())
    data = yaml.safe_load(path.read_text()) or {}
    cfg = Config.model_validate(data)
    cfg.root = path.resolve().parent
    return cfg

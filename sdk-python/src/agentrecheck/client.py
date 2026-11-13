"""Minimal client for the AgentRecheck cloud API."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .models import RunResult, Trace


class CloudError(Exception):
    pass


class CloudClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_env(cls) -> CloudClient | None:
        """Build a client from env vars, or None when upload is not configured.

        Both AGENTRECHECK_API_KEY and AGENTRECHECK_API_URL are required; there
        is deliberately no default URL.
        """
        key = os.environ.get("AGENTRECHECK_API_KEY")
        url = os.environ.get("AGENTRECHECK_API_URL")
        if not key or not url:
            return None
        return cls(url, key)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise CloudError(f"Could not reach {self.api_url}: {exc}") from exc
        if response.status_code >= 400:
            raise CloudError(f"{path} returned {response.status_code}: {response.text[:300]}")
        return response.json()

    def upload_trace(self, trace: Trace) -> dict[str, Any]:
        return self._post("/api/traces", trace.to_payload())

    def upload_run(self, run: RunResult) -> dict[str, Any]:
        return self._post("/api/runs", run.to_payload())

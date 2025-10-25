"""Client for the internally hosted basic NLU model that returns RouteCriteria-like payloads."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings

from .preprocessor import PreprocessedQuery


class NLUBasicModelClient:
    """Simple HTTP client that talks to the in-house basic NLU endpoint."""

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        timeout: float = 10.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._endpoint = (endpoint or settings.nlu_basic_model_url).rstrip("/")
        self._timeout = timeout
        self._client = client

    def parse(self, *, preprocessed: PreprocessedQuery) -> Dict[str, Any]:
        payload = {"text": preprocessed.original_text}
        try:
            if self._client is not None:
                response = self._client.post(
                    self._endpoint, json=payload, timeout=self._timeout
                )
            else:
                response = httpx.post(
                    self._endpoint, json=payload, timeout=self._timeout
                )
        except httpx.HTTPError as exc:
            raise RuntimeError("Basic NLU model request failed") from exc

        if response.status_code >= 400:
            raise RuntimeError(
                f"Basic NLU model request failed with status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Basic NLU model returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Basic NLU model response must be a JSON object.")

        return data

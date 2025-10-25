"""High-level orchestration for converting NLU queries into RouteCriteria."""
from __future__ import annotations

from typing import Dict, Optional

from app.models.request import Center, RouteCriteria

from .llm_client import RouteCriteriaLLMClient
from .nlu_basic_model_client import NLUBasicModelClient
from .preprocessor import PreprocessedQuery, QueryPreprocessor
from .validator import RouteCriteriaValidator


class RouteCriteriaParserService:
    """Decoupled pipeline: preprocess → LLM → validate/repair."""

    def __init__(
        self,
        *,
        preprocessor: Optional[QueryPreprocessor] = None,
        llm_client: Optional[RouteCriteriaLLMClient] = None,
        basic_client: Optional[NLUBasicModelClient] = None,
        validator: Optional[RouteCriteriaValidator] = None,
        basic_model_word_threshold: int = 10,
    ) -> None:
        self._preprocessor = preprocessor or QueryPreprocessor()
        self._llm_client = llm_client or RouteCriteriaLLMClient()
        self._basic_client = basic_client or NLUBasicModelClient()
        self._validator = validator or RouteCriteriaValidator()
        self._basic_model_word_threshold = max(basic_model_word_threshold, 0)

    def parse(self, query: str, center: Center) -> RouteCriteria:
        preprocessed = self._preprocessor.process(query)
        raw_payload = self._dispatch(preprocessed=preprocessed, center=center)
        return self._validator.validate(raw_payload, center=center)

    def _dispatch(self, *, preprocessed: PreprocessedQuery, center: Center) -> Dict[str, object]:
        word_count = self._count_words(preprocessed.normalized_text)
        if word_count <= self._basic_model_word_threshold:
            try:
                return self._basic_client.parse(preprocessed=preprocessed)
            except RuntimeError:
                # Fallback to LLM when the internal service is unavailable.
                pass
        return self._llm_client.parse(preprocessed=preprocessed, center=center)

    @staticmethod
    def _count_words(text: str) -> int:
        if not text:
            return 0
        # Split on whitespace to approximate word boundaries for space-delimited languages.
        return len(text.split())

    # Exposed for testing hooks
    @property
    def preprocessor(self) -> QueryPreprocessor:  # pragma: no cover - simple proxy
        return self._preprocessor

    @property
    def validator(self) -> RouteCriteriaValidator:  # pragma: no cover - simple proxy
        return self._validator

    @property
    def llm_client(self) -> RouteCriteriaLLMClient:  # pragma: no cover - simple proxy
        return self._llm_client

    @property
    def basic_client(self) -> NLUBasicModelClient:  # pragma: no cover - simple proxy
        return self._basic_client

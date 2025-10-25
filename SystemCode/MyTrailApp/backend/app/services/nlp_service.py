"""Facade for the RouteCriteria parsing pipeline."""
from __future__ import annotations

from fastapi.concurrency import run_in_threadpool

from app.models.request import Center, RouteCriteria
from app.services.nlp import RouteCriteriaParserService


class NLPService:
    """Expose parsing as a FastAPI-friendly service."""

    def __init__(self, parser: RouteCriteriaParserService | None = None) -> None:
        self._parser = parser or RouteCriteriaParserService()

    async def parse_query(self, query: str, center: Center) -> RouteCriteria:
        return await run_in_threadpool(self._parser.parse, query, center)

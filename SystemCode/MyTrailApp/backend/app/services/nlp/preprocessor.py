"""Preprocessing utilities for natural language parsing."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PreprocessedQuery:
    """Normalized view of the user's free-text query."""

    original_text: str
    normalized_text: str
    language: str
    contains_emojis: bool


class QueryPreprocessor:
    """Simple text cleanup and language heuristics with i18n awareness."""

    _LANGUAGE_PATTERNS = {
        "zh": re.compile(r"[\u4e00-\u9fff]"),
        "ja": re.compile(r"[\u3040-\u30ff]"),
        "ko": re.compile(r"[\uac00-\ud7af]"),
        "es": re.compile(r"[¿¡ñáéíóúü]", re.IGNORECASE),
        "fr": re.compile(r"[àâçéèêëîïôûùüÿœ]", re.IGNORECASE),
        "de": re.compile(r"[äöüß]", re.IGNORECASE),
        "ru": re.compile(r"[\u0400-\u04ff]"),
    }

    _EMOJI_PATTERN = re.compile(
        r"[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]"
    )

    def process(self, query: str) -> PreprocessedQuery:
        cleaned = self._normalize_whitespace(query)
        language = self._detect_language(cleaned)
        has_emojis = bool(self._EMOJI_PATTERN.search(cleaned))
        return PreprocessedQuery(
            original_text=query,
            normalized_text=cleaned,
            language=language,
            contains_emojis=has_emojis,
        )

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return " ".join(text.strip().split())

    def _detect_language(self, text: str) -> str:
        for code, pattern in self._LANGUAGE_PATTERNS.items():
            if pattern.search(text):
                return code
        # Treat extended Latin languages with many accents as unknown-latin
        if re.search(r"[A-Za-z]", text):
            return "en"
        return "unknown"

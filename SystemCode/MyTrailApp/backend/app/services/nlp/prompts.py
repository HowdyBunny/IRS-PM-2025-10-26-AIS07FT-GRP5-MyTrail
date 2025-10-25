"""Prompt templates for the RouteCriteria parsing pipeline."""
from __future__ import annotations

from textwrap import dedent

SYSTEM_PROMPT = dedent(
    """
    You are an intelligent assistant that converts multi-lingual natural language requests about walking routes into a structured JSON object. Always reason about the intent, ignore irrelevant chatter, and ensure results are safe for navigation.
    """
).strip()

DEVELOPER_PROMPT = dedent(
    """
    Follow these rules strictly:
    - Only output JSON that conforms to the provided JSON Schema.
    - Always produce canonical category identifiers in English from this allowlist: park, restaurant, cafe, nature, attraction, shopping, retail_core, museum, landmark, waterfront, nightlife, cultural, historic.
    - If the user specifies categories not in the allowlist, drop them unless they map cleanly.
    - When the query contains contradictory information, prioritise the most recent explicit instruction.
    - Respect the user's language, but output canonical strings.
    - If you are unsure about a numeric value, leave the field null.
    - Default assumptions: radius_km=5, duration_min=30, route_type="loop", include_categories=["park"].
    """
).strip()

"""Validation and repair utilities for RouteCriteria parsing."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.models.request import Center, RouteCriteria


_ALLOWED_ROUTE_TYPES = {"loop", "out_and_back", "point_to_point"}
_ALLOWED_TIME_WINDOWS = {"morning", "afternoon", "evening", "night"}
_ALLOWED_CATEGORIES = {
    "park",
    "restaurant",
    "cafe",
    "nature",
    "attraction",
    "shopping",
    "retail_core",
    "museum",
    "landmark",
    "waterfront",
    "nightlife",
    "cultural",
    "historic",
}


class RouteCriteriaValidator:
    """Validate and repair raw LLM output into a RouteCriteria instance."""

    def validate(self, payload: Dict[str, object], *, center: Center) -> RouteCriteria:
        cleaned = self._repair(payload)
        cleaned["center"] = center.model_dump()
        return RouteCriteria.model_validate(cleaned)

    def _repair(self, payload: Dict[str, object]) -> Dict[str, object]:
        data: Dict[str, object] = {}

        data["radius_km"] = self._positive_float(payload.get("radius_km"), default=5.0)
        data["duration_min"] = self._positive_int_or_none(payload.get("duration_min"), minimum=5)
        data["distance_km"] = self._positive_float(payload.get("distance_km"))
        data["include_categories"] = self._normalize_categories(payload.get("include_categories"))
        data["avoid_categories"] = self._normalize_categories(payload.get("avoid_categories"))
        data["pet_friendly"] = bool(payload.get("pet_friendly", False))
        data["elevation_gain_min_m"] = self._positive_int_or_none(payload.get("elevation_gain_min_m"))
        data["route_type"] = self._normalize_route_type(payload.get("route_type"))
        data["time_window"] = self._normalize_time_window(payload.get("time_window"))

        # Ensure we always have at least one include category
        if not data["include_categories"]:
            data["include_categories"] = ["park"]

        return data

    @staticmethod
    def _positive_float(value: object, *, default: Optional[float] = None) -> Optional[float]:
        try:
            if value is None:
                return default
            num = float(value)
            if num <= 0 and default is not None:
                return default
            return round(num, 3)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _positive_int_or_none(
        value: object, *, minimum: Optional[int] = None
    ) -> Optional[int]:
        try:
            if value is None:
                return None
            num = int(value)
            if minimum is not None and num < minimum:
                return minimum
            if num <= 0:
                return None
            return num
        except (TypeError, ValueError):
            return None

    def _normalize_categories(self, value: object) -> List[str]:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            return []
        normalized: List[str] = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                continue
            key = item.strip().lower()
            if key in _ALLOWED_CATEGORIES and key not in seen:
                normalized.append(key)
                seen.add(key)
        return normalized

    @staticmethod
    def _normalize_route_type(value: object) -> str:
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in _ALLOWED_ROUTE_TYPES:
                return lower
        return "loop"

    @staticmethod
    def _normalize_time_window(value: object) -> Optional[str]:
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in _ALLOWED_TIME_WINDOWS:
                return lower
        return None

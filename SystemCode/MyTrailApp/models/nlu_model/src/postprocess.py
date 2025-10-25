from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from data_example.dictionary_whitelist import CANON_LOOKUP, ROUTE_TYPE_MAP
from data_example.schema import RouteCriteria


@dataclass(frozen=True)
class SlotSpan:
    label: str
    tokens: Tuple[str, ...]
    start: int
    end: int

    @property
    def text(self) -> str:
        return " ".join(self.tokens)

    @property
    def label_tag(self) -> str:
        return self.label.split("-", 1)[-1]


def bio_to_spans(slots: Sequence[Dict[str, str]]) -> List[SlotSpan]:
    spans: List[SlotSpan] = []
    current_label: Optional[str] = None
    current_tokens: List[str] = []
    start_idx: Optional[int] = None

    for idx, slot in enumerate(slots):
        raw_label = slot.get("label", "O")
        token = slot.get("word", "")
        if not raw_label or raw_label == "O":
            if current_label is not None and current_tokens:
                spans.append(
                    SlotSpan(
                        label=current_label,
                        tokens=tuple(current_tokens),
                        start=start_idx if start_idx is not None else idx - len(current_tokens),
                        end=idx - 1,
                    )
                )
            current_label = None
            current_tokens = []
            start_idx = None
            continue

        prefix, _, tag = raw_label.partition("-")
        if prefix not in ("B", "I") or not tag:
            # Treat malformed tags as outside
            if current_label is not None and current_tokens:
                spans.append(
                    SlotSpan(
                        label=current_label,
                        tokens=tuple(current_tokens),
                        start=start_idx if start_idx is not None else idx - len(current_tokens),
                        end=idx - 1,
                    )
                )
            current_label = None
            current_tokens = []
            start_idx = None
            continue

        if prefix == "B" or tag != (current_label.split("-", 1)[-1] if current_label else None):
            if current_label is not None and current_tokens:
                spans.append(
                    SlotSpan(
                        label=current_label,
                        tokens=tuple(current_tokens),
                        start=start_idx if start_idx is not None else idx - len(current_tokens),
                        end=idx - 1,
                    )
                )
            current_label = raw_label
            current_tokens = [token]
            start_idx = idx
        else:
            current_tokens.append(token)

    if current_label is not None and current_tokens:
        spans.append(
            SlotSpan(
                label=current_label,
                tokens=tuple(current_tokens),
                start=start_idx if start_idx is not None else len(slots) - len(current_tokens),
                end=len(slots) - 1,
            )
        )

    return spans


def _clean_token(token: str) -> str:
    token = token.strip().lower()
    token = token.replace("’", "'")
    token = re.sub(r"^[^\w]+", "", token)
    token = re.sub(r"[^\w]+$", "", token)
    return token


def _tokens_lower(tokens: Iterable[str]) -> List[str]:
    lowered: List[str] = []
    for token in tokens:
        if "-" in token:
            lowered.extend(_clean_token(part) for part in token.split("-") if part)
        else:
            lowered.append(_clean_token(token))
    return [t for t in lowered if t]


def _extract_first_number(tokens: Iterable[str]) -> Optional[float]:
    for token in tokens:
        if not token:
            continue
        match = re.search(r"[-+]?\d*\.?\d+", token)
        if match:
            try:
                return float(match.group())
            except ValueError:
                continue
    return None


def _normalize_duration(tokens: Sequence[str]) -> Optional[int]:
    lowered = _tokens_lower(tokens)
    if not lowered:
        return None

    if "half" in lowered and any(unit in lowered for unit in ("hour", "hours", "hr", "hrs")):
        return 30

    value = _extract_first_number(lowered)
    if value is None:
        return None

    if any(unit in lowered for unit in ("hour", "hours", "hr", "hrs")):
        return int(round(value * 60))
    return int(round(value))


def _normalize_distance(tokens: Sequence[str]) -> Optional[float]:
    lowered = _tokens_lower(tokens)
    if not lowered:
        return None

    value = _extract_first_number(lowered)
    if value is None:
        return None

    if any(unit in lowered for unit in ("mile", "miles", "mi")):
        return round(value * 1.60934, 2)
    if any(unit in lowered for unit in ("meter", "meters", "m")):
        return round(value / 1000.0, 2)
    return round(value, 2)


def _normalize_elevation(tokens: Sequence[str]) -> Optional[int]:
    lowered = _tokens_lower(tokens)
    if not lowered:
        return None

    value = _extract_first_number(lowered)
    if value is None:
        return None
    if any(unit in lowered for unit in ("foot", "feet", "ft")):
        return int(round(value * 0.3048))
    return int(round(value))


def _normalize_route_type(tokens: Sequence[str]) -> Optional[str]:
    text = " ".join(_tokens_lower(tokens))
    if not text:
        return None
    for canonical, variants in ROUTE_TYPE_MAP.items():
        for variant in variants:
            if text == variant or text.replace(" ", "") == variant.replace(" ", ""):
                return canonical
    return None


def _normalize_category(tokens: Sequence[str]) -> Optional[str]:
    text = _clean_token(" ".join(tokens))
    if not text:
        return None
    if text in CANON_LOOKUP:
        return CANON_LOOKUP[text]
    singular = text.rstrip("s")
    if singular in CANON_LOOKUP:
        return CANON_LOOKUP[singular]
    return text


_TIME_PATTERN = re.compile(r"(\d{1,2}(?::\d{2})?)")


def _parse_time_token(value: str) -> Tuple[int, int]:
    if ":" in value:
        hour_str, minute_str = value.split(":", 1)
        return int(hour_str), int(minute_str)
    return int(value), 0


def _format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _normalize_time_window(tokens: Sequence[str]) -> Optional[Dict[str, str]]:
    lowered_tokens = _tokens_lower(tokens)
    if not lowered_tokens:
        return None

    token_text = " ".join(lowered_tokens)
    meridiem_hint: Optional[str] = None
    if "pm" in lowered_tokens:
        meridiem_hint = "pm"
    elif "am" in lowered_tokens:
        meridiem_hint = "am"

    matches = list(_TIME_PATTERN.finditer(token_text))
    times_24h: List[Tuple[int, int]] = []
    if matches:
        for match in matches:
            hour, minute = _parse_time_token(match.group(1))
            if meridiem_hint == "pm" and hour < 12:
                hour += 12
            elif meridiem_hint == "am" and hour == 12:
                hour = 0
            times_24h.append((hour, minute))

        if len(times_24h) >= 2:
            start_hour, start_minute = times_24h[0]
            end_hour, end_minute = times_24h[1]
            return {
                "start_local": _format_time(start_hour, start_minute),
                "end_local": _format_time(end_hour, end_minute),
            }
        if len(times_24h) == 1:
            start_hour, start_minute = times_24h[0]
            return {
                "start_local": _format_time(start_hour, start_minute),
                "end_local": _format_time(min(start_hour + 2, 23), start_minute),
            }

    keyword_ranges = [
        ({"early", "morning"}, ("05:00", "07:00")),
        ({"morning"}, ("08:00", "10:00")),
        ({"afternoon"}, ("12:00", "15:00")),
        ({"evening"}, ("18:00", "21:00")),
        ({"tonight"}, ("18:00", "21:00")),
        ({"weekend"}, ("12:00", "15:00")),
    ]
    token_set = set(lowered_tokens)
    for keywords, (start, end) in keyword_ranges:
        if keywords.issubset(token_set):
            return {"start_local": start, "end_local": end}

    return None


def build_route_criteria(intent: str, spans: Sequence[SlotSpan]) -> RouteCriteria:
    include_categories: List[str] = []
    avoid_categories: List[str] = []
    route_type: Optional[str] = None
    duration_min: Optional[int] = None
    distance_km: Optional[float] = None
    radius_km: Optional[float] = None
    elevation_gain_min_m: Optional[int] = None
    pet_friendly: Optional[bool] = None
    time_window: Optional[Dict[str, str]] = None

    for span in spans:
        tag = span.label_tag
        if tag == "CAT_INC":
            category = _normalize_category(span.tokens)
            if category and category not in include_categories:
                include_categories.append(category)
        elif tag == "CAT_AVD":
            category = _normalize_category(span.tokens)
            if category and category not in avoid_categories:
                avoid_categories.append(category)
        elif tag == "ROUTE_TYPE":
            normalized = _normalize_route_type(span.tokens)
            if normalized:
                route_type = normalized
        elif tag == "DURATION":
            normalized = _normalize_duration(span.tokens)
            if normalized is not None:
                duration_min = normalized
        elif tag == "DISTANCE":
            normalized = _normalize_distance(span.tokens)
            if normalized is not None:
                distance_km = normalized
        elif tag == "RADIUS":
            normalized = _normalize_distance(span.tokens)
            if normalized is not None:
                radius_km = normalized
        elif tag == "ELEV_MIN":
            normalized = _normalize_elevation(span.tokens)
            if normalized is not None:
                elevation_gain_min_m = normalized
        elif tag == "PET":
            if intent == "negation":
                pet_friendly = False
            else:
                pet_friendly = True
        elif tag == "TIMEWIN":
            if intent == "negation":
                time_window = None
            else:
                normalized = _normalize_time_window(span.tokens)
                if normalized:
                    time_window = normalized

    criteria = RouteCriteria()

    if include_categories:
        criteria.include_categories = include_categories
    if avoid_categories:
        criteria.avoid_categories = avoid_categories
    if route_type:
        criteria.route_type = route_type
    if duration_min is not None:
        criteria.duration_min = duration_min
    if distance_km is not None:
        criteria.distance_km = distance_km
    if radius_km is not None:
        criteria.radius_km = radius_km
    if elevation_gain_min_m is not None:
        criteria.elevation_gain_min_m = elevation_gain_min_m
    if pet_friendly is not None:
        criteria.pet_friendly = pet_friendly
    if time_window is not None:
        criteria.time_window = time_window

    criteria_dict = criteria.dict()
    return RouteCriteria(**criteria_dict)

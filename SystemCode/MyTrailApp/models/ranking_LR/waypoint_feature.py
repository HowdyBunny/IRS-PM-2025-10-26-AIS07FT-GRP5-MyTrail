from __future__ import annotations
import os
import json
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import math

#############################
# Utilities
#############################

def _to_seconds(duration: Any) -> float:
    """Parse duration which may be like "8752s" or a numeric seconds value."""
    if duration is None:
        return float("nan")
    if isinstance(duration, (int, float)):
        return float(duration)
    s = str(duration).strip().lower()
    if s.endswith("s") and s[:-1].isdigit():
        try:
            return float(s[:-1])
        except Exception:
            return float("nan")
    # Fallback: try float
    try:
        return float(s)
    except Exception:
        return float("nan")


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _polyline_bbox_area_km2(viewport: Dict[str, Any] | None) -> float:
    """Approximate area from viewport bounds if present."""
    if not viewport or "low" not in viewport or "high" not in viewport:
        return float("nan")
    low, high = viewport.get("low", {}), viewport.get("high", {})
    lat1, lon1 = low.get("latitude"), low.get("longitude")
    lat2, lon2 = high.get("latitude"), high.get("longitude")
    if None in (lat1, lon1, lat2, lon2):
        return float("nan")
    # Approximate area by multiplying edge lengths in km (haversine across edges)
    width_km = _haversine_km(lat1, lon1, lat1, lon2)
    height_km = _haversine_km(lat1, lon1, lat2, lon1)
    return width_km * height_km


def _entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p + 1e-12)
    return ent

#############################
# Feature Extractor
#############################

class RouteFeatureExtractor(BaseEstimator, TransformerMixin):
    """Transforms a list of route dicts into a list of flat feature dicts.

    Each route becomes a dictionary of numeric/categorical features
    compatible with DictVectorizer.
    """

    def __init__(self, random_state: int | None = 42):
        self.random_state = random_state
        random.seed(random_state)
        np.random.seed(random_state if random_state is not None else None)

    def fit(self, X: List[Dict[str, Any]], y: Any = None):
        # Stateless
        return self

    def transform(self, X: List[Dict[str, Any]]) -> List[Dict[str, float]]:
        feats: List[Dict[str, float]] = []
        for r in X:
            feats.append(self._one_route_features(r))
        return feats

    # --- per-route feature engineering ---
    def _one_route_features(self, r: Dict[str, Any]) -> Dict[str, float]:
        f: Dict[str, float] = {}

        # Basic route-level signals
        f["distance_m"] = _safe_float(r.get("distance"))
        f["duration_s"] = _to_seconds(r.get("duration"))

        metadata = r.get("metadata", {}) or {}
        route_type = (metadata.get("route_type") or "").strip().lower()
        if route_type:
            f[f"route_type={route_type}"] = 1.0

        categories_used = metadata.get("categories_used") or []
        f["categories_used_count"] = float(len(categories_used))
        for cat in categories_used:
            if not cat:
                continue
            f[f"meta_category={str(cat).strip().lower()}"] = 1.0

        # Geometry / viewport scale (rough compactness proxy)
        viewport = ((r.get("geometry") or {}).get("viewport"))
        f["viewport_area_km2"] = _polyline_bbox_area_km2(viewport)

        # Waypoint aggregation
        wps: List[Dict[str, Any]] = r.get("waypoints") or []
        f["waypoint_count"] = float(len(wps))

        ratings = [
            _safe_float(w.get("rating"))
            for w in wps
            if w.get("rating") is not None
        ]
        ratings = [x for x in ratings if not math.isnan(x)]
        if ratings:
            f["wp_rating_mean"] = float(np.mean(ratings))
            f["wp_rating_min"] = float(np.min(ratings))
            f["wp_rating_max"] = float(np.max(ratings))
            f["wp_rating_std"] = float(np.std(ratings))
        else:
            # leave as NaN; DictVectorizer will ignore missing keys
            pass

        # Distance between consecutive waypoint locations (rough internal path proxy)
        coords: List[Tuple[float, float]] = []
        for w in wps:
            loc = w.get("location") or {}
            lat, lng = loc.get("lat"), loc.get("lng")
            if lat is not None and lng is not None:
                coords.append((float(lat), float(lng)))
        if len(coords) >= 2:
            segs = [
                _haversine_km(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
                for i in range(len(coords) - 1)
            ]
            f["wp_path_len_km"] = float(sum(segs))
            f["wp_path_mean_seg_km"] = float(np.mean(segs))
            f["wp_path_max_seg_km"] = float(np.max(segs))

        # Waypoint declared distance_km aggregates (if provided)
        declared_dists = [
            _safe_float(w.get("distance_km"))
            for w in wps
            if w.get("distance_km") is not None
        ]
        declared_dists = [x for x in declared_dists if not math.isnan(x)]
        if declared_dists:
            f["wp_declared_dist_sum_km"] = float(sum(declared_dists))
            f["wp_declared_dist_mean_km"] = float(np.mean(declared_dists))

        # Category / search_category distributions and entropy
        cat_counts: Dict[str, int] = {}
        search_cat_counts: Dict[str, int] = {}
        for w in wps:
            cat = (w.get("category") or "").strip().lower()
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            scat = (w.get("search_category") or "").strip().lower()
            if scat:
                search_cat_counts[scat] = search_cat_counts.get(scat, 0) + 1
        if cat_counts:
            f["wp_cat_unique"] = float(len(cat_counts))
            f["wp_cat_entropy"] = _entropy(list(cat_counts.values()))
            for k, v in cat_counts.items():
                f[f"wp_cat={k}"] = float(v)
        if search_cat_counts:
            f["wp_search_cat_unique"] = float(len(search_cat_counts))
            f["wp_search_cat_entropy"] = _entropy(list(search_cat_counts.values()))
            for k, v in search_cat_counts.items():
                f[f"wp_search_cat={k}"] = float(v)

        return f

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Any, Dict, List
from collections import Counter
from collections import  defaultdict

def parse_duration_seconds(d: Any) -> float:
    if d is None: return np.nan
    if isinstance(d, (int, float)): return float(d)
    s = str(d).strip().lower()
    if s.endswith("s"):
        try: return float(s[:-1])
        except: return np.nan
    try: return float(s)
    except: return np.nan

def safe_get(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if cur is None or not isinstance(cur, dict): return default
        cur = cur.get(k)
    return default if cur is None else cur

def viewport_area(geometry: dict) -> float:
    low_lat = safe_get(geometry, "viewport", "low", "latitude", default=np.nan)
    low_lng = safe_get(geometry, "viewport", "low", "longitude", default=np.nan)
    high_lat = safe_get(geometry, "viewport", "high", "latitude", default=np.nan)
    high_lng = safe_get(geometry, "viewport", "high", "longitude", default=np.nan)
    if any(pd.isna([low_lat, low_lng, high_lat, high_lng])): return np.nan
    return abs(high_lat - low_lat) * abs(high_lng - low_lng)

def duration_per_km(distance_m: Any, duration_s: Any) -> float:
    dkm = (float(distance_m) / 1000) if pd.notna(distance_m) else np.nan
    ds = float(duration_s) if pd.notna(duration_s) else np.nan
    if dkm and dkm > 0 and pd.notna(ds): return ds / dkm
    return np.nan

class RouteFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, top_k_categories: int = 12):
        self.top_k_categories = top_k_categories
        self.fitted_categories_: List[str] = []
        self.fitted_route_types_: List[str] = []

    def fit(self, X: List[Dict[str, Any]], y=None):
        cat_counter = Counter()
        route_type_counter = Counter()
        for r in X:
            wps = r.get("waypoints", []) or []
            for w in wps:
                for key in ("category", "search_category"):
                    c = (w.get(key) or "").strip().lower()
                    if c: cat_counter[c] += 1
            rt = safe_get(r, "metadata", "route_type", default="")
            if rt: route_type_counter[rt] += 1
        self.fitted_categories_ = [c for c, _ in cat_counter.most_common(self.top_k_categories)]
        self.fitted_route_types_ = [t for t, _ in route_type_counter.most_common()]
        return self

    def transform(self, X: List[Dict[str, Any]]):
        rows = []
        for r in X:
            distance = r.get("distance", np.nan)
            duration_s = parse_duration_seconds(r.get("duration"))
            wps = r.get("waypoints", []) or []
            n_wp = len(wps)
            ratings = [w.get("rating") for w in wps if w.get("rating") is not None]
            avg_rating = np.mean(ratings) if ratings else np.nan
            max_rating = np.max(ratings) if ratings else np.nan

            cat_counts = Counter()
            for w in wps:
                for key in ("category", "search_category"):
                    c = (w.get(key) or "").strip().lower()
                    if c: cat_counts[c] += 1

            row: Dict[str, Any] = {}
            total_cats = sum(cat_counts.values()) or 1
            for c in getattr(self, "fitted_categories_", []):
                row[f"cat_{c}_ratio"] = cat_counts.get(c, 0) / total_cats

            search_radius = safe_get(r, "metadata", "search_radius_km", default=np.nan)
            route_type = safe_get(r, "metadata", "route_type", default=None)
            for t in getattr(self, "fitted_route_types_", []):
                row[f"route_type_{t}"] = 1.0 if route_type == t else 0.0

            predicted_score = safe_get(r, "metadata", "predicted_score", default=np.nan)
            user_score = r.get("score", np.nan)
            area = viewport_area(r.get("geometry", {}) or {})
            pace = duration_per_km(distance, duration_s)

            row.update(dict(
                distance_m=distance, duration_s=duration_s, n_waypoints=n_wp,
                avg_rating=avg_rating, max_rating=max_rating, search_radius_km=search_radius,
                predicted_score=predicted_score, score=user_score, viewport_area=area, sec_per_km=pace
            ))
            rows.append(row)

        df = pd.DataFrame(rows).fillna(0.0)
        df = df[sorted(df.columns)]
        self.feature_names_ = list(df.columns)
        return df.values
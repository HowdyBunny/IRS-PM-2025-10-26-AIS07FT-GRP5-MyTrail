# -*- coding: utf-8 -*-
import os, re
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.base import BaseEstimator, TransformerMixin
from route_feature import RouteFeatureExtractor, parse_duration_seconds, safe_get, viewport_area, duration_per_km
# ========= theme inference utils =========
def distance_bucket(distance_m: float) -> str:
    if np.isnan(distance_m): return "Unknown"
    km = distance_m / 1000.0
    if km < 5: return "Short"
    elif km < 10: return "Medium"
    else: return "Long"

def infer_theme_name(routes_in_cluster: List[Dict[str, Any]]) -> str:
    cat_counter = Counter()
    distances, ratings = [], []
    for r in routes_in_cluster:
        distances.append(r.get("distance", np.nan))
        for w in r.get("waypoints", []) or []:
            for key in ("category", "search_category"):
                c = (w.get(key) or "").strip().title()
                if c:
                    cat_counter[c] += 1
        rv = [w.get("rating") for w in r.get("waypoints", []) or [] if w.get("rating") is not None]
        ratings.extend(rv)

    top = cat_counter.most_common(2)
    if top and (len(top) == 1 or (len(top) == 2 and top[0][1] >= top[1][1] * 1.2)):
        theme = top[0][0]
        if theme.lower() in {"park", "nature", "scenic"} and len(top) >= 2:
            return f"{top[0][0]} & {top[1][0]}"
        return theme

    dist_med = np.nanmedian(distances) if distances else np.nan
    bucket = distance_bucket(dist_med if pd.notna(dist_med) else np.nan)
    if ratings:
        m = float(np.mean(ratings))
        suffix = "Scenic" if m >= 4.5 else ("Popular" if m >= 4.2 else "Urban Mix")
    else:
        suffix = "Mixed"
    return f"{bucket} • {suffix}"

# ========= load model =========
MODEL_PATH = os.getenv("MODEL_PATH", "./out/route_cluster_model.pkl")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
pipe = joblib.load(MODEL_PATH)

# ========= API =========
app = FastAPI(title="MyTrail Cluster Service", version="1.0.0")

class PredictBody(BaseModel):
    routes: List[Dict[str, Any]]

@app.get("/health")
def health():
    return {"status":"ok","model":os.path.basename(MODEL_PATH)}

@app.post("/predict")
def predict(payload: PredictBody):
    routes = payload.routes or []
    if not routes:
        return {"themes":[]}
    labels = pipe.predict(routes)  # pipeline: RouteFeatureExtractor -> StandardScaler -> (MiniBatch)KMeans
    cluster_to_routes = defaultdict(list)
    for r, lbl in zip(routes, labels):
        cluster_to_routes[int(lbl)].append(r)

    used, themes = {}, []
    for idx, cid in enumerate(sorted(cluster_to_routes.keys())):
        group = cluster_to_routes[cid]
        name = infer_theme_name(group)
        themes.append({"id": f"theme_{idx+1}", "ThemeName": name, "Routes": group})
    return {"themes": themes}

@app.post("/predict_labels")
def predict_labels(payload: PredictBody):
    routes = payload.routes or []
    labels = pipe.predict(routes) if routes else []
    return {"labels": [int(x) for x in labels]}
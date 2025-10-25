#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Route Ranking — Linear Regression (scikit-learn)

• Extracts engineered features from each route + its waypoints
• Trains a LinearRegression model to predict a numeric score
• Saves a single .pkl containing a full sklearn Pipeline (vectorizer + model)
• Supports batch scoring on new routes with the same schema

Input training data format (JSON or JSONL):
[
  {
    "id": "route_1",
    "name": "Via Bay East Garden & Fort Canning Tree Tunnel",
    "distance": 10551,                 # meters (int/float)
    "duration": "8752s",              # string like "8752s" or seconds number
    "waypoints": [ { ... }, ... ],     # list of POIs/steps with ratings, categories, etc.
    "geometry": { ... },
    "metadata": { "route_type": "loop", "categories_used": ["nature","park"], ... },
    "score": 0.8                       # target label for training (float)
  },
  ...
]

Usage
-----
Train:
  python train.py train --data data/train_routes.json --out model/route_ranker.pkl
  # Optional: evaluate with holdout split and print metrics

Predict (score new routes):
  python train.py predict --model model/route_ranker.pkl --data data/new_routes.json --out data/new_routes_scored.json

Notes
-----
• The saved .pkl is a sklearn Pipeline and can be loaded to score any future route dicts.
• Feature set is intentionally generic & robust to missing fields.
"""

from __future__ import annotations
import argparse
import json
import math
import os
import random
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
from waypoint_feature import RouteFeatureExtractor, _to_seconds, _safe_float, _polyline_bbox_area_km2
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib


#############################
# IO helpers
#############################

def _load_routes(path: str) -> List[Dict[str, Any]]:
    """Load JSON array or JSONL file of route dicts."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            return []
        if text[0] == "[":
            data = json.loads(text)
            assert isinstance(data, list), "Expected a JSON array at top-level"
            return data
        # otherwise JSONL
        routes: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            routes.append(json.loads(line))
        return routes


def _extract_xy(routes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], np.ndarray, List[str]]:
    X: List[Dict[str, Any]] = []
    y_list: List[float] = []
    ids: List[str] = []
    for r in routes:
        if "score" not in r:
            # skip items without label for training
            continue
        ids.append(str(r.get("id")))
        y_list.append(_safe_float(r.get("score")))
        X.append(r)
    if not X:
        raise ValueError("No labeled routes with 'score' found in the dataset.")
    return X, np.array(y_list, dtype=float), ids

#############################
# Train & Predict
#############################

def train_cmd(args: argparse.Namespace) -> None:
    routes = _load_routes(args.data)
    X_dicts, y, ids = _extract_xy(routes)

    fe = RouteFeatureExtractor(random_state=args.random_state)

    pipe = Pipeline(
        steps=[
            ("fe", fe),
            ("dv", DictVectorizer(sparse=False)),
            ("lr", LinearRegression())
        ]
    )

    X_train, X_val, y_train, y_val = train_test_split(
        X_dicts, y, test_size=args.val_ratio, random_state=args.random_state
    )

    pipe.fit(X_train, y_train)

    # Evaluation
    y_pred = pipe.predict(X_val) if len(X_val) > 0 else np.array([])
    if y_pred.size > 0:
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        print(f"Validation: MAE={mae:.4f} | R2={r2:.4f} | n={len(y_val)}")
    else:
        print("Trained on full data (no validation split)")

    # Save model pipeline
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    joblib.dump(pipe, args.out)
    print(f"Saved model pipeline to: {args.out}")

    # Optionally score the training set (or a provided --score-on file) for quick sanity check
    if args.score_on:
        print(f"Scoring file: {args.score_on}")
        score_cmd(argparse.Namespace(model=args.out, data=args.score_on, out=args.scored_out or "scored.json"))


def score_cmd(args: argparse.Namespace) -> None:
    pipe: Pipeline = joblib.load(args.model)
    routes = _load_routes(args.data)

    # Predict scores for each route (no requirement for 'score' field here)
    preds = pipe.predict(routes)

    # Attach predictions and write out
    out_items = []
    for r, p in zip(routes, preds):
        item = dict(r)
        item["predicted_score"] = float(p)
        out_items.append(item)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out_items)} scored routes → {args.out}")

#############################
# CLI
#############################

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train/predict linear regression route ranker")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Train
    p_train = sub.add_parser("train", help="Train Linear Regression model and save .pkl")
    p_train.add_argument("--data", required=True, help="Path to JSON or JSONL training file")
    p_train.add_argument("--out", "--output", dest="out", required=True,help="Where to save the sklearn Pipeline .pkl")
    p_train.add_argument("--val-ratio", type=float, default=0.2, help="Holdout ratio for validation (default 0.2)")
    p_train.add_argument("--random-state", type=int, default=42, help="Random seed for split/num features")
    p_train.add_argument("--score-on", default=None, help="Optional: JSON/JSONL file to score after training (defaults to training file if omitted)")
    p_train.add_argument("--scored-out", default=None, help="Optional: where to write the scored output JSON")
    p_train.set_defaults(func=train_cmd)

    # Predict
    p_pred = sub.add_parser("predict", help="Load .pkl and score new routes")
    p_pred.add_argument("--model", required=True, help="Path to saved sklearn Pipeline .pkl")
    p_pred.add_argument("--data", required=True, help="Path to JSON or JSONL with new routes")
    p_pred.add_argument("--out", "--output", dest="out", required=True, help="Where to write JSON with predicted_score field")
    p_pred.set_defaults(func=score_cmd)

    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

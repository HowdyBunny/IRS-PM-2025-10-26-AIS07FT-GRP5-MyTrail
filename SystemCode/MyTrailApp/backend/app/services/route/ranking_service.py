"""Route ranking service that loads a persisted regression model."""
from __future__ import annotations
import json
import sys
import app.artifacts.waypoint_feature as waypoint_feature
sys.modules['waypoint_feature'] = waypoint_feature
from app.artifacts.waypoint_feature import RouteFeatureExtractor
import sys
from pathlib import Path
from typing import Dict, List, Optional
import math

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _sanitize_feature_dict(d: dict) -> dict:
    """Drop keys with NaN/Inf/None values; convert all remaining entries to floats."""
    clean = {}
    for k, v in d.items():
        # Skip None values
        if v is None:
            continue
        # Numeric values: filter out NaN/Inf, convert to float
        if isinstance(v, (int, float)):
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                continue
            clean[k] = fv
        else:
            # Category/one-hot keys are typically 1.0 or bool/int; drop non-numeric garbage values
            try:
                fv = float(v)
                if not (math.isnan(fv) or math.isinf(fv)):
                    clean[k] = fv
            except Exception:
                # If it were a valid one-hot value (1.0) we would not get here; skip conservatively
                continue
    return clean



class RouteRankingService:

    """Score and rank routes using a pre-trained regression model."""

    def __init__(self, model_path: Optional[str | Path] = None) -> None:
        if model_path is None:
            model_path = PROJECT_ROOT / "app" / "artifacts" / "ranking_LR_model.pkl"
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Route ranking model artefact not found at {self.model_path}"
            )

        self._model = self._load_model(self.model_path)

    def _load_model(self, path: Path):
        import joblib
        return joblib.load(path)

    
    def rank_routes(self, routes: List[Dict]) -> List[Dict]:
        if not routes:
            return []

        # extractor = RouteFeatureExtractor()
        # feature_vectors = extractor.transform(routes)
        # feature_vectors = [_sanitize_feature_dict(fv) for fv in feature_vectors]
        # Support models that expose either predict_batch or predict
        if hasattr(self._model, "predict_batch"):
            scores = self._model.predict_batch(routes)
        else:
            scores = self._model.predict(routes)

        for route, score in zip(routes, scores):
            predicted = float(score)
            route["score"] = predicted
            # route.setdefault("metadata", {})["score"] = predicted

        return sorted(routes, key=lambda route: route.get("score", 0.0), reverse=True)

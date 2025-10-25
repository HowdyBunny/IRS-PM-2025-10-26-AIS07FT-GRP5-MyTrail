# app.py
from __future__ import annotations
import os, sys, types, json
import joblib
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from pydantic import BaseModel

import waypoint_feature  # Ensure we can import the actual class implementation

DEFAULT_MODEL_PATH = os.getenv("MODEL_PATH", "out/ranking_LR_model.pkl")

app = FastAPI(title="Route Ranker Inference API", version="1.1.0")

class ModelHolder:
    pipe = None
    path = None

    @classmethod
    def _apply_unpickle_shim(cls):
        # Backwards compatibility: older models reference __main__.RouteFeatureExtractor
        if "__main__" not in sys.modules:
            sys.modules["__main__"] = types.ModuleType("__main__")
        sys.modules["__main__"].RouteFeatureExtractor = waypoint_feature.RouteFeatureExtractor

    @classmethod
    def load(cls, path: str):
        cls._apply_unpickle_shim()
        try:
            pipe = joblib.load(path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load model: {e}")
        cls.pipe = pipe
        cls.path = path

    @classmethod
    def ensure_loaded(cls):
        if cls.pipe is None:
            cls.load(DEFAULT_MODEL_PATH)


@app.on_event("startup")
def _startup():
    ModelHolder.ensure_loaded()


class PredictRequest(BaseModel):
    routes: List[Dict[str, Any]]
    return_items: bool = True

def _predict(routes: List[Dict[str, Any]]) -> List[float]:
    ModelHolder.ensure_loaded()
    try:
        preds = ModelHolder.pipe.predict(routes)
        return [float(p) for p in preds]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {e}")

@app.get("/health")
def health():
    ModelHolder.ensure_loaded()
    return {"status": "ok", "model_path": ModelHolder.path, "version": app.version}

@app.post("/predict")
def predict(req: PredictRequest):
    preds = _predict(req.routes)
    if not req.return_items:
        return {"count": len(preds), "predictions": preds}
    items = []
    for r, p in zip(req.routes, preds):
        x = dict(r)
        x["predicted_score"] = p
        items.append(x)
    return {"count": len(items), "items": items}

@app.post("/predict_file")
async def predict_file(file: UploadFile = File(...), return_items: bool = True):
    raw = await file.read()
    text = raw.decode("utf-8").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        routes = json.loads(text) if text[0] == "[" else [json.loads(l) for l in text.splitlines() if l.strip()]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {e}")
    preds = _predict(routes)
    if not return_items:
        return {"count": len(preds), "predictions": preds}
    return {"count": len(preds), "items": [{**r, "predicted_score": p} for r, p in zip(routes, preds)]}

@app.post("/reload")
def reload_model(path: Optional[str] = Body(None, embed=True)):
    target = path or os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
    ModelHolder.load(target)
    return {"message": "reloaded", "model_path": target}

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import torch
from flask import Flask, jsonify, request
from threading import Lock
from transformers import AutoTokenizer
from pydantic import ValidationError

from src.data_utils import compute_word_ids
from src.modeling import JointIntentSlotModel
from src.postprocess import bio_to_spans, build_route_criteria

MODEL_DIR = Path("trained_model")
MAX_LENGTH = 128
HOST = "192.168.0.207"
PORT = 4000
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class ModelService:
    def __init__(self, model_dir: Path) -> None:
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory '{model_dir}' does not exist. Run training first.")

        label_path = model_dir / "label_maps.json"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing label map file at '{label_path}'.")

        with label_path.open("r", encoding="utf-8") as f:
            label_data = json.load(f)

        self.intent2id: Dict[str, int] = {k: int(v) for k, v in label_data["intent2id"].items()}
        self.slot2id: Dict[str, int] = {k: int(v) for k, v in label_data["slot2id"].items()}
        self.id2intent: Dict[int, str] = {idx: label for label, idx in self.intent2id.items()}
        self.id2slot: Dict[int, str] = {idx: label for label, idx in self.slot2id.items()}

        metadata_path = model_dir / "metadata.json"
        if metadata_path.exists():
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            encoder_name = metadata.get("encoder_name", "microsoft/deberta-v3-base")
        else:
            encoder_name = "microsoft/deberta-v3-base"

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, use_fast=False)

        self.model = JointIntentSlotModel(
            encoder_name=encoder_name,
            num_intents=len(self.intent2id),
            num_slots=len(self.slot2id),
        )
        state_dict = torch.load(model_dir / "pytorch_model.bin", map_location=DEVICE)
        self.model.load_state_dict(state_dict)
        self.model.to(DEVICE)
        self.model.eval()

    def predict(self, text: str) -> Dict[str, object]:
        words = text.strip().split()
        if not words:
            raise ValueError("Input text must contain at least one token.")

        encoded = self.tokenizer(
            words,
            is_split_into_words=True,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_attention_mask=True,
            return_tensors=None,
            add_special_tokens=True,
            return_special_tokens_mask=True,
        )
        word_ids = compute_word_ids(self.tokenizer, encoded, words)

        input_ids = torch.tensor([encoded["input_ids"]], dtype=torch.long, device=DEVICE)
        attention_mask = torch.tensor([encoded["attention_mask"]], dtype=torch.long, device=DEVICE)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        intent_logits = outputs["intent_logits"].squeeze(0)
        slot_logits = outputs["slot_logits"].squeeze(0)

        intent_probabilities = torch.softmax(intent_logits, dim=-1)
        intent_idx = int(torch.argmax(intent_probabilities).item())
        intent_label = self.id2intent[intent_idx]
        intent_confidence = float(intent_probabilities[intent_idx].item())

        slot_indices = torch.argmax(slot_logits, dim=-1).cpu().tolist()
        slots: List[Dict[str, str]] = []
        seen_words: set[int] = set()
        for position, word_id in enumerate(word_ids):
            if word_id is None or word_id in seen_words or word_id >= len(words):
                continue
            label_id = int(slot_indices[position])
            slots.append(
                {
                    "word": words[word_id],
                    "label": self.id2slot[label_id],
                }
            )
            seen_words.add(word_id)

        return {
            "intent": {
                "label": intent_label,
                "confidence": intent_confidence,
            },
            "slots": slots,
        }


app = Flask(__name__)
_service_lock = Lock()
service: Optional[ModelService] = None


def get_service() -> ModelService:
    global service
    if service is None:
        with _service_lock:
            if service is None:
                service = ModelService(MODEL_DIR)
    return service


@app.route("/health", methods=["GET"])
def health() -> object:
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict_route() -> object:
    payload = request.get_json(force=True, silent=True)
    if not payload or "text" not in payload:
        return jsonify({"error": "Request JSON must include 'text'."}), 400

    text = str(payload["text"])
    if not text.strip():
        return jsonify({"error": "Input text must be non-empty."}), 400

    try:
        prediction = get_service().predict(text)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Model inference failed."}), 500
    try:
        spans = bio_to_spans(prediction["slots"])
        route_criteria = build_route_criteria(prediction["intent"]["label"], spans)
    except ValidationError as exc:
        return jsonify({"error": f"Schema validation failed: {exc}"}), 500

    return jsonify(route_criteria.dict())


if __name__ == "__main__":
    try:
        get_service()
    except FileNotFoundError as exc:
        raise SystemExit(f"Model loading failed: {exc}") from exc
    app.run(host=HOST, port=PORT)

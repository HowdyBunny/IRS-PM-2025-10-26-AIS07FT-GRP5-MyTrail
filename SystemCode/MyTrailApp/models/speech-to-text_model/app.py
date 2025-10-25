import os
import subprocess
import tempfile
from typing import Dict, Optional

import torch
import torchaudio
from flask import Flask, jsonify, request
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def create_app() -> Flask:
    app = Flask(__name__)

    model_dir = os.environ.get("WHISPER_MODEL_DIR", "whisper-en-finetuned")
    if not os.path.isdir(model_dir):
        raise RuntimeError(
            f"Model directory '{model_dir}' does not exist. "
            "Set WHISPER_MODEL_DIR to the directory holding the fine-tuned Whisper model."
        )

    processor_load_paths = [model_dir, os.path.join(model_dir, "processor")]
    processor = None
    for path in processor_load_paths:
        if os.path.isdir(path):
            try:
                processor = WhisperProcessor.from_pretrained(path, local_files_only=True)
                break
            except (OSError, ValueError):
                continue
    if processor is None:
        raise RuntimeError(
            "Unable to load WhisperProcessor. Ensure 'preprocessor_config.json' is present "
            "either in the model directory or in a 'processor' subdirectory."
        )
    model = WhisperForConditionalGeneration.from_pretrained(model_dir, local_files_only=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    target_sample_rate: int = processor.feature_extractor.sampling_rate

    def _prepare_waveform(path: str) -> torch.Tensor:
        try:
            waveform, sample_rate = torchaudio.load(path)
        except RuntimeError:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as converted:
                converted_path = converted.name
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        path,
                        "-ac",
                        "1",
                        "-ar",
                        str(target_sample_rate),
                        converted_path,
                    ],
                    check=True,
                )
                waveform, sample_rate = torchaudio.load(converted_path)
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                raise RuntimeError(
                    "Failed to load audio. Ensure FFmpeg is installed and the file is a supported format."
                ) from exc
            finally:
                try:
                    os.unlink(converted_path)
                except OSError:
                    pass

        if waveform.ndim == 2 and waveform.shape[0] > 1:
            # Convert multi-channel audio to mono by averaging channels.
            waveform = waveform.mean(dim=0, keepdim=True)

        waveform = waveform.squeeze(0)

        if sample_rate != target_sample_rate:
            waveform = torchaudio.functional.resample(
                waveform, sample_rate, target_sample_rate
            )

        return waveform

    def _get_generate_kwargs(language: Optional[str], task: str) -> Dict:
        if not language:
            return {}
        try:
            forced_decoder_ids = processor.get_decoder_prompt_ids(
                language=language, task=task
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported language '{language}'. "
                "Use ISO-639-1 codes, e.g. 'en', 'zh', 'de'."
            ) from exc
        return {"forced_decoder_ids": forced_decoder_ids}

    @app.route("/health", methods=["GET"])
    def health() -> tuple:
        return jsonify({"status": "ok"}), 200

    @app.route("/transcribe", methods=["POST"])
    def transcribe() -> tuple:
        if "file" not in request.files:
            return jsonify({"error": "Request must include audio file under 'file' field."}), 400

        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"error": "Uploaded file must have a filename."}), 400

        task = request.form.get("task", "transcribe")
        if task not in {"transcribe", "translate"}:
            return jsonify({"error": "Parameter 'task' must be either 'transcribe' or 'translate'."}), 400

        language = request.form.get("language")
        try:
            generate_kwargs = _get_generate_kwargs(language, task)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(uploaded_file.filename)[1]) as tmp:
            uploaded_file.save(tmp.name)
            waveform = _prepare_waveform(tmp.name)

        inputs = processor(
            waveform.numpy(),
            sampling_rate=target_sample_rate,
            return_tensors="pt",
        )

        input_features = inputs.input_features.to(device)

        with torch.inference_mode():
            predicted_ids = model.generate(input_features, **generate_kwargs)

        transcription = processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0]

        detected_language = language or getattr(processor.tokenizer, "language", None)

        return jsonify({"text": transcription, "language": detected_language, "task": task}), 200

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)

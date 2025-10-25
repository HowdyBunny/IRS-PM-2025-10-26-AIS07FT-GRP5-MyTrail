# Joint Intent & Slot Filling Model

This project trains a joint natural language understanding model that predicts both route-finding intents and BIO-formatted slot labels. The model shares a single encoder (`microsoft/deberta-v3-base`) with two task-specific heads trained together.

## Setup
- Install dependencies: `pip install -r requirements.txt`
- Ensure the training (`data/train.jsonl`) and evaluation (`data/test.jsonl`) files follow the provided JSONL format with `slots_bio` entries.
- `microsoft/deberta-v3-base` now defaults to the slow tokenizer to avoid optional `tiktoken` downloads. Pass `--use_fast_tokenizer` if you have the fast tokenizer dependencies set up.

## Training
```
python train.py \
  --train_path data/train.jsonl \
  --eval_path data/test.jsonl \
  --epochs 10 \
  --train_batch_size 16 \
  --eval_batch_size 16 \
  --encoder_lr 3e-5 \
  --head_lr 1e-3
```

Artifacts are saved automatically to `trained_model/` (or override via `--output_dir`). The folder contains the model weights, tokenizer files, `label_maps.json`, and `metadata.json` (records the encoder backbone).

Metrics printed after each epoch include intent accuracy and the slot F1 score (using `seqeval`, ignoring `O` tags). The best model checkpoint and label maps are saved in `--output_dir`.

## Notes
- Adjust `--max_length` if your inputs exceed the default.
- The slot loss weight `λ` defaults to `1.0` and can be changed with `--slot_loss_weight`.
- If you hit import errors about `tiktoken`, `protobuf`, or `sentencepiece`, install them via the requirements list.
- The script automatically separates encoder and head parameters so they can use different learning rates.

## Deployment
- Ensure `train.py` has been run at least once so `trained_model/` contains `pytorch_model.bin`, tokenizer files, `label_maps.json`, and `metadata.json`.
- Start the Flask server: `python app.py`
- The service listens on `192.168.0.207:4000`. Send a POST request to `http://192.168.0.207:4000/predict` with JSON payload `{"text": "your utterance"}` to receive the intent prediction and token-level slots.

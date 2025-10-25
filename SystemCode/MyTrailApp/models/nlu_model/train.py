from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
from seqeval.metrics import f1_score
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm.auto import tqdm
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from src.data_utils import (
    IntentSlotDataset,
    LabelMaps,
    build_label_maps,
    collate_batch,
    load_jsonl,
)
from src.modeling import JointIntentSlotModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Joint intent classification and slot filling training script.")
    parser.add_argument("--train_path", type=Path, default=Path("data/train.jsonl"), help="Path to training data.")
    parser.add_argument("--eval_path", type=Path, default=Path("data/test.jsonl"), help="Path to evaluation data.")
    parser.add_argument("--encoder_name", type=str, default="microsoft/deberta-v3-base", help="Pretrained encoder name.")
    parser.add_argument("--max_length", type=int, default=128, help="Maximum sequence length.")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs.")
    parser.add_argument("--train_batch_size", type=int, default=16, help="Training batch size.")
    parser.add_argument("--eval_batch_size", type=int, default=16, help="Evaluation batch size.")
    parser.add_argument("--encoder_lr", type=float, default=3e-5, help="Learning rate for encoder parameters.")
    parser.add_argument("--head_lr", type=float, default=1e-3, help="Learning rate for classification heads.")
    parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay.")
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Linear warmup ratio.")
    parser.add_argument("--max_grad_norm", type=float, default=1.0, help="Gradient clipping norm.")
    parser.add_argument("--slot_loss_weight", type=float, default=1.0, help="Weight applied to the slot loss.")
    parser.add_argument("--dropout", type=float, default=0.1, help="Dropout applied before the heads.")
    parser.add_argument("--seed", type=int, default=13, help="Random seed.")
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("trained_model"),
        help="Directory to save the trained model.",
    )
    parser.add_argument(
        "--use_fast_tokenizer",
        action="store_true",
        help="Use the fast tokenizer implementation when available.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def create_optimizer(model: JointIntentSlotModel, encoder_lr: float, head_lr: float, weight_decay: float) -> AdamW:
    encoder_parameters = []
    head_parameters = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.startswith("encoder"):
            encoder_parameters.append(param)
        else:
            head_parameters.append(param)
    return AdamW(
        [
            {"params": encoder_parameters, "lr": encoder_lr},
            {"params": head_parameters, "lr": head_lr},
        ],
        weight_decay=weight_decay,
    )


def move_to_device(batch: Dict[str, torch.Tensor], device: torch.device) -> Dict[str, torch.Tensor]:
    batch_on_device = {
        "input_ids": batch["input_ids"].to(device),
        "attention_mask": batch["attention_mask"].to(device),
        "intent_labels": batch["intent_labels"].to(device),
        "slot_labels": batch["slot_labels"].to(device),
    }
    return batch_on_device


@torch.no_grad()
def evaluate(
    model: JointIntentSlotModel,
    dataloader: DataLoader,
    label_maps: LabelMaps,
    device: torch.device,
) -> Tuple[float, float]:
    model.eval()

    intent_correct = 0
    total_examples = 0
    all_true_slots = []
    all_pred_slots = []

    for batch in dataloader:
        batch_device = move_to_device(batch, device)
        outputs = model(
            input_ids=batch_device["input_ids"],
            attention_mask=batch_device["attention_mask"],
        )

        intent_logits = outputs["intent_logits"]
        slot_logits = outputs["slot_logits"]

        intent_preds = intent_logits.argmax(dim=-1)
        intent_labels = batch_device["intent_labels"]

        intent_correct += (intent_preds == intent_labels).sum().item()
        total_examples += intent_labels.size(0)

        slot_preds = slot_logits.argmax(dim=-1).cpu().numpy()
        slot_labels = batch["slot_labels"].cpu().numpy()
        word_ids_batch = batch["word_ids"]

        for pred_seq, label_seq, word_ids in zip(slot_preds, slot_labels, word_ids_batch):
            pred_tags = []
            true_tags = []
            for idx, word_id in enumerate(word_ids):
                if word_id is None:
                    continue
                if label_seq[idx] == -100:
                    continue
                pred_tags.append(label_maps.id2slot[int(pred_seq[idx])])
                true_tags.append(label_maps.id2slot[int(label_seq[idx])])
            all_pred_slots.append(pred_tags)
            all_true_slots.append(true_tags)

    intent_accuracy = intent_correct / max(total_examples, 1)
    slot_f1 = f1_score(all_true_slots, all_pred_slots)
    return intent_accuracy, slot_f1


def save_artifacts(
    model: JointIntentSlotModel,
    tokenizer,
    label_maps: LabelMaps,
    output_dir: Path,
    encoder_name: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_dir / "pytorch_model.bin")
    tokenizer.save_pretrained(output_dir)
    label_data = {
        "intent2id": label_maps.intent2id,
        "slot2id": label_maps.slot2id,
    }
    with (output_dir / "label_maps.json").open("w", encoding="utf-8") as f:
        json.dump(label_data, f, indent=2, ensure_ascii=False)
    metadata = {"encoder_name": encoder_name}
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    train_examples = load_jsonl(args.train_path)
    eval_examples = load_jsonl(args.eval_path)
    label_maps = build_label_maps(train_examples)

    tokenizer = AutoTokenizer.from_pretrained(args.encoder_name, use_fast=args.use_fast_tokenizer)

    train_dataset = IntentSlotDataset(
        train_examples,
        tokenizer=tokenizer,
        label_maps=label_maps,
        max_length=args.max_length,
    )
    eval_dataset = IntentSlotDataset(
        eval_examples,
        tokenizer=tokenizer,
        label_maps=label_maps,
        max_length=args.max_length,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.train_batch_size,
        shuffle=True,
        collate_fn=collate_batch,
    )
    eval_loader = DataLoader(
        eval_dataset,
        batch_size=args.eval_batch_size,
        shuffle=False,
        collate_fn=collate_batch,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = JointIntentSlotModel(
        encoder_name=args.encoder_name,
        num_intents=len(label_maps.intent2id),
        num_slots=len(label_maps.slot2id),
        dropout=args.dropout,
        slot_loss_weight=args.slot_loss_weight,
    ).to(device)

    optimizer = create_optimizer(model, args.encoder_lr, args.head_lr, args.weight_decay)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = math.floor(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    best_eval_f1 = float("-inf")

    for epoch in range(1, args.epochs + 1):
        model.train()
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch}", unit="batch")
        running_loss = 0.0

        for batch in progress_bar:
            batch_device = move_to_device(batch, device)

            outputs = model(
                input_ids=batch_device["input_ids"],
                attention_mask=batch_device["attention_mask"],
                intent_labels=batch_device["intent_labels"],
                slot_labels=batch_device["slot_labels"],
            )
            loss = outputs["loss"]

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            running_loss += loss.item()
            progress_bar.set_postfix(loss=running_loss / (progress_bar.n or 1))

        intent_acc, slot_f1 = evaluate(model, eval_loader, label_maps, device)
        print(f"Epoch {epoch}: intent_acc={intent_acc:.4f}, slot_f1={slot_f1:.4f}")

        if slot_f1 > best_eval_f1 and args.output_dir:
            best_eval_f1 = slot_f1
            save_artifacts(model, tokenizer, label_maps, args.output_dir, args.encoder_name)

    if args.output_dir:
        save_artifacts(model, tokenizer, label_maps, args.output_dir, args.encoder_name)


if __name__ == "__main__":
    main()

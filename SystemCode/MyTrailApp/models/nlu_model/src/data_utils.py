from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class LabelMaps:
    intent2id: Dict[str, int]
    id2intent: Dict[int, str]
    slot2id: Dict[str, int]
    id2slot: Dict[int, str]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def build_label_maps(examples: Iterable[Dict[str, Any]]) -> LabelMaps:
    intents = set()
    slots = set()
    for record in examples:
        intents.add(record["intent"])
        slots.update(label for _, label in record["slots_bio"])
    intent2id = {label: idx for idx, label in enumerate(sorted(intents))}
    slot2id = {label: idx for idx, label in enumerate(sorted(slots))}
    id2intent = {idx: label for label, idx in intent2id.items()}
    id2slot = {idx: label for label, idx in slot2id.items()}
    return LabelMaps(
        intent2id=intent2id,
        id2intent=id2intent,
        slot2id=slot2id,
        id2slot=id2slot,
    )


def compute_word_ids(tokenizer, tokenized, tokens: List[str]) -> List[Optional[int]]:
    try:
        return tokenized.word_ids()  # type: ignore[attr-defined]
    except ValueError:
        return build_word_ids_slow(tokenizer, tokenized, tokens)


def build_word_ids_slow(tokenizer, tokenized, tokens: List[str]) -> List[Optional[int]]:
    input_ids: List[int] = tokenized["input_ids"]
    special_tokens_mask: Optional[List[int]] = tokenized.get("special_tokens_mask")
    pad_token_id = tokenizer.pad_token_id
    all_special_ids = set(tokenizer.all_special_ids)

    # Pre-tokenize each original token to know how many pieces it expands to
    per_token_pieces: List[List[int]] = [
        tokenizer.encode(token, add_special_tokens=False) for token in tokens
    ]

    word_ids: List[Optional[int]] = []
    current_word_idx = -1
    piece_offset = 0
    current_pieces: List[int] = []

    for position, token_id in enumerate(input_ids):
        is_special = False
        if special_tokens_mask is not None and position < len(special_tokens_mask):
            is_special = bool(special_tokens_mask[position])
        if not is_special and (token_id == pad_token_id or token_id in all_special_ids):
            is_special = True

        if is_special:
            word_ids.append(None)
            continue

        if piece_offset == 0:
            current_word_idx += 1
            if current_word_idx >= len(per_token_pieces):
                word_ids.append(None)
                continue
            current_pieces = per_token_pieces[current_word_idx]
            if not current_pieces:
                word_ids.append(None)
                continue

        word_ids.append(current_word_idx)
        piece_offset += 1

        if piece_offset >= len(current_pieces):
            piece_offset = 0

    return word_ids


class IntentSlotDataset(Dataset):
    def __init__(
        self,
        examples: List[Dict[str, Any]],
        tokenizer,
        label_maps: LabelMaps,
        max_length: int = 128,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.label_maps = label_maps
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        example = self.examples[idx]
        tokens, slot_labels = zip(*example["slots_bio"])
        tokenized = self.tokenizer(
            list(tokens),
            is_split_into_words=True,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_attention_mask=True,
            return_tensors=None,
            add_special_tokens=True,
            return_special_tokens_mask=True,
        )
        word_ids = compute_word_ids(self.tokenizer, tokenized, list(tokens))

        aligned_slot_labels: List[int] = []
        slot_ids = [self.label_maps.slot2id[label] for label in slot_labels]
        previous_word_id: Optional[int] = None
        for word_id in word_ids:
            if word_id is None:
                aligned_slot_labels.append(-100)
            elif word_id != previous_word_id:
                aligned_slot_labels.append(slot_ids[word_id])
            else:
                aligned_slot_labels.append(-100)
            previous_word_id = word_id

        intent_id = self.label_maps.intent2id[example["intent"]]

        return {
            "input_ids": torch.tensor(tokenized["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(tokenized["attention_mask"], dtype=torch.long),
            "intent_label": torch.tensor(intent_id, dtype=torch.long),
            "slot_labels": torch.tensor(aligned_slot_labels, dtype=torch.long),
            "word_ids": word_ids,
            "tokens": list(tokens),
            "example_id": example["id"],
        }


def collate_batch(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    input_ids = torch.stack([item["input_ids"] for item in batch])
    attention_mask = torch.stack([item["attention_mask"] for item in batch])
    intent_labels = torch.stack([item["intent_label"] for item in batch])
    slot_labels = torch.stack([item["slot_labels"] for item in batch])
    word_ids = [item["word_ids"] for item in batch]
    tokens = [item["tokens"] for item in batch]
    example_ids = [item["example_id"] for item in batch]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "intent_labels": intent_labels,
        "slot_labels": slot_labels,
        "word_ids": word_ids,
        "tokens": tokens,
        "example_ids": example_ids,
    }

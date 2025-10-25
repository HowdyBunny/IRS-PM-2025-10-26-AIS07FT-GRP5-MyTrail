from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn
from transformers import AutoModel


class JointIntentSlotModel(nn.Module):
    def __init__(
        self,
        encoder_name: str,
        num_intents: int,
        num_slots: int,
        dropout: float = 0.1,
        slot_loss_weight: float = 1.0,
    ) -> None:
        super().__init__()
        self.encoder = AutoModel.from_pretrained(encoder_name)
        hidden_size = self.encoder.config.hidden_size

        self.intent_dropout = nn.Dropout(dropout)
        self.intent_classifier = nn.Linear(hidden_size, num_intents)

        self.slot_dropout = nn.Dropout(dropout)
        self.slot_classifier = nn.Linear(hidden_size, num_slots)

        self.intent_loss_fn = nn.CrossEntropyLoss()
        self.slot_loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
        self.slot_loss_weight = slot_loss_weight

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        intent_labels: Optional[torch.Tensor] = None,
        slot_labels: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        cls_output = sequence_output[:, 0]

        intent_logits = self.intent_classifier(self.intent_dropout(cls_output))
        slot_logits = self.slot_classifier(self.slot_dropout(sequence_output))

        loss = None
        if intent_labels is not None and slot_labels is not None:
            intent_loss = self.intent_loss_fn(intent_logits, intent_labels)
            slot_loss = self.slot_loss_fn(
                slot_logits.view(-1, slot_logits.size(-1)),
                slot_labels.view(-1),
            )
            loss = intent_loss + self.slot_loss_weight * slot_loss

        return {
            "loss": loss,
            "intent_logits": intent_logits,
            "slot_logits": slot_logits,
        }


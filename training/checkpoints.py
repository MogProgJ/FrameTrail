"""The class count of an RF-DETR checkpoint, which rfdetr must be told when it differs from 90.

rfdetr 1.11 configures 90 classes unless told otherwise. It loads a checkpoint with more classes and then cuts the
head back to 90 rows, so every class after the 90th silently disappears (the pilot has 110, the full vocabulary 595).
Building the model with num_classes=head_classes(weights) keeps the whole head.
"""
from __future__ import annotations

from pathlib import Path


def head_classes(weights: Path | str) -> int:
    """Classes in a checkpoint's detection head: its rows minus the extra no-object row."""
    import torch
    checkpoint = torch.load(weights, map_location='cpu', weights_only=False)
    state = checkpoint.get('model')
    if state is None:  # PyTorch Lightning .ckpt
        state = {key.removeprefix('model.'): value for key, value in checkpoint['state_dict'].items()}
    return int(state['class_embed.bias'].shape[0]) - 1

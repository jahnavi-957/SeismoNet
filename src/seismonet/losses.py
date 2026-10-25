"""Segmentation loss for P/S/noise targets — handles missing phases.

Targets are (B, 3, L) continuous Gaussian P/S + clipped remainder noise (labels.make_targets).
Loss is a per-sample, per-channel loss averaged over the window:
- Default: cross-entropy against the Gaussian targets (soft targets) via KL-like form
  L = - sum_c  y_c * log(softmax(logits)_c)  averaged over L (and B).
  This is the correct form when targets are distributions, not hard labels.
- Missing phase: when a P or S Gaussian is all-zero (trace_S_arrival_sample == ""), the
  target mass is entirely in noise — the loss naturally sees no P/S mass there.
  No masking is needed; the same formula works (y_P == 0 → no loss from P there).

Missing-phase handling is therefore "do not fabricate P/S" at the target level (already in
labels.make_targets); the loss does not need to special-case it beyond accepting soft targets.

Alternative hard-label cross_entropy would be wrong here (targets are not one-hot).
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def soft_cross_entropy_loss(
    logits: torch.Tensor,  # (B, 3, L)
    targets: torch.Tensor,  # (B, 3, L) — P/S/noise Gaussian + clipped noise, sum=1 per sample
) -> torch.Tensor:
    if logits.shape != targets.shape:
        raise ValueError(f"logits {tuple(logits.shape)} vs targets {tuple(targets.shape)}")
    if logits.dim() != 3 or logits.shape[1] != 3:
        raise ValueError(f"expected (B,3,L), got {tuple(logits.shape)}")
    # softmax over channels
    log_probs = F.log_softmax(logits, dim=1)  # (B,3,L)
    # -y * log p, sum over channels, mean over batch+length
    loss = -(targets * log_probs).sum(dim=1).mean()
    return loss


def forward_with_loss(
    model,
    waveform: torch.Tensor,
    targets: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return (loss, probabilities) for a batch."""
    logits = model(waveform)
    loss = soft_cross_entropy_loss(logits, targets)
    probs = F.softmax(logits, dim=1)
    return loss, probs

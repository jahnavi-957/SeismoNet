"""Small 1D U-Net for three-component phase picking — P2 Part B.

Input: (B, 3, 3072)  — ENZ counts-normalized windows (SR-001/SR-004, windowing.length=3072, depth=4).
Output: (B, 3, 3072) per-sample P/S/noise probabilities (softmax over dim=1).

Four encoder/decoder levels, skip connections, shape-safe down/up (FR-036/SR-008,
shapes.check_window_depth_compatible). Modest width (base 16) for 4 GiB VRAM.
Model code stays in src/seismonet/model.py — separate from the data pipeline.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv1d(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm1d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv1d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm1d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Down1d(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.pool = nn.MaxPool1d(2)
        self.conv = DoubleConv1d(in_ch, out_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(self.pool(x))


class Up1d(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose1d(in_ch, out_ch, kernel_size=2, stride=2)
        self.conv = DoubleConv1d(in_ch, out_ch)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        # Crop skip if needed (handles odd lengths; for 3072 % 16==0 none needed, but safe)
        if x.shape[2] != skip.shape[2]:
            diff = skip.shape[2] - x.shape[2]
            skip = skip[:, :, diff // 2 : diff // 2 + x.shape[2]]
        x = torch.cat([skip, x], dim=1)
        return self.conv(x)


class SeismoUnet1d(nn.Module):
    """4-level 1D U-Net.  Input 3 ch, output 3 ch logits."""

    def __init__(self, base: int = 16, depth: int = 4) -> None:
        super().__init__()
        if depth != 4:
            raise ValueError(f"this milestone fixes depth=4 (config depth={depth} — match baseline)")
        self.base = base
        self.depth = depth
        self.inc = DoubleConv1d(3, base)
        self.downs = nn.ModuleList(
            [Down1d(base * (2 ** i), base * (2 ** (i + 1))) for i in range(depth)]
        )
        # Ups: mirror of downs
        self.ups = nn.ModuleList(
            [Up1d(base * (2 ** (depth - i)), base * (2 ** (depth - i - 1))) for i in range(depth)]
        )
        self.outc = nn.Conv1d(base, 3, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 3, L) where L % 16 == 0 (3072); fail fast otherwise
        if x.dim() != 3 or x.shape[1] != 3:
            raise ValueError(f"expected (B,3,L), got {tuple(x.shape)}")
        if x.shape[2] % (1 << self.depth) != 0:
            raise ValueError(f"length {x.shape[2]} not divisible by 2**{self.depth} (FR-036)")
        skips = []
        h = self.inc(x)
        skips.append(h)
        for d in self.downs:
            h = d(h)
            skips.append(h)
        # skips: [L, L/2, L/4, L/8, L/16]; last is bottom, not used as skip
        h = skips.pop()  # bottom
        for up in self.ups:
            skip = skips.pop()
            h = up(h, skip)
        logits = self.outc(h)
        return logits

    def probabilities(self, x: torch.Tensor) -> torch.Tensor:
        return F.softmax(self.forward(x), dim=1)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

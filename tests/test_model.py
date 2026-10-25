import torch
import pytest

from seismonet.model import SeismoUnet1d, count_parameters
from seismonet.losses import soft_cross_entropy_loss


def test_model_shape():
    m = SeismoUnet1d()
    x = torch.randn(2, 3, 3072)
    out = m(x)
    assert tuple(out.shape) == (2, 3, 3072)


def test_forward_probabilities():
    m = SeismoUnet1d()
    m.eval()
    x = torch.randn(2, 3, 3072)
    probs = m.probabilities(x)
    assert tuple(probs.shape) == (2, 3, 3072)
    # Per-sample P/S/noise sum to 1
    assert torch.allclose(probs.sum(dim=1), torch.ones(2, 3072), atol=1e-5)

def test_loss_on_synthetic_targets():
    m = SeismoUnet1d()
    x = torch.randn(2, 3, 3072)
    # Synthetic targets: soft Gaussian-like (valid per labels.make_targets contract)
    targets = torch.stack([
        torch.zeros(3072),  # P absent -> all-zero Gaussian, peak would be 0
        torch.zeros(3072),
        torch.ones(3072),
    ]).unsqueeze(0).expand(2, -1, -1).contiguous()
    # But make at least one sample have a real P Gaussian so loss > 0
    # Use a simple Gaussian bump at center for P
    import numpy as np
    L = 3072
    c = L // 2
    sigma = 20.0
    g = np.exp(-0.5 * ((np.arange(L) - c) / sigma) ** 2)
    targets2 = torch.zeros(2, 3, L)
    targets2[:, 0, :] = torch.from_numpy(g)
    targets2[:, 2, :] = torch.clamp(1.0 - targets2[:, 0, :], min=0)
    logits = m(x)
    loss = soft_cross_entropy_loss(logits, targets2)
    assert loss.requires_grad
    assert torch.isfinite(loss).item()

def test_missing_phase_targets():
    # Missing S -> S channel all-zero; loss should still be finite and not NaN
    import numpy as np
    L = 3072
    m = SeismoUnet1d()
    x = torch.randn(1, 3, L)
    # P present, S absent
    g = np.exp(-0.5 * ((np.arange(L) - 1000) / 10.0) ** 2)
    targets = torch.zeros(1, 3, L)
    targets[0, 0, :] = torch.from_numpy(g)
    targets[0, 2, :] = 1.0 - targets[0, 0, :]
    logits = m(x)
    loss = soft_cross_entropy_loss(logits, targets)
    assert torch.isfinite(loss).item()

def test_count_parameters():
    m = SeismoUnet1d(base=16)
    n = count_parameters(m)
    assert n > 10_000  # smallest 1D U-Net is ~100k params
    assert n < 2_000_000

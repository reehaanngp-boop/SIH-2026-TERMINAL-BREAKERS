"""PyTorch port of MesoNet's MesoInception-4 deepfake detector.

MesoNet (Afchar et al., WIFS 2018) is a tiny CNN that classifies a *face crop*
as real (0) or manipulated/deepfake (1). This is a faithful re-implementation of
the Keras ``MesoInception_4`` architecture from the official repo
(https://github.com/DariusAf/MesoNet, Apache-2.0), so the published ``.h5``
checkpoints can be loaded after a one-time weight conversion (see
``scripts/convert_mesonet_weights.py``).

It is a per-frame *image* classifier, not a video model: the deepfake signal for
a video is produced by scoring face crops across sampled frames and aggregating
the per-crop scores (see ``deepfake.py``).

Notes
-----
* Keras stores Conv2D kernels as ``(rows, cols, in_ch, out_ch)``; PyTorch wants
  ``(out_ch, in_ch, rows, cols)``. The conversion script transposes exactly.
* Keras BatchNormalization uses ``epsilon=1e-3``; keep that here so converted
  weights run identically.
* The final layer is a sigmoid trained with mean-squared error against
  ``{0: real, 1: fake}``, so the output is a *score*, not a calibrated
  probability.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from torch import nn


class _InceptionLayer(nn.Module):
    """Keras ``MesoInception4.InceptionLayer(a, b, c, d)``:

    x1 = Conv(1x1, a)
    x2 = Conv(1x1, b) -> Conv(3x3, b)
    x3 = Conv(1x1, c) -> Conv(3x3, c, dilation=2)
    x4 = Conv(1x1, d) -> Conv(3x3, d, dilation=3)
    concat[x1, x2, x3, x4]  (channel-wise)
    """

    def __init__(self, in_ch: int, a: int, b: int, c: int, d: int) -> None:
        super().__init__()
        self.conv1x1_a = nn.Conv2d(in_ch, a, 1, padding=0)
        self.conv1x1_b = nn.Conv2d(in_ch, b, 1, padding=0)
        self.conv3x3_b = nn.Conv2d(b, b, 3, padding=1)
        self.conv1x1_c = nn.Conv2d(in_ch, c, 1, padding=0)
        self.conv3x3_c = nn.Conv2d(c, c, 3, padding=2, dilation=2)  # 'same' for dil=2
        self.conv1x1_d = nn.Conv2d(in_ch, d, 1, padding=0)
        self.conv3x3_d = nn.Conv2d(d, d, 3, padding=3, dilation=3)  # 'same' for dil=3

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Every Keras Conv2D in the inception block has activation='relu'.
        x1 = torch.relu(self.conv1x1_a(x))
        x2 = torch.relu(self.conv3x3_b(torch.relu(self.conv1x1_b(x))))
        x3 = torch.relu(self.conv3x3_c(torch.relu(self.conv1x1_c(x))))
        x4 = torch.relu(self.conv3x3_d(torch.relu(self.conv1x1_d(x))))
        return torch.cat([x1, x2, x3, x4], dim=1)


class MesoInception4(nn.Module):
    """MesoInception-4 deepfake classifier. Input: 256x256x3 RGB face crop."""

    def __init__(self) -> None:
        super().__init__()
        self.incept1 = _InceptionLayer(in_ch=3, a=1, b=4, c=4, d=2)  # -> 11 ch
        self.bn1 = nn.BatchNorm2d(11, eps=1e-3)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)

        self.incept2 = _InceptionLayer(in_ch=11, a=2, b=4, c=4, d=2)  # -> 12 ch
        self.bn2 = nn.BatchNorm2d(12, eps=1e-3)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)

        self.conv3 = nn.Conv2d(12, 16, 5, padding=2)  # 'same'
        self.bn3 = nn.BatchNorm2d(16, eps=1e-3)
        self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2)

        self.conv4 = nn.Conv2d(16, 16, 5, padding=2)  # 'same'
        self.bn4 = nn.BatchNorm2d(16, eps=1e-3)
        self.pool4 = nn.MaxPool2d(kernel_size=4, stride=4)  # 32 -> 8

        self.fc1 = nn.Linear(16 * 8 * 8, 16)
        self.leaky = nn.LeakyReLU(negative_slope=0.1)
        self.fc2 = nn.Linear(16, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool1(self.bn1(self.incept1(x)))
        x = self.pool2(self.bn2(self.incept2(x)))
        x = self.pool3(self.bn3(torch.relu(self.conv3(x))))
        x = self.pool4(self.bn4(torch.relu(self.conv4(x))))
        x = torch.flatten(x, start_dim=1)
        x = self.leaky(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x


def load_mesonet(path: str) -> MesoInception4 | None:
    """Load the converted MesoInception-4 weights. Returns None on any failure."""
    try:
        model = MesoInception4()
        state = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        return model
    except Exception:  # noqa: BLE001
        return None


def score_crop(model: MesoInception4, crop: np.ndarray) -> float:
    """Score one face crop.

    ``crop`` is a HxWx3 RGB array in [0, 1] (already resized 256x256 by the
    caller). Returns the MesoNet sigmoid (0 = real, 1 = manipulated).
    """
    x = torch.from_numpy(np.ascontiguousarray(crop, dtype=np.float32))
    x = x.permute(2, 0, 1).unsqueeze(0)  # HWC -> NCHW
    with torch.no_grad():
        return float(model(x).item())

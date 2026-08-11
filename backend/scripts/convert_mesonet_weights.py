"""Convert MesoNet's Keras ``MesoInception_DF.h5`` to a PyTorch state dict.

The weights are converted with an independent numpy re-implementation of the
same forward pass (scipy.ndimage.correlate == 'same' zero-padded
cross-correlation) so we can prove the Keras->PyTorch axis order and the
arithmetic are correct WITHOUT installing TensorFlow. If the converted model
does not reproduce the numpy reference to ~1e-4, the script exits non-zero.

Source weights (Apache-2.0):
  https://github.com/DariusAf/MesoNet  ->  weights/MesoInception_DF.h5

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\convert_mesonet_weights.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import numpy as np
import h5py  # noqa: E402
import torch  # noqa: E402
from scipy import ndimage  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.detectors.video.mesonet_model import MesoInception4  # noqa: E402

# Ordered model layers -> expected Keras weight shapes.
# Conv2D Keras kernel shape is (rows, cols, in_ch, out_ch).
CONV_ORDER: list[tuple[str, tuple[int, int, int, int]]] = [
    ("incept1.conv1x1_a", (1, 1, 3, 1)),
    ("incept1.conv1x1_b", (1, 1, 3, 4)),
    ("incept1.conv3x3_b", (3, 3, 4, 4)),
    ("incept1.conv1x1_c", (1, 1, 3, 4)),
    ("incept1.conv3x3_c", (3, 3, 4, 4)),
    ("incept1.conv1x1_d", (1, 1, 3, 2)),
    ("incept1.conv3x3_d", (3, 3, 2, 2)),
    ("incept2.conv1x1_a", (1, 1, 11, 2)),
    ("incept2.conv1x1_b", (1, 1, 11, 4)),
    ("incept2.conv3x3_b", (3, 3, 4, 4)),
    ("incept2.conv1x1_c", (1, 1, 11, 4)),
    ("incept2.conv3x3_c", (3, 3, 4, 4)),
    ("incept2.conv1x1_d", (1, 1, 11, 2)),
    ("incept2.conv3x3_d", (3, 3, 2, 2)),
    ("conv3", (5, 5, 12, 16)),
    ("conv4", (5, 5, 16, 16)),
]
BN_ORDER: list[tuple[str, int]] = [
    ("bn1", 11), ("bn2", 12), ("bn3", 16), ("bn4", 16),
]
DENSE_ORDER: list[tuple[str, tuple[int, int]]] = [
    ("fc1", (1024, 16)), ("fc2", (16, 1)),
]

EPS = 1e-3  # Keras BatchNormalization epsilon


# ---------------------------------------------------------------------------
# Numpy reference forward (independent implementation, Keras layout semantics)
# ---------------------------------------------------------------------------

def _dilate(kernel: np.ndarray, dilation: int) -> np.ndarray:
    """Insert zero gaps so scipy's dense correlate matches a dilated conv."""
    if dilation <= 1:
        return kernel
    k = kernel.shape[0]
    n = k + (k - 1) * (dilation - 1)
    out = np.zeros((n, n, kernel.shape[2], kernel.shape[3]), dtype=kernel.dtype)
    out[::dilation, ::dilation] = kernel
    return out


def conv_same(x: np.ndarray, kernel: np.ndarray, bias: np.ndarray, dilation: int = 1) -> np.ndarray:
    """x: (C,H,W); kernel: (rows,cols,Cin,Cout) Keras layout; 'same' zero-pad."""
    kernel = _dilate(kernel, dilation)
    out = np.zeros((kernel.shape[3], x.shape[1], x.shape[2]), dtype=np.float64)
    for cin in range(x.shape[0]):
        for cout in range(kernel.shape[3]):
            out[cout] += ndimage.correlate(
                x[cin], kernel[:, :, cin, cout], mode="constant", cval=0.0
            )
    return out + bias[:, None, None]


def bn_forward(x: np.ndarray, gamma, beta, mean, var) -> np.ndarray:
    return (x - mean[:, None, None]) / np.sqrt(var[:, None, None] + EPS) * gamma[:, None, None] + beta[:, None, None]


def maxpool(x: np.ndarray, k: int) -> np.ndarray:
    c, h, w = x.shape
    return x.reshape(c, h // k, k, w // k, k).max(axis=(2, 4))


def dense_forward(x: np.ndarray, kernel: np.ndarray, bias: np.ndarray) -> np.ndarray:
    """x: (D,); kernel: (in, out) Keras layout."""
    return x @ kernel + bias


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def leaky_relu(x: np.ndarray) -> np.ndarray:
    return np.where(x > 0, x, 0.1 * x)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


DILATION = {  # 3x3 inception branches with dilation (c: 2, d: 3)
    "incept1.conv3x3_c": 2, "incept1.conv3x3_d": 3,
    "incept2.conv3x3_c": 2, "incept2.conv3x3_d": 3,
}


def numpy_forward(img: np.ndarray, sd: dict[str, np.ndarray]) -> np.ndarray:
    """Full MesoInception-4 forward in pure numpy (Keras semantics)."""
    x = img
    def conv(x, name):
        return conv_same(x, sd[name + ".weight"], sd[name + ".bias"], DILATION.get(name, 1))
    def bn(x, name):
        return bn_forward(x, sd[name + ".weight"], sd[name + ".bias"],
                          sd[name + ".running_mean"], sd[name + ".running_var"])

    def incept(x, p):
        x1 = relu(conv(x, p + "conv1x1_a"))
        x2 = relu(conv(relu(conv(x, p + "conv1x1_b")), p + "conv3x3_b"))
        x3 = relu(conv(relu(conv(x, p + "conv1x1_c")), p + "conv3x3_c"))
        x4 = relu(conv(relu(conv(x, p + "conv1x1_d")), p + "conv3x3_d"))
        return np.concatenate([x1, x2, x3, x4], axis=0)

    x = maxpool(bn(incept(x, "incept1."), "bn1"), 2)
    x = maxpool(bn(incept(x, "incept2."), "bn2"), 2)
    x = maxpool(bn(relu(conv(x, "conv3")), "bn3"), 2)
    x = maxpool(bn(relu(conv(x, "conv4")), "bn4"), 4)
    f = x.reshape(-1)
    f = leaky_relu(dense_forward(f, sd["fc1.weight"], sd["fc1.bias"]))
    out = sigmoid(dense_forward(f, sd["fc2.weight"], sd["fc2.bias"]))
    return float(out[0])


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def main() -> None:
    settings = get_settings()
    src = settings.model_dir / "mesonet" / "MesoInception_DF.h5"
    dst = settings.model_dir / "mesonet" / "mesoInception_DF.pth"
    if not src.exists():
        sys.exit(f"Missing source weights: {src}\nDownload from "
                 "https://github.com/DariusAf/MesoNet/blob/master/weights/MesoInception_DF.h5")

    convs: list[tuple[str, np.ndarray, np.ndarray]] = []
    bns: list[tuple[str, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    denses: list[tuple[str, np.ndarray, np.ndarray]] = []

    with h5py.File(src, "r") as f:
        for layer_name in f.attrs["layer_names"]:
            name = layer_name.decode() if isinstance(layer_name, bytes) else layer_name
            grp = f[name]
            wnames = grp.attrs.get("weight_names", [])
            if not len(wnames):
                continue
            weights = {}
            for w in wnames:
                key = str(w.decode() if isinstance(w, bytes) else w)
                ds = f[key] if key in f else grp[key]  # absolute or relative path
                weights[Path(key).name.split(":")[0]] = ds[()]  # 'kernel:0' -> 'kernel'
            if "gamma" in weights:
                bns.append((name, weights["gamma"], weights["beta"],
                            weights["moving_mean"], weights["moving_variance"]))
            elif "kernel" in weights:
                kern, bias = weights["kernel"], weights["bias"]
                if kern.ndim == 4:
                    convs.append((name, kern, bias))
                elif kern.ndim == 2:
                    denses.append((name, kern, bias))

    # Keras 2.1.5 stores ``layer_names`` in a scrambled order, but each layer's
    # numeric suffix is its creation index, and creation order == architectural
    # order. Sort by that suffix so the zips below are deterministic.
    def suffix(item: tuple[str, ...]) -> int:
        digits = "".join(ch for ch in item[0] if ch.isdigit())
        return int(digits or -1)

    convs.sort(key=suffix)
    bns.sort(key=suffix)
    denses.sort(key=suffix)

    if len(convs) != len(CONV_ORDER) or len(bns) != len(BN_ORDER) or len(denses) != len(DENSE_ORDER):
        sys.exit(f"Layer-count mismatch: convs={len(convs)}/{len(CONV_ORDER)}, "
                 f"bn={len(bns)}/{len(BN_ORDER)}, dense={len(denses)}/{len(DENSE_ORDER)}")

    model = MesoInception4()
    sd = {}
    keras_sd: dict[str, np.ndarray] = {}  # Keras-layout arrays for the numpy reference
    for (module, shape), (_, kern, bias) in zip(CONV_ORDER, convs):
        if kern.shape != shape:
            sys.exit(f"Conv {module}: Keras shape {kern.shape} != expected {shape}")
        keras_sd[f"{module}.weight"] = kern.astype(np.float64)  # (rows, cols, in, out)
        keras_sd[f"{module}.bias"] = bias.astype(np.float64)
        # Keras (rows, cols, in, out) -> PyTorch (out, in, rows, cols)
        sd[f"{module}.weight"] = torch.from_numpy(np.transpose(kern, (3, 2, 0, 1)).copy())
        sd[f"{module}.bias"] = torch.from_numpy(bias.copy())
    for (module, ch), (_, gamma, beta, mean, var) in zip(BN_ORDER, bns):
        if len(gamma) != ch:
            sys.exit(f"BN {module}: expected {ch} features, got {len(gamma)}")
        keras_sd[f"{module}.weight"] = gamma.astype(np.float64)
        keras_sd[f"{module}.bias"] = beta.astype(np.float64)
        keras_sd[f"{module}.running_mean"] = mean.astype(np.float64)
        keras_sd[f"{module}.running_var"] = var.astype(np.float64)
        sd[f"{module}.weight"] = torch.from_numpy(gamma.copy())
        sd[f"{module}.bias"] = torch.from_numpy(beta.copy())
        sd[f"{module}.running_mean"] = torch.from_numpy(mean.copy())
        sd[f"{module}.running_var"] = torch.from_numpy(var.copy())
        sd[f"{module}.num_batches_tracked"] = torch.tensor(0, dtype=torch.long)  # unused at inference
    for (module, shape), (_, kern, bias) in zip(DENSE_ORDER, denses):
        if kern.shape != shape:
            sys.exit(f"Dense {module}: Keras shape {kern.shape} != expected {shape}")
        keras_sd[f"{module}.weight"] = kern.astype(np.float64)  # (in, out)
        keras_sd[f"{module}.bias"] = bias.astype(np.float64)
        # Keras (in, out) -> PyTorch (out, in)
        sd[f"{module}.weight"] = torch.from_numpy(np.transpose(kern, (1, 0)).copy())
        sd[f"{module}.bias"] = torch.from_numpy(bias.copy())

    missing = set(model.state_dict()) - set(sd)
    extra = set(sd) - set(model.state_dict())
    if missing or extra:
        sys.exit(f"Key mismatch — missing {sorted(missing)}, extra {sorted(extra)}")
    model.load_state_dict(sd)
    model.eval()

    # ---- Independent numpy validation -------------------------------------------------
    rng = np.random.default_rng(42)
    np_sd = keras_sd
    max_err = 0.0
    for idx in range(3):
        img = rng.random((3, 256, 256)).astype(np.float64) if idx < 2 else np.zeros((3, 256, 256))
        ref = numpy_forward(img, np_sd)
        with torch.no_grad():
            got = float(model(torch.from_numpy(img).unsqueeze(0).float()).item())
        err = abs(ref - got)
        max_err = max(max_err, err)
        print(f"  sample {idx}: numpy={ref:.6f} torch={got:.6f} diff={err:.2e}")
    print(f"  max |numpy - torch| = {max_err:.2e}  (weights {'OK' if max_err < 1e-4 else 'MISMATCH'})")
    if max_err >= 1e-4:
        sys.exit("Validation failed: converted weights do not reproduce the numpy reference.")

    torch.save(sd, dst)
    print(f"Saved {dst} ({dst.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

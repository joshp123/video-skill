# Written by AI on 2026.11.17 by model Claude Opus 5.5.
"""What the model hears at a join: plain signal measures and a frozen speech model's features, from 5 s around it."""
import numpy as np
from sound import SR, normalised

HALF = 2.5                         # seconds of sound each side of the join
LAYERS = [3, 6, 9, 12, 15, 18, 21, 24]
WAVLM = "microsoft/wavlm-large"


def window(x, t):
    """5 s centred on time t (seconds) of x, mirrored at the ends of the file, speech set to -20 dBFS."""
    a, b, n = int(round((t - HALF) * SR)), int(round((t + HALF) * SR)), len(x)
    idx = np.abs(np.arange(a, b))
    idx = np.where(idx >= n, 2 * (n - 1) - idx, idx).clip(0, n - 1)
    return normalised(x[idx])


def _db(x):
    return 10 * np.log10(np.mean(np.asarray(x, np.float64) ** 2) + 1e-12) if len(x) else -120.0


def _logmel(y):
    import torch, torchaudio
    mel = torchaudio.transforms.MelSpectrogram(SR, n_fft=400, hop_length=160, n_mels=40)
    return (10 * torch.log10(mel(torch.from_numpy(y)) + 1e-10)).numpy().T


def _voicing(seg):
    seg = seg - seg.mean()
    if np.sum(seg ** 2) < 1e-8:
        return 0.0
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    return float(np.max(ac[SR // 400: SR // 60]) / ac[0])


def signal(y):
    """About twenty measures of level, clicks, spectral change, room tone and voicing at the join (the window's centre)."""
    n = len(y) // 2
    fr = np.array([_db(y[k:k + 80]) for k in range(0, len(y) - 80, 80)])          # 5 ms frames
    floor, k0 = np.percentile(fr, 10), n // 80
    lvl = lambda a, b: _db(y[max(0, n + int(a * SR)): n + int(b * SR)])
    steps = np.abs([_db(y[k:k + 160]) - _db(y[k - 160:k]) for k in range(160, len(y) - 160, 40)])
    near = np.abs([_db(y[k:k + 160]) - _db(y[k - 160:k]) for k in range(n - 480, n + 480, 40)])
    hp = np.abs(np.diff(y))
    blocks = hp[: len(hp) // 32 * 32].reshape(-1, 32).max(1)
    click = 20 * np.log10(hp[n - 16:n + 16].max() + 1e-9) - 20 * np.log10(np.median(blocks) + 1e-9)
    M = _logmel(y)
    m0 = n // 160
    flux = lambda m: np.mean(np.abs(M[m - 3:m].mean(0) - M[m:m + 3].mean(0)))
    allflux = np.array([flux(m) for m in range(5, len(M) - 5)])
    f0 = flux(m0)
    lvl10 = M.mean(1)
    qL, qR = np.arange(max(0, m0 - 240), m0 - 2), np.arange(m0 + 2, min(len(M), m0 + 240))
    qL, qR = qL[lvl10[qL] <= np.percentile(lvl10[qL], 15)], qR[lvl10[qR] <= np.percentile(lvl10[qR], 15)]
    sp = fr > floor + 15
    spL, spR = fr[:k0][sp[:k0]], fr[k0:][sp[k0:]]
    loud = fr > floor + 12

    def edge_run(side):
        idx = list(range(k0 - 1, -1, -1) if side == "L" else range(k0, len(fr)))
        k = 0
        while k < len(idx) and not loud[idx[k]] and k < 6:
            k += 1
        start = k
        while k < len(idx) and loud[idx[k]]:
            k += 1
        p = k
        while p < len(idx) and not loud[idx[p]]:
            p += 1
        return min((k - start) * 0.005, 1.0), min((p - k) * 0.005, 1.0)

    burstL, pauseL = edge_run("L")
    burstR, pauseR = edge_run("R")
    q = np.concatenate([[0], (~loud).astype(int), [0]])
    d = np.diff(q)
    pause_here = max([(e - s) * 0.005 for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]) if s <= k0 <= e] or [0.0])
    return [lvl(-0.02, 0) - floor, lvl(0, 0.02) - floor, lvl(-0.02, 0), lvl(0, 0.02),
            near.max(), near.max() - np.percentile(steps, 95), click, f0, (allflux < f0).mean(),
            (f0 - np.median(allflux)) / (allflux.std() + 1e-9),
            np.mean(np.abs(M[qL].mean(0) - M[qR].mean(0))), abs(M[qL].mean() - M[qR].mean()),
            abs(np.median(spL) - np.median(spR)) if len(spL) > 10 and len(spR) > 10 else 0.0,
            _voicing(y[n - 480:n]), _voicing(y[n:n + 480]), burstL, pauseL, burstR, pauseR, pause_here, floor]


_model = {}


def speech_model():
    if not _model:
        import torch
        from transformers import AutoFeatureExtractor, WavLMModel
        _model["dev"] = "mps" if torch.backends.mps.is_available() else "cpu"
        _model["fe"] = AutoFeatureExtractor.from_pretrained(WAVLM)
        _model["m"] = WavLMModel.from_pretrained(WAVLM).to(_model["dev"]).eval()
    return _model


def speech(ys, batch=16):
    """For each window: the frame-to-frame jump in every WavLM layer at the join (TRACE), against the window's median,
    and the mean of 8 layers over the join and over 0.44 s either side."""
    import torch
    m = speech_model()
    c, trace, pooled = int(1.5 / 0.02), [], []
    for b in range(0, len(ys), batch):
        segs = [y[len(y) // 2 - int(1.5 * SR): len(y) // 2 + int(1.5 * SR)] for y in ys[b:b + batch]]
        x = m["fe"](segs, sampling_rate=SR, return_tensors="pt").input_values.to(m["dev"])
        with torch.inference_mode():
            H = torch.stack(m["m"](x, output_hidden_states=True).hidden_states, 1).float()
        for hs in H:
            hn = torch.nn.functional.normalize(hs, dim=-1)
            d = 1 - (hn[:, 1:] * hn[:, :-1]).sum(-1)
            trace.append((d[:, c - 4: c + 4].max(1).values - d.median(1).values).cpu().numpy())
            P = hs[LAYERS]
            pooled.append(torch.cat([P[:, c - 3: c + 4].mean(1), P[:, c - 25: c - 3].mean(1), P[:, c + 4: c + 26].mean(1)], -1)
                          .reshape(-1).cpu().numpy().astype(np.float16))
    return np.array(trace, np.float32), np.array(pooled)


def measure(ys):
    """Everything the classifier reads, for a list of 5 s windows."""
    trace, pooled = speech(ys)
    return dict(signal=np.array([signal(y) for y in ys], np.float32), trace=trace, pooled=pooled)

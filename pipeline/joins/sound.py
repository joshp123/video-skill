# Written by AI on 2026.11.17 by model Claude Opus 5.5.
"""Reading sound, its level trace and room floor, its pauses, and joining pieces as Resolve will."""
import subprocess
import numpy as np

SR = 16000
FRAME = 0.01                 # level trace step, seconds
QUIET_DB = 10                # a frame is quiet within this many dB of the room floor
MIN_PAUSE = 0.08             # a pause is at least this long


def read(path, start=None, end=None):
    """Mono float32 at 16 kHz, from any file ffmpeg reads (first channel); optionally one stretch, in seconds."""
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{max(0.0, start):.6f}"]
    if end is not None:
        cmd += ["-t", f"{end - max(0.0, start or 0.0):.6f}"]
    cmd += ["-i", str(path), "-map", "0:a:0", "-af", "pan=mono|c0=c0", "-ar", str(SR), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def levels(x):
    """Level of each 10 ms frame, dB full scale."""
    n = int(FRAME * SR)
    x = x[: len(x) // n * n].astype(np.float64)
    return 10 * np.log10(np.mean(x.reshape(-1, n) ** 2, 1) + 1e-12)


def floor_trace(db, window=20.0):
    """Room floor around each frame: the 5th percentile of the levels within +-window/2 seconds."""
    step = int(1 / FRAME)                       # one value a second, then held
    half = int(window / 2 / FRAME)
    pts = [np.percentile(db[max(0, k - half): k + half + 1], 5) for k in range(0, len(db), step)]
    return np.repeat(pts, step)[: len(db)]


def pauses(db, floor):
    """Every pause, as (start, end) seconds: runs of frames within QUIET_DB of the floor, at least MIN_PAUSE long."""
    quiet = np.concatenate([[False], db < floor + QUIET_DB, [False]]).astype(int)
    d = np.diff(quiet)
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    keep = (ends - starts) * FRAME >= MIN_PAUSE - 1e-9
    return [(s * FRAME, e * FRAME) for s, e in zip(starts[keep], ends[keep])]


def speech_level(x):
    """RMS level of the speech frames (more than 15 dB over the floor), dB full scale."""
    db = levels(x)
    if not len(db):
        return -120.0
    loud = db[db > np.percentile(db, 10) + 15]
    if len(loud) < 20:
        loud = np.sort(db)[-max(1, len(db) // 3):]
    return float(10 * np.log10(np.mean(10 ** (loud / 10))))


def normalised(x):
    """The window with its speech at -20 dBFS RMS, so every measure is relative to this recording's own speech."""
    return x * np.float32(10 ** ((-20 - speech_level(x)) / 20))


def join(pieces, crossfades):
    """Pieces (arrays) joined in order, each join an equal-power crossfade of the given seconds centred on the cut.
    Each piece must carry crossfade/2 of handle at every joined edge. Returns the audio and each join's time."""
    out, times = [], []
    for k, p in enumerate(pieces):
        p = p.astype(np.float32)
        if k:
            h = int(round(crossfades[k - 1] * SR / 2))
            if h:
                t = np.linspace(0, np.pi / 2, 2 * h, dtype=np.float32)
                tail = out[-1][-2 * h:] * np.cos(t) + p[: 2 * h] * np.sin(t)
                out[-1] = out[-1][: -2 * h]
                out.append(tail)
                p = p[2 * h:]
            times.append(sum(len(o) for o in out) / SR - h / SR)
        out.append(p)
    return np.concatenate(out), times

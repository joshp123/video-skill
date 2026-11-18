# Written by AI on 2026.11.17 by model Claude Opus 5.5.
"""Making labelled joins from a recording, and training the join classifier on them.

Every example is a join this code makes itself, so the label is known: clean joins cut inside measured pauses, the way
`place` cuts, and seven kinds of bad join. The words only locate edges; their text is never used."""
import json, re
import numpy as np, soundfile as sf
import sound
from sound import SR
from features import HALF, measure

KINDS = ["clean", "chop_end", "clip_start", "scrap", "click", "room", "connected"]
# A level step between takes is not a kind: a 5 s window cannot tell it from ordinary sentence-to-sentence level, so
# `check` reports the step in dB and the agent decides.
CTX = HALF + 0.1                     # sound kept each side when building, so the window can be shifted
JITTER = 0.025                       # the window centre is up to this far from the true join (a join time a little out)


# ---------- word times good enough to build examples from ----------
def align(audio_path, words, ranges, max_chunk=25.0):
    """Utterances with aligned word times, from a long recording and a rough transcript ([{start, end, word}], seconds).
    The transcript is split where it pauses; each stretch is force-aligned (torchaudio MMS) and kept if the aligner
    is confident. Returns dicts: {id, path, start, dur, words: [{w, s, e, p}]} with word times relative to start."""
    import torch
    from torchaudio.pipelines import MMS_FA as B
    model, tok, aligner = B.get_model().eval(), B.get_tokenizer(), B.get_aligner()
    info = sf.info(audio_path)
    out = []
    for r, (a, b) in enumerate(ranges):
        ws = [dict(w=re.sub(r"[^a-z']", "", w["word"].lower()), s=w["start"], e=w["end"]) for w in words
              if a <= w["start"] < b]
        ws = [w for w in ws if w["w"] and not w["w"].startswith("'")]
        chunks, cur = [], []
        for w in ws:
            if cur and (w["s"] - cur[-1]["e"] > 0.4 or w["e"] - cur[0]["s"] > max_chunk):
                chunks.append(cur); cur = []
            cur.append(w)
        chunks.append(cur)
        for k, ch in enumerate(chunks):
            if len(ch) < 4:
                continue
            s0, s1 = max(0.0, ch[0]["s"] - 1.0), min(info.duration, ch[-1]["e"] + 1.0)
            x, _ = sf.read(audio_path, start=int(s0 * SR), stop=int(s1 * SR), dtype="float32")
            with torch.inference_mode():
                em, _ = model(torch.from_numpy(x)[None])
            try:
                spans = aligner(em[0], tok([w["w"] for w in ch]))
            except Exception:
                continue
            ratio = len(x) / em.shape[1] / SR
            al = [dict(w=w["w"], s=s0 + sp[0].start * ratio, e=s0 + sp[-1].end * ratio,
                       p=float(sum(t.score for t in sp) / len(sp))) for w, sp in zip(ch, spans)]
            if np.mean([w["p"] for w in al]) < 0.5:
                continue
            start = max(0.0, al[0]["s"] - CTX - 0.5)
            dur = min(info.duration, al[-1]["e"] + CTX + 0.5) - start
            out.append(dict(id=f"rec{r}-c{k:04d}", session=f"rec{r}", group=f"rec{r}-b{k // 8}", path=str(audio_path), start=start, dur=dur,
                            words=[dict(w=w["w"], s=w["s"] - start, e=w["e"] - start, p=w["p"]) for w in al]))
    return out


# ---------- labelled joins ----------
class Source:
    """Utterances grouped into sessions (one speaker, one room); joins are made within a session. An utterance's
    `group` keeps related joins in one cross-validation fold (a speaker, or a stretch of one recording)."""

    def __init__(self, utts):
        self.sessions = {}
        for u in utts:
            if len(u["words"]) >= 6:
                self.sessions.setdefault(u.get("session") or "-".join(u["id"].split("-")[:2]), []).append(u)
        self.sessions = list(self.sessions.values())
        self._audio, self._pauses = {}, {}

    def audio(self, u):
        """Speech at -20 dBFS RMS, level trace and room floor (dB)."""
        if u["id"] not in self._audio:
            start = int(u.get("start", 0) * SR)
            x, sr = sf.read(u["path"], start=start, stop=start + int(u["dur"] * SR) if "start" in u else None, dtype="float32")
            if x.ndim > 1:
                x = x[:, 0]
            assert sr == SR, f"{u['path']} must be 16 kHz"
            on = np.zeros(len(x), bool)
            for w in u["words"]:
                on[int(w["s"] * SR):int(w["e"] * SR)] = True
            x = x * (10 ** (-20 / 20) / (np.sqrt(np.mean(x[on] ** 2)) + 1e-9))
            db = sound.levels(x)
            self._audio[u["id"]] = (x, db, float(np.percentile(db, 5)))
            if len(self._audio) > 300:
                self._audio.pop(next(iter(self._audio)))
        return self._audio[u["id"]]

    def pause_after(self, u, i):
        """The longest pause (by level) between word i and the next, as (start, end) seconds, or None."""
        key = u["id"]
        if key not in self._pauses:
            _, db, fl = self.audio(u)
            ps = sound.pauses(db, np.full(len(db), fl))
            w = u["words"]
            res = []
            for k in range(len(w)):
                a, b = w[k]["e"] - 0.03, (w[k + 1]["s"] if k + 1 < len(w) else u["dur"]) + 0.03
                inside = [(max(s, a), min(e, b)) for s, e in ps if e > a and s < b]
                inside = [p for p in inside if p[1] - p[0] >= sound.MIN_PAUSE]
                res.append(max(inside, key=lambda p: p[1] - p[0]) if inside else None)
            self._pauses[key] = res
        return self._pauses[key][i]


def _noise(rng, n):
    x = rng.standard_normal(n).astype(np.float32)
    kind = rng.integers(3)
    if kind == 1:
        x = np.cumsum(x); x -= np.convolve(x, np.ones(801) / 801, "same")
    elif kind == 2:
        f = rng.uniform(300, 4000)
        k = np.sinc(2 * f / SR * np.arange(-200, 201)) * np.hanning(401)
        x = np.convolve(x, k / k.sum(), "same")
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)


def _fade(rng):
    return 0.0 if rng.random() < 0.25 else float(rng.uniform(0.005, 0.04))


def build(src, kind, rng):
    """One labelled join of the given kind: a 5 s window around it, or None if this draw does not fit."""
    sess = src.sessions[rng.integers(len(src.sessions))]
    same = rng.random() < 0.5 or len(sess) < 2
    u1 = sess[rng.integers(len(sess))]
    u2 = u1 if same else sess[rng.integers(len(sess))]
    if not same and u2["id"] == u1["id"]:
        return None
    w1, w2 = u1["words"], u2["words"]
    i = int(rng.integers(2, len(w1) - 1))
    lo = i + 2 if same else 1
    if lo >= len(w2) - 2:
        return None
    j = int(rng.integers(lo, len(w2) - 2))
    fade = _fade(rng)
    pL, pR = src.pause_after(u1, i), src.pause_after(u2, j - 1)

    def in_pause(p, side):              # a cut inside a pause, clear of its edges by half the fade plus 10 ms
        m = fade / 2 + 0.01
        if p is None or p[1] - p[0] < 2 * m:
            return None
        span = min(p[1] - p[0] - 2 * m, 0.35)
        return p[0] + m + rng.uniform(0, span) if side == "L" else p[1] - m - rng.uniform(0, span)

    c1, c2, info = in_pause(pL, "L"), in_pause(pR, "R"), {}
    x1 = src.audio(u1)[0]
    x2 = src.audio(u2)[0]
    if kind in ("clean", "room"):
        pass
    elif kind == "chop_end":
        d = w1[i]["e"] - w1[i]["s"]
        if d < 0.15:
            return None
        info["ms"] = rng.uniform(30, min(150, 600 * d)); c1 = w1[i]["e"] - info["ms"] / 1000
    elif kind == "clip_start":
        d = w2[j]["e"] - w2[j]["s"]
        if d < 0.15:
            return None
        info["ms"] = rng.uniform(20, min(120, 600 * d)); c2 = w2[j]["s"] + info["ms"] / 1000
    elif kind == "scrap":
        if rng.random() < 0.5:          # the start of the removed next word is left on the outgoing side
            nxt = w1[i + 1]; d = nxt["e"] - nxt["s"]
            if d < 0.06:
                return None
            info.update(ms=rng.uniform(40, min(150, 1000 * d)), side="out"); c1 = nxt["s"] + info["ms"] / 1000
        else:                           # the tail of the removed previous word is left on the incoming side
            prv = w2[j - 1]; d = prv["e"] - prv["s"]
            if d < 0.06:
                return None
            info.update(ms=rng.uniform(40, min(150, 1000 * d)), side="in"); c2 = prv["e"] - info["ms"] / 1000
    elif kind == "click":               # a butt join on a loud sample at a word edge
        fade = 0.0
        out = rng.random() < 0.5
        x, at = (x1, w1[i]["e"]) if out else (x2, w2[j]["s"])
        a, b = (int((at - 0.03) * SR), int((at + 0.005) * SR)) if out else (int((at - 0.005) * SR), int((at + 0.03) * SR))
        seg = np.abs(x[max(0, a):b])
        if not len(seg) or seg.max() < 0.03:
            return None
        if out:
            c1 = (a + int(np.argmax(seg))) / SR; c2 = c2 if c2 is not None else in_pause(pR, "R")
        else:
            c2 = (a + int(np.argmax(seg))) / SR
    elif kind == "connected":           # both cuts at word boundaries with no pause
        gL, gR = w1[i + 1]["s"] - w1[i]["e"], w2[j]["s"] - w2[j - 1]["e"]
        if pL is not None or pR is not None or gL > 0.06 or gR > 0.06:
            return None
        c1, c2 = w1[i]["e"] + max(gL, 0) / 2, w2[j]["s"] - max(gR, 0) / 2
    if c1 is None or c2 is None:
        return None

    x1, x2 = x1.copy(), x2.copy()
    if kind == "room":
        side = rng.random() < 0.5; up = rng.uniform(8, 20); info.update(side="out" if side else "in", db=up)
        xs, fl = (x1, src.audio(u1)[2]) if side else (x2, src.audio(u2)[2])
        xs += _noise(rng, len(xs)) * max(10 ** ((fl + up) / 20), 10 ** (-58 / 20))

    h, n = int(round(fade * SR / 2)), int(CTX * SR)
    a1, b1 = int(round(c1 * SR)), int(round(c2 * SR))
    if a1 - n < 0 or b1 + n > len(x2) or a1 + h > len(x1) or b1 - h < 0:
        return None
    y, _ = sound.join([x1[a1 - n: a1 + h], x2[b1 - h: b1 + n]], [fade])
    step = 0.0
    if kind in ("clean", "room"):
        # the room tone a listener hears switch at the cut: the pause each side, up to 120 ms of it, clear of the fade
        lv = lambda x, a, b: float(np.median(sound.levels(x[int(a * SR): int(b * SR)])))
        if c1 - 0.01 - max(pL[0], c1 - 0.12) < 0.02 or min(pR[1], c2 + 0.12) - c2 - 0.01 < 0.02:
            return None
        step = abs(lv(x1, max(pL[0], c1 - 0.12), c1 - 0.01) - lv(x2, c2 + 0.01, min(pR[1], c2 + 0.12)))
        if kind == "room" and step < 6:
            return None
        if kind == "clean" and step >= 6:      # two stretches whose room tone differs this much make a room jump
            kind, info = "room", dict(natural=True, db=step)
        elif kind == "clean" and step >= 4:     # too close to call
            return None
    shift = int(rng.uniform(-JITTER, JITTER) * SR)
    centre = n + shift
    y = sound.normalised(y[centre - int(HALF * SR): centre + int(HALF * SR)])
    return dict(kind=kind, y=y, fade=fade, same=bool(same), shift_ms=shift / SR * 1000, u1=u1["id"], u2=u2["id"],
                cut_out=u1.get("start", 0) + c1, cut_in=u2.get("start", 0) + c2, room_step_db=float(step),
                group=u1.get("group") or u1["id"].split("-")[0], **info)


def examples(utts, n_clean, n_fault, seed=0, out=None):
    """Labelled joins from utterances, measured. Saves features and labels to out (.npz) and returns them."""
    rng, src, joins = np.random.default_rng(seed), Source(utts), []
    for kind in KINDS:
        n, got, tries = (n_clean if kind == "clean" else n_fault), 0, 0
        while got < n and tries < n * 500:
            tries += 1
            j = build(src, kind, rng)
            if j is not None:
                joins.append(j); got += 1
        print(f"{kind}: {got} joins ({tries} draws)", flush=True)
    f = measure([j.pop("y") for j in joins])
    if out:
        np.savez(out, meta=json.dumps(joins), **f)
    return joins, f


# ---------- the classifier ----------
def _gbm():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0)


def _probe():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.01, max_iter=2000))


def load(paths):
    """Concatenated features and labels from example files."""
    meta, parts = [], {"signal": [], "trace": [], "pooled": []}
    for p in paths:
        d = np.load(p, allow_pickle=True)
        m = json.loads(str(d["meta"]))
        keep = np.array([x["kind"] in KINDS for x in m])          # older files may hold kinds no longer trained
        meta += [x for x, k in zip(m, keep) if k]
        for k in parts:
            parts[k].append(d[k][keep])
    f = {k: np.concatenate(v) for k, v in parts.items()}
    f["y"] = np.array([KINDS.index(m["kind"]) for m in meta])
    f["group"] = np.array([m["group"] for m in meta])
    return meta, f


def _stack(f, probe_p):
    return np.column_stack([f["signal"], f["trace"], probe_p])


def oof(f, folds=5):
    """Out-of-fold class probabilities on the training joins, folds split by speaker or stretch of recording."""
    from sklearn.model_selection import GroupKFold
    y, g, X = f["y"], f["group"], f["pooled"].astype(np.float32)
    pp = np.zeros((len(y), len(KINDS)))
    for a, b in GroupKFold(folds).split(X, y, g):
        pp[b] = _probe().fit(X[a], y[a]).predict_proba(X[b])
    S = _stack(f, pp)
    out = np.zeros_like(pp)
    for a, b in GroupKFold(folds).split(S, y, g):
        out[b] = _gbm().fit(S[a], y[a]).predict_proba(S[b])
    return pp, out


def fit(train_paths, calibrate_paths, budgets=(0.01, 0.02, 0.05, 0.1, 0.2)):
    """Train on every example file; set the flag thresholds so each budget is the share of clean joins flagged in the
    calibration files (out of fold), which should be the target voice and microphone."""
    meta, f = load(train_paths)
    pp, out = oof(f)
    probe = _probe().fit(f["pooled"].astype(np.float32), f["y"])
    gbm = _gbm().fit(_stack(f, pp), f["y"])
    cal = np.zeros(len(meta), bool)
    cal_ids = {m["u1"] for p in calibrate_paths for m in json.loads(str(np.load(p, allow_pickle=True)["meta"]))}
    cal = np.array([m["u1"] in cal_ids for m in meta]) & (f["y"] == 0)
    clean_scores = 1 - out[cal, 0]
    thresholds = {f"{b:g}": float(np.quantile(clean_scores, 1 - b)) for b in budgets}
    return dict(probe=probe, gbm=gbm, kinds=KINDS, thresholds=thresholds,
                trained=__import__("datetime").datetime.now().isoformat(timespec="minutes"),
                trained_on=[str(p) for p in train_paths], calibrated_on=[str(p) for p in calibrate_paths],
                n_train=len(meta), n_calibration_clean=int(cal.sum()))


def predict(model, f):
    """Class probabilities for measured windows."""
    pp = model["probe"].predict_proba(f["pooled"].astype(np.float32))
    return model["gbm"].predict_proba(_stack(f, pp))

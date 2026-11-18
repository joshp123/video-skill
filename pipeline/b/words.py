"""When each known word starts and ends on the lav: forced alignment of the transcript's words, for assemble.py.

Written by AI on 2026-11-18 by Claude Opus 5.5, for the rebuild, from measurements on Josh's lav (codex-switch,
private/research/2026-11-17/rebuild-tooling.md, addendum).

The verbatim transcript's word times run early in connected speech, by 120 to 490 ms on ten words October's editor
measured by hand, while after a pause they are within about 30 ms. Forced alignment of the same words fixes connected
speech, within 65 ms on eight of the ten, but marks a word after a pause 35 to 50 ms late. So:
- times: torchaudio's MMS forced aligner (MMS_FA) on each window of the lav, with every transcript word in the window;
- a word that follows a pause starts at the onset after a pause nearest its aligned start, from 300 ms before (and after
  the word before) to 150 ms after, an onset as qc.py's gate defines it (the level settles an onset after a pause;
  nothing settles one inside speech); the transcript's fillers ([UM]) go to the aligner as sound that is no word;
- confidence: wav2vec2 large LV-60k (LibriSpeech, WAV2VEC2_ASR_LARGE_LV60K_960H) aligns the same words, and a word's
  confidence is its mean letter probability. A word under 0.15, or not settled by the level and with the two
  aligners' starts more than 0.1 s apart, is listed as doubtful with both times: not to be trusted without a look.

words.py LAV TRANSCRIPT WINDOWS.json OUT.json
WINDOWS.json: [[from_s, to_s], ...] on the lav's clock, each with the transcript's words inside it; or
[{"window": [from_s, to_s], "words": [transcript words]}, ...] for an exact piece and exactly its words. OUT.json: per
window, every word with letters, {"word", "transcript_start", "start", "end", "score", "snapped"}, and "doubtful" words.
Runs in pipeline/joins' environment, which has torch and torchaudio and both models offline (about 3 s to load, under
a second a window after that); assemble.py calls it.
"""
import json
import re
import subprocess
import sys

import numpy as np
import torch
import torchaudio

SR = 16000
HOP = 0.005
PAUSE_S = 0.1
SNAP_BEFORE_S, SNAP_AFTER_S = 0.3, 0.15
DOUBT_SCORE, DOUBT_DISAGREE_S = 0.15, 0.1
FILLER = "*"  # MMS_FA's token for sound that is no word: the transcript's [UM], [throatclearing]


def said(word):
    return "".join(re.sub(r"[^a-z']", " ", word.lower().replace("-", " ").replace("’", "'")).split())


def align(bundle, model, audio, texts, upper):
    labels = bundle.get_dict(star=FILLER) if not upper else {c: i for i, c in enumerate(bundle.get_labels())}
    tokens = [[labels[c.upper() if upper else c] for c in t if (c.upper() if upper else c) in labels] for t in texts]
    with torch.inference_mode():
        emission, _ = model(torch.from_numpy(audio.copy())[None])
        emission = torch.log_softmax(emission, -1)
    flat = [t for tk in tokens for t in tk]
    aligned, scores = torchaudio.functional.forced_align(emission, torch.tensor([flat]), blank=0)
    spans = torchaudio.functional.merge_tokens(aligned[0], scores[0].exp())
    ratio = len(audio) / SR / emission.shape[1]
    out, i = [], 0
    for tk in tokens:
        part = spans[i:i + len(tk)]
        i += len(tk)
        out.append((part[0].start * ratio, part[-1].end * ratio, float(np.mean([s.score for s in part]))) if part else None)
    return out


def level(audio):
    """The level every 5 ms over 10 ms windows, in dB, as qc.py measures a render."""
    hop, width = int(HOP * SR), int(0.01 * SR)
    n = max(0, (len(audio) - width) // hop)
    frames = np.lib.stride_tricks.sliding_window_view(audio, width)[::hop][:n]
    return 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)


def onsets_after_pauses(db):
    """qc.py's onsets after a pause (a rise of 10 dB within 80 ms out of a 30 ms dip, reaching speech, after 100 ms under
    the pause level), in seconds. qc.py's levels are absolute on a render at -14 LUFS; the lav is quieter, so here they
    are set from the window's loud speech, as far under it as qc.py's are under a render's (speech 20 dB, pause 23 dB)."""
    loud = np.percentile(db, 95)
    speech, pause_level = loud - 20, loud - 23
    dip, peak, pause = 6, 16, int(PAUSE_S / HOP)
    found, last = [], -1.0
    for k in range(max(dip, pause), len(db) - peak):
        floor, top = db[k - dip:k].max(), db[k:k + peak].max()
        if db[k] < floor + 3 or top < floor + 10 or top < speech:
            continue
        if k * HOP - last > 0.06 and db[k - pause:k].max() < pause_level:
            found.append(k * HOP)
        last = k * HOP
    return found


def onset_near(onsets, at, earliest):
    """The onset after a pause nearest AT, from SNAP_BEFORE_S before (not before EARLIEST) to SNAP_AFTER_S after."""
    near = [t for t in onsets if max(at - SNAP_BEFORE_S, earliest) <= t <= at + SNAP_AFTER_S]
    return min(near, key=lambda t: abs(t - at)) if near else None


def main(lav, transcript, windows_file, out_file):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", lav, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    every = json.load(open(transcript))["words"]
    times = torchaudio.pipelines.MMS_FA
    confidence = torchaudio.pipelines.WAV2VEC2_ASR_LARGE_LV60K_960H
    times_model, confidence_model = times.get_model().eval(), confidence.get_model().eval()
    result = []
    for window in json.load(open(windows_file)):
        if isinstance(window, dict):  # an exact piece of the lav and exactly the words in it
            (a, b), inside = window["window"], window["words"]
        else:
            a, b = window
            inside = [w for w in every if a <= w["start"] and w["end"] <= b]
        spoken = [w for w in inside if not w["word"].startswith("[") and said(w["word"])]
        audio = x[int(a * SR):int(b * SR)]
        placed = align(times, times_model, audio, [FILLER if w["word"].startswith("[") else said(w["word"]) for w in inside
                                                  if w["word"].startswith("[") or said(w["word"])], upper=False)
        placed = [p for w, p in zip([w for w in inside if w["word"].startswith("[") or said(w["word"])], placed)
                  if not w["word"].startswith("[")]
        checked = align(confidence, confidence_model, audio, [said(w["word"]) for w in spoken], upper=True)
        onsets = onsets_after_pauses(level(audio))
        rows, doubtful, previous_end = [], [], 0.0
        for w, p, c in zip(spoken, placed, checked):
            if p is None:
                continue
            start, end = p[0], p[1]
            rise = onset_near(onsets, start, previous_end) if start - previous_end >= PAUSE_S else None
            if rise is not None:
                start = rise
            row = {"word": w["word"], "transcript_start": w["start"], "aligned_start": round(a + p[0], 4), "start": round(a + start, 4), "end": round(a + max(end, start + HOP), 4),
                   "score": round(c[2], 3) if c else 0.0, "snapped": rise is not None}
            if not c or c[2] < DOUBT_SCORE or (rise is None and abs(c[0] - p[0]) > DOUBT_DISAGREE_S):
                doubtful.append({**row, "confidence_aligner_start": round(a + c[0], 4) if c else None})
            rows.append(row)
            previous_end = max(previous_end, end)
        result.append({"window": [a, b], "words": rows, "doubtful": doubtful})
    json.dump(result, open(out_file, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])

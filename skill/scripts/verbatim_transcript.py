"""Verbatim word-timed transcript for placing cuts: CrisperWhisper 2.0 medium.

Written by AI on 2026.10.14 by model claude-opus-5.5, from the 12 Oct 2026 Codex run
(Media/Edits/2026-10-12-camera-session/scripts/transcribe_session.py), with the inputs as arguments.
Device argument and devenv added by AI on 2026-10-22 by Claude Opus 5.5, fault pass after the
codex-switch test.

Keeps ums ([UM], [UH]), restarts and cut-off words, timed to the word. About 5 to 6 minutes
for 23 minutes of audio on Josh's M4 with --device mps (the default; 24 s of audio in 10 s
through the devenv on 22 Oct); --device cpu runs in float32 at about real time (24 s in 23 s)
and writes no compiled-shader cache. It uses the CrisperWhisper code vendored
on 12 Oct (MIT; the model weights carry a separate non-commercial research licence); set
CRISPERWHISPER_VENDOR if it moves. Apply the camera offset here only if the audio isn't
already padded onto the front camera's clock, never both.

usage: verbatim_transcript.py AUDIO_16K_MONO.wav OUT_BASENAME [OFFSET_SECONDS] [--device mps|cpu]
       OFFSET_SECONDS is added to every time, e.g. to put lav times on the front camera's clock.
run, from this folder, in its devenv (devenv.nix beside this file: Python 3.13 and uv; the model
is read offline from the SSD; leave TMPDIR alone, a temp path with spaces breaks devenv):
       devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
         --with numpy --with soundfile --with soxr \
         python -B -I verbatim_transcript.py lav16k.wav transcript/lav_verbatim 36.737
Writes OUT.json ({"words": [{"start", "end", "word"}]}) and OUT.txt (one timed line per phrase).
"""
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict

sys.path.insert(0, os.environ.get("CRISPERWHISPER_VENDOR",
                "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session/scripts/vendor"))
from crisperwhisper import CrisperWhisperModel  # noqa: E402

parser = argparse.ArgumentParser(description="Verbatim word-timed transcript (CrisperWhisper 2.0 medium).")
parser.add_argument("audio_path")
parser.add_argument("out_base")
parser.add_argument("offset", nargs="?", type=float, default=0.0)
parser.add_argument("--device", choices=["mps", "cpu"], default="mps")
arguments = parser.parse_args()
audio_path, out_base, offset = arguments.audio_path, arguments.out_base, arguments.offset
logging.basicConfig(level=logging.WARNING)

began = time.time()
model = CrisperWhisperModel("medium", backend="transformers", device=arguments.device,
                            compute_type="float16" if arguments.device == "mps" else "float32")
result = model.transcribe(audio_path, language="en", mode="verbatim", word_timestamps=True)
data = asdict(result)
words = [{"start": round(w["start"] + offset, 3), "end": round(w["end"] + offset, 3), "word": w["word"].strip()}
         for w in data.get("words") or [] if w.get("start") is not None]

mmss = lambda t: f"{int(t // 60):02d}:{t % 60:04.1f}"
lines, current, line_start, previous_end = [], [], None, None
for w in words:
    if current and (w["start"] - previous_end > 0.7 or len(current) >= 25):
        lines.append(f"{mmss(line_start)}  {' '.join(current)}")
        current = []
    if not current:
        line_start = w["start"]
    current.append(w["word"])
    previous_end = w["end"]
if current:
    lines.append(f"{mmss(line_start)}  {' '.join(current)}")

json.dump({"audio": audio_path, "model": "nyralabs/CrisperWhisper2.0_medium", "mode": "verbatim",
           "offset_seconds": offset, "words": words}, open(out_base + ".json", "w"), indent=1)
open(out_base + ".txt", "w").write("\n".join(lines) + "\n")
print(f"{len(words)} words, {len(lines)} lines, {time.time() - began:.0f} s -> {out_base}.txt")

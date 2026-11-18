#!/bin/sh
# Written by AI on 2026.11.18 by model Claude Opus 5.5. Runs every path an agent uses, on Josh's lav, and fails loudly.
# Covers: place with --words; a start estimate 0.4 s early ("Let" at 368.34, spoken at about 368.75); an edge set by hand
# (start_at) with --words; an edge with no pause next to it ("here" runs into "You"); check from the lav; check from a
# rendered-style file (AAC in .mp4, -14 LUFS). Needs the media drive. Takes about a minute.
set -eu
here="$(cd "$(dirname "$0")/.." && pwd)"
S="/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session"
LAV="$S/audio/dji_0597_aligned_to_nikon_48k_stereo.wav"; WORDS="$S/transcript/lav-verbatim-front.json"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
"$here/joins" place "$LAV" "$here/example/codex-switch-168-259.json" --words "$WORDS" --out "$tmp/a.json"
"$here/joins" place "$LAV" "$here/example/edge-cases.json" --words "$WORDS" --out "$tmp/b.json"
"$here/joins" check --lav "$LAV" "$tmp/a.json" --out "$tmp/c.json"
ffmpeg -v error -ss 168 -t 30 -i "$LAV" -af loudnorm=I=-14 -c:a aac "$tmp/r.mp4"
span="$("$here/.devenv/state/venv/bin/python" -c "import json,sys; print(json.load(open(sys.argv[1]))['check']['calibration_span'])" "$tmp/a.json")"
"$here/joins" check --audio "$tmp/r.mp4" --at 5,12.5 --lav "$LAV" --span "$span" --out "$tmp/d.json"
"$here/.devenv/state/venv/bin/python" - "$tmp" <<'PY'
import json, sys
t = sys.argv[1]
a, b, c, d = (json.load(open(f"{t}/{n}.json")) for n in "abcd")
assert len(a["check"]["joins"]) == 9 and a["check"]["model"]["sha256"]
print("codex-switch 168-259 s: flagged joins", a["check"]["flagged"], "| scores", [j["score"] for j in a["check"]["joins"]])
p2, p3 = b["pieces"][1], b["pieces"][2]
assert p2["start_edge"]["status"] == "pause", p2["start_edge"]
assert p3["start_edge"]["status"] == "given" and "words" in p3
print("late estimate:", p2["start_edge"]["estimate_off_by"], "s off; piece holds:", p2["words"])
print("hand-set edge:", p3["start_edge"], "| piece 2 end:", p2["end_edge"]["status"])
sa, sc = [j["score"] for j in a["check"]["joins"]], [j["score"] for j in c["joins"]]
assert max(abs(x - y) for x, y in zip(sa, sc)) <= 0.01, f"check --lav disagrees with place: {sa} {sc}"
assert len(d["joins"]) == 2 and d["model"] == c["model"] and d["threshold"] == c["threshold"] == a["check"]["threshold"], (d["threshold"], c["threshold"])
print("flag set from:", c["threshold_from"])
print("smoke: all paths ran")
PY

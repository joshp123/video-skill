#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
LAV="/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session/audio/dji_0597_aligned_to_nikon_48k_stereo.wav"
WORDS="/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session/transcript/lav-verbatim-front.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$HERE/joins" place "$LAV" "$HERE/example/codex-switch-168-259.json" --words "$WORDS" --out "$TMP/placed.json"
"$HERE/joins" seams --audio "$LAV" --at 176.9,182.26 --out "$TMP/seams" --json-out "$TMP/seams.json"
test -f "$TMP/seams/all-seams.wav"
echo "smoke: all paths ran"

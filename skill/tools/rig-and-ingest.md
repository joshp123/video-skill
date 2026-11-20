# Rig, ingest, transcription, and graphics

## Camera and audio rig

Check `~/code/gear/camera-gear/inventory.md` when gear changes; establish actual session settings from the files themselves and record them in `Edits/<session>/inventory.md`.

| Role | Device | Format & quirks |
| --- | --- | --- |
| Front (main, master clock) | Nikon Z f | 3840×2160, 10-bit H.265 `.MOV`, N-Log, auto white balance, fast lens (natural shallow DOF). ExifTool reads lens/picture control via nix store: `"$(ls -d /nix/store/*-Image-ExifTool-*/bin/exiftool \| sort -t- -k5 -V \| tail -1)"`. |
| Wide | DJI Osmo Pocket 4 | 3840×2160, 10-bit H.265 `.MP4`, D-Log, auto white balance, 20 mm f/2 (everything sharp). Confirm D-Log visually (flat contrast). |
| Dialogue (lav) | DJI Mic Mini | Recorded into the Pocket's `.MP4` stereo AAC track (identical channels). Wireless radio feed is delayed against the Pocket's own picture; cameras' room mics are for sync only. |
| Screen | Cap (`/Applications/Cap.app`, `cap` CLI/MCP) or macOS (`Cmd-Shift-5`) | Cap records raw local 4K/60fps + cursor data: use single-window Focus Mode for isolated app windows, or full-display / area capture for multi-window flows (e.g. `agent-keyring` popups). macOS screen recordings are variable frame rate. |

- **Tags lie:** both Nikon and DJI tag log footage as BT.709; `ffprobe` cannot detect log.
- **Clocks lie:** never sync by timecode or file creation times (they can differ by seconds to hours).
- **SD cards:** Nikon mounts at `/Volumes/NIKON Z F  ` (two trailing spaces, `DCIM/`); Pocket at `Osmo SD 1TB` (`DCIM/DJI_001/`, ignore `.LRF` proxies). Always quote paths and never erase cards.

## Sync, ingest, and face touches

`pipeline/b/ingest.py start` copies/hashes files, cross-correlates the lav against the Nikon's mic at 5 points (padding the lav onto the front camera's clock; apply speed correction only if drift > half a frame), finds clean room tone (verified high-passed at 1 kHz and 4 kHz), starts the verbatim transcript, runs face-touch scans (`skill/scripts/face_touch.swift`, Apple Vision) on both cameras, and creates the Resolve project.

- **Settle wide picture offset by eye** when ingest's head-motion windows disagree by > 20 ms: check the clap transient and late-take bilabials ("p"/"b"/"m") against the lav. Record offsets once (`front_time = clip_time + picture_offset_s`; padded lav has offset `0`).
- **Face touches:** read both cameras' scan logs together and open flagged frames at full size; cut or cover every moment a hand touches his face.
- **Screen recordings:** sync to the front clock on two widely separated events (screen glow on face, key clicks on lav). Conform variable-fps macOS recordings before editing, trimming inside the filter so `-ss` never drops the opening frame:
  ```sh
  ffmpeg -i SCREEN.mov -vf "fps=25,trim=start=S:end=E,setpts=PTS-STARTPTS" -c:v prores_ks -profile:v 3 OUT.mov
  ```

## Verbatim transcription and forced alignment

Resolve's built-in transcription drops ums, stutters, and cut-off words (`(...)`), so ingest runs CrisperWhisper (`skill/scripts/verbatim_transcript.py`) on the padded lav (~5–6 min for 23 min on GPU):

```sh
# Manual re-run (inside skill/scripts/, leave TMPDIR unset):
devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
  --with numpy --with soundfile --with soxr \
  python -B -I verbatim_transcript.py LAV_16K.wav EDIT/transcript/NAME OFFSET_S [--device cpu]
```

- **Check the raw transcript:** inspect any gap > 10 s and check the final timestamp against audio length (CrisperWhisper can loop on long silences and drop untimed words). Re-transcribe missed stretches on their own.
- **Fix proper nouns** (e.g. "Kodux" → "Codex") in a working copy from the tool's README while keeping original times.
- **Exact timing comes from audio, not ASR:** `pipeline/joins/joins place` cuts edges inside measured room-tone pauses; `pipeline/b/words.py` (torchaudio MMS + wav2vec2 forced alignment) times caption words and anchors on each placed piece.

## Audio listening & dialogue seams

- Place cuts inside measured pauses (`joins place`) with 40 ms constant-power crossfades (`Cross Fade +3 dB`) on build, or a plain butt join when `edit.py cut` removes time inside a shot.
- If a filler ("um") runs into the next word with no pause, prefer keeping it (tightening the pause before it) or test an 80 ms fade-in over room tone.
- **Direct listening:** `report.py` extracts 4 s WAV clips around every join (`seams/join-NN-*.wav` and `seams/all-seams.wav`). Listen directly with `read_file` on a native-audio Gemini model (Gemini 4 Neon, or delegated via T3 `delegate_task` if driving from Claude/Codex) to verify clean starts/ends, room tone, pitch/prosody, and no doubled breaths. Never claim audio is clean without listening (or listing unverified non-pause seams for Josh).

## Graphics: Fusion templates + Remotion terminals

- **Native Fusion templates first** (`looks/2026-10-16-signpost-pill/` + `pipeline/b/templates/`): `Signpost Opening`, `Signpost Title`, `Signpost Highlight` (orange outline around app pixels), `Signpost Photo`, and `Signpost Closing`. Edit words/regions via `edit.py title` (takes `[[highlighted]]` syntax). Rebuild templates only when the look itself changes (`pipeline/b/make_templates.py`).
- **Remotion (`pipeline/graphics/`)** is the standing exception for per-frame text animations: `Terminal.tsx`, `AskTerminal.tsx` (agent prompt box, hide captions underneath), and `Keyline.tsx`. Capture real PTY output at the exact panel column width:
  ```sh
  PAGER=cat python3 pipeline/graphics/capture-terminal.py --columns N --output EDIT/graphics/content/NAME.txt -- /abs/path/to/tool ARGS
  ```
  Render transparent ProRes 4444 clips via `pipeline/b/render-graphics.mjs` using Remotion's bundled headless shell (never installed Chrome). Verify pill padding and edges over mid-grey and on the graded timeline.
- **Look evolution:** keep all style tokens (sizes, colours, motion, caption face clearance) in `looks/<name>/look.json` and its `README.md`, never hardcoded per video.

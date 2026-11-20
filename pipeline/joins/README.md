# joins: deterministic pause placement and seam audio extraction

Two deterministic commands for dialogue cuts (all editorial judgement stays with the model and direct listening):

- **`place`**: places each kept piece's start and end inside a measured room-tone pause of the lav (from rough transcript times), and reports `level_step_db`, `room_step_db`, and any edge that has no pause next to it (`needs_listen`).
- **`seams`**: extracts a 4-second WAV clip around each dialogue join time (plus a concatenated `all-seams.wav`) so a native-audio model (Gemini) or Josh can listen directly to every seam.

This folder's devenv also provides `torch` and `torchaudio` for `pipeline/b/words.py` (forced word alignment for captions).

## Usage

```sh
pipeline/joins/joins place LAV.wav PIECES.json [--words TRANSCRIPT.json] [--crossfade 0.04] [--out placed.json]
pipeline/joins/joins seams --audio RENDER.mp4 --joins join-times.json --out seams/ [--window 4.0]
```

Setup once per machine: `cd pipeline/joins && devenv shell -- true`.

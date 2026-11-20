# The pipeline

A video is built once from a plan onto one DaVinci Resolve timeline, then edited in place. From build onward, the Resolve timeline is the single source of truth.

Run Resolve commands with `/usr/bin/python3 -B` from `pipeline/b/` (they start Resolve `-nogui` and configure scripting env vars automatically). Run `ingest.py` from `pipeline/`'s devenv (`cd pipeline && devenv shell -- python3 b/ingest.py ...`). Every command prints JSON. Keep all caches and renders on the SSD (`session.CACHE`, `Media/Resolve Cache`).

## Core commands

| Step | Command | Purpose |
| --- | --- | --- |
| Resolve daemon | `b/session.py start \| stop \| status` | Start/stop windowless Resolve (`-nogui`) with cross-Space modal dialog detection |
| Ingest | `b/ingest.py start --session DIR --video DIR --source ...` | Copy/hash media, sync lav, transcribe verbatim (CrisperWhisper), scan face touches, write `plan.json` header, create project |
| Ingest status | `b/ingest.py status --session DIR [--wait S]` | Poll detached ingest and list `needs_the_model` |
| New video from session | `b/ingest.py header --video DIR --slug NAME (--like PLAN \| --session DIR)` | Reuse an already-ingested session |
| Project setup | `b/project.py PLAN.json` | Create DWG/Intermediate Rec.709 1080×1920 project, colour groups, source bin, input log spaces |
| Measure plan | `b/assemble.py PLAN.json --out edit-list.json --force` | Resolve word anchors, place cuts in measured pauses (`joins place`), force-align caption words (`words.py`), check caption widths and highlight spans (~10–20 s, no Resolve) |
| Build first cut | `b/build.py PLAN.json --timeline NAME` | Lay V1–V5 + A1–A2 + titles, run one `.drt` pass for per-word captions and 40 ms constant-power crossfades, grade, apply wide blur + cache flags, read back and diff |
| Edit in place | `b/edit.py PLAN.json --timeline NAME CMD ...` | Multi-track timeline edits: `cut`, `insert`, `split`, `camera`, `title`, `still`, `captions`, `tidy` (0.5–4 s) |
| Read back | `b/readback.py PLAN.json --timeline NAME [--describe]` | Dump live timeline items, grades, and caption word timings |
| Render | `b/render.py PLAN.json --timeline NAME --out FILE [--preset phone\|post\|master\|still\|sound] [--range IN OUT] [--loudness PRESET\|off] [--wait-for-cache]` | Render from Resolve's render cache (~30–45 s for 90 s short) |
| Loudness preset | `b/loudness.py --target -12 --ceiling -1` | Write/find Optimize-to-Standard preset (~-14.5 LUFS / -1.2 dBTP) |
| Physics & seams check | `b/report.py PLAN.json --timeline NAME --render FILE` | Measure loudness/true-peak (`ebur128`), detect black/offline frames, extract 4 s seam WAVs (`joins seams`) for direct listening (~2–3 s) |
| Audio helper | `joins/joins place` / `joins/joins seams` | Deterministic room-floor pause placement and seam WAV extraction |

## Timeline layout

| Track | Contents |
| --- | --- |
| `V1` Background | Solid look background (`color=c=0x171717` ProRes) |
| `V2` Main camera | Reference/front camera for the entire film (stays underneath V3) |
| `V3` Second camera | Wide camera only where shown, with look blur + render cache |
| `V4` App | Screen recordings, stills, and Remotion terminal clips |
| `V5` Titles | Look Fusion title/highlight/photo/closing templates |
| `V6+` | Overlays added later (`edit.py still`) |
| `A1` / `A2` | Lav dialogue (sample-exact edges) / room tone under gaps |
| `Subtitle 1` | Look caption template with per-word highlight timings |

## Direct Resolve MCP edits (preferred for single-item changes)

Blackmagic's `davinci-resolve` MCP connects to the same windowless Resolve:

- **Inspect visually:** `get_thumbnails` (grid across cuts/layouts), `get_image` (full-res graded frames, no captions), `describe_grade` (CDLs and colour management). Render `render.py --preset still --range F F` to see burned-in captions.
- **Single-item edits (`run_script` / `run_script_unsafe`):** framing (`item.SetProperties`), grade (`item.SetCDL`), move/trim graphics (`SetPosition`/`SetLeftOffset`/`SetRightOffset`), audio edges (`SetLeftOffset(..., True)`, `SetFades`), or call `edit.py` functions directly via `run_script_unsafe`.

## `b/edit.py` commands

- `cut AT FRAMES`: removes `FRAMES` across all tracks (butt join on the newly cut dialogue seam so removed speech never bleeds back).
- `insert AT FRAMES`: opens `FRAMES` of empty film across all tracks with room tone.
- `split AT [--tracks ...]`: splits camera clips at `AT` without moving time.
- `camera START END CAMERA [--framing JSON]`: switches angle via V3 clip (with neighbour framing, grade, and blur) or clears V3 for front camera.
- `title AT JSON [--frames N]`: updates Fusion title inputs in place (supports `[[pill]]` syntax).
- `still FILE START FRAMES`: places a still on a new top video track.
- `captions JSON`: updates caption text/word timings via `.drt` (invalidates render cache; batch caption edits together).
- `tidy`: deletes superseded timelines (keeps current + `"look background blur"`) and unused media, and reports the render cache folder to trash after quitting Resolve.

## Supporting modules

- `b/timeline_file.py`, `subtitles/write_caption_track.py`, `b/captions.py`: `.drt` export/rewrite/import for per-word captions and sub-frame crossfades.
- `b/words.py`: torchaudio MMS + wav2vec2 forced alignment (runs in `pipeline/joins/.devenv/state/venv/bin/python`).
- `b/sound.py`, `b/graphic.py`, `b/resolve_windows.swift`: audio placement, Fusion title helpers, cross-Space dialog guard.
- `b/make_templates.py`, `b/template_kinds.py`, `b/templates/`, `resolve/build_graphics.py`: rebuilds the look's `.setting` Fusion templates when look tokens change.
- `b/render-graphics.mjs`, `graphics/`: Remotion 4 project (`Terminal.tsx`, `AskTerminal.tsx`, `Keyline.tsx`) and `capture-terminal.py`.

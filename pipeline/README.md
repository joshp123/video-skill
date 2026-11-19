<!-- Written by AI on 2026.11.19 by model claude opus 5.5, for DaVinci Resolve Studio 21.2 on Josh's MacBook (M4 Pro, 24 GB) and Mac mini. Every time below was measured on the codex-switch footage (two 3840 by 2160 cameras at 25 fps, the lav, a 91 s vertical short); the evidence is private/research/2026-11-17/rebuild-tooling.md, "Addendum, 19 Nov". -->

# The pipeline

A video is cut once and then changed in place. The first cut is built from the model's plan into one Resolve timeline. From then on that timeline is the only copy of the cut: a note is a change to it, made with Resolve's own scripting calls, then one render. Nothing is rebuilt and nothing outside the timeline is kept in step with it.

| Step | Tool | Time on codex-switch |
| --- | --- | --- |
| Footage to a checked session and the plan's header | `b/ingest.py` | 5 min 40 s |
| The plan's Resolve project | `b/project.py` | 14 s |
| The first cut, graded and blurred | `b/build.py` | 27 s |
| Resolve fills its render cache, in the background | (Resolve) | 4 min |
| A note | Resolve calls, or `b/edit.py` | 0.6 to 4 s |
| The film, from the cache | `b/render.py` | 31 s; 46 s after five notes, at load 36 to 60 |
| The checks, as one list | `b/report.py` | 46 s |

Times scale with the machine's other load: say the load average beside any time you report. Run the commands with `/usr/bin/python3 -B` from `pipeline/b` (they start Resolve windowless and set its scripting variables themselves). Every command prints JSON. Paths in a plan are relative to its folder. Caches and renders go on the media drive (`session.CACHE`, `Media/Resolve Cache`); nothing large goes on the internal disk.

## Resolve: windowless, one at a time

Every command calls `session.connect(project)`. If Resolve is not running it is started with `-nogui`: no window, nothing takes the foreground. `session.py start | stop | status`.

- **Dialogs.** A windowless Resolve still raises modal dialogs, on Josh's screen. `SaveProject()` while the unnamed "Untitled Project" is open raises one and never returns. So the tools never save the unnamed project and never close a project, and they stop with the dialog's title if one appears. Nothing may call Resolve until it is cancelled. Do not use the MCP's `launch_resolve`: start Resolve with `session.py start`.
- **One video job per Mac.** A render blocks every other call until it ends. Resolve grows to 10 GB or more on blurred footage; restart it (`session.py stop`) between heavy stages if the Mac swaps.
- **"Align audio edits to frame boundaries"** must be off (it is), or the sub-frame sound calls round to whole frames while returning True.

## The Resolve MCP

Blackmagic's MCP server (`davinci-resolve`) talks to the same windowless Resolve.
- `get_image` and `get_thumbnails` show the model graded frames of the timeline without moving the playhead: use them to look at a cut. They do not draw the caption track; render a still for that (`render.py --preset still --range F F`).
- `run_script` runs a short script in a sandbox with no files (up to 60 s); `run_script_unsafe` has files, so it can use these tools:
  ```python
  import sys; sys.path.insert(0, "/Users/josh/code/video-skill/pipeline/b"); import edit
  result = edit.cut(resolve, project, "codex-switch", at=578, frames=10, plan_path=".../plan.json")
  ```
- `search_scripting_api` and `get_scripting_docs` hold the API for 21.2. Read them before saying Resolve cannot do something.

## The timeline

| Track | What |
| --- | --- |
| V1 Background | the look's background |
| V2 Main camera | the plan's `reference` camera, the whole film, under the second camera too |
| V3 Second camera | only where the film shows it, with the look's background blur |
| V4 App | screen recordings, stills and rendered graphics |
| V5 Titles | the look's Fusion templates as title items |
| V6 and up | anything laid over everything later (a still) |
| A1 Dialogue, A2 Room tone | pieces of the lav, every edge exact to the sample |
| Captions | the subtitle track in the look's caption template, each word lit as it is said |

The two cameras are plain clips, synced by the plan's `picture_offset_s` (front-camera time = this camera's time + offset). Josh switches a shot by hand by disabling or trimming the V3 clip. There is no multicam clip and no second "finish" timeline: the grade, the blur and the render cache live on the timeline that is edited. The project holds this timeline and "look background blur", the carrier the blur is copied from.

## `b/ingest.py`

`start --session DIR --video DIR --source PATH ...`, then `status --session DIR [--wait S]`. Run it with the pipeline devenv's Python (`cd pipeline && devenv shell -- python3 b/ingest.py ...`). It copies the cards, hashes every file, finds the lav's offset on the front camera's clock by cross-correlation, pads the lav onto that clock, transcribes it word for word, finds room tone, scans both cameras for face touches, writes the plan's header (`plan.json`, nothing editorial) and runs `project.py`. `needs_the_model` lists what only the model can settle: the wide camera's log profile, each camera's picture against its sound, names in the transcript, the screen recording's offset and private detail, the face touches.

**The wide camera's picture offset is not measured well enough to trust to a frame**: on 12 October its windows fell 80 ms apart. When they disagree by over 20 ms the header carries the lav's offset and the model settles the picture offset by eye (the clap, his lips).

`ingest.py header --video DIR --slug NAME (--like PLAN | --session DIR)` starts another video from a session already ingested.

## `b/project.py PLAN.json`

Makes the plan's project: colour management (DaVinci YRGB Color Managed, Wide Gamut / Intermediate, Rec.709 Gamma 2.4 out), 1080 by 1920 at the plan's rate, project media and render cache on the media drive, one colour group per camera, the cameras and the lav in a Source bin with each camera's input colour space. A project that already holds timelines is refused.

## `b/build.py PLAN.json --timeline NAME`

Builds the first cut once. `assemble.py` turns the plan into `edit-list.json` (its help gives the plan's format): it finds the kept words, has `joins/joins place` put every sound edge inside a measured pause and score every join, aligns every word to the lav for the captions and anchors, and converts everything to timeline frames. Then the timeline above, in this order: picture, titles, sound, **one pass through the timeline's file** (each crossfade's sub-frame geometry and the captions with their word times), then the grade, the blur and the render cache. The file pass comes first because an imported timeline has no render cache. The timeline is read back and compared with the edit list; `differences` lists every mismatch. `assemble`'s report lists what needs a look: edges with no pause, flagged joins, doubtful word times, words heard but not chosen.

To measure a plan without Resolve (its length, every edge with no pause, every flagged join), run `assemble.py PLAN.json --out edit-list.json --force` alone: about 20 s, plus 20 to 50 s the first time a lav stretch is calibrated. The 27 s build above reused run 6's calibration. A camera's grade lives in the plan's `cameras` (`grade`, `group`): `build.py` and `edit.py camera` read it there when no clip of that camera is on the timeline to copy from.

The edit list is the build's input only. After the build, read the cut from the timeline (`readback.py`), never from the list.

## Changing the cut

**Most notes are one or two calls**; do them directly, through the MCP or a script:

| Note | Calls |
| --- | --- |
| a shot's framing | `item.SetProperties({"ZoomX": ..., "Pan": ...})` |
| a picture over a span | `edit.still` (below), or `AppendToTimeline` then trim: a still is laid at its default length whatever `endFrame` says |
| a graphic moved or trimmed | `item.SetPosition`, `SetLeftOffset`, `SetRightOffset` |
| a title's words | `edit.title`: a styled text takes its `[[ ]]` pill through `LoadSettings`, which no single call does |
| a sound edge | `SetLeftOffset(x, True)`, `SetRightOffset(x, True)`, `SetPosition({...}, True, True)`: sub-frame |
| a camera's grade | `SetCDL` on node 1 of each of its clips |

**`b/edit.py`** does the edits that must treat every track together, each in one call, from a shell (`edit.py PLAN.json --timeline NAME COMMAND ...`) or the MCP. Each returns `changes` (every item added, removed or changed, read before and after) and `notes`; check both.

| Command | What it does | Time |
| --- | --- | --- |
| `cut AT FRAMES` | takes FRAMES out from AT on every track: camera clips and sound running across are cut in two, the second part starting later in its source; titles and pictures running across are shortened; everything after moves up | 0.8 s |
| `insert AT FRAMES` | opens FRAMES of empty film at AT: the same, the other way, with room tone under the gap | 0.6 s (test clips only) |
| `split AT` | cuts the camera clips under AT in two, no change in time | 0.5 s (test clips only) |
| `camera START END CAMERA` | shows CAMERA from START to END: the second camera as a V3 clip with its neighbour's framing, grade and blur; the main camera by clearing V3 | 0.6 s |
| `title AT JSON` | sets inputs of the title under AT | 0.6 s |
| `still FILE START FRAMES` | a picture over everything on a new top track | 1.2 s |
| `captions JSON` | retypes or re-times captions, through the timeline's file | 3.9 s, then 4 min 46 s of cache refill |
| `tidy` | deletes every other timeline but the blur carrier, and media nothing uses | 0.1 s |

Taking frames out of one shot leaves a jump cut in the picture: cover it with `camera` across the cut, or a panel.

What Resolve's API cannot do, and what each tool does about it (21.2, tested 17 to 19 Nov):
- **No blade.** A cut across a clip is a trim plus a new clip of the same media, given the original's attributes, grade and cache flags.
- **`MoveItems` moves one track at a time**; transitions are left out of the move.
- **Crossfades.** `AddTransition` makes whole frames; a two-frame one centres on a sub-frame edit, a one-frame one does not. Trimming a clip's end removes or drags its crossfade. So `cut` puts a two-frame (80 ms) crossfade back at a join it disturbed, where the build made 40 ms through the file, and says so; the report's join check scores it.
- **Captions.** No call creates a caption or sets its text or word times. `MoveItems` moves a caption with its words lit at the right frames. A caption cannot be trimmed. So retyping a caption, or a `cut` or `insert` across one, writes the caption track through the timeline's file (`timeline_file.py`), and the timeline is replaced by its import.
- **Titles** cannot be lengthened, nor shortened past their first five seconds, by any offset call: `cut` and `insert` lay a title running across again at its new length, with its inputs.

**The render cache.** The look's blur costs about 0.4 s a frame live. `build.py` flags each blur node for Resolve's render cache and sets the project's cache to "user"; Resolve fills it in the background while it is idle (codex-switch: 1.34 GB in about 4 minutes at load 5). Renders then read the cache (`render.py`). Trims and moves keep it; a new clip (a split's second part, a camera switch) is worked out live at the next render, about 0.4 s a frame. **A timeline imported from its file has no cache**: after a `captions` command, or a `cut` across a caption, Resolve fills it again (4 min 46 s on codex-switch); a render before then works the blurred frames out live. Deleting a timeline deletes its cache.

## `b/render.py PLAN.json --timeline NAME --out FILE [--preset phone|post|master|still|sound] [--range IN OUT] [--loudness PRESET] [--wait-for-cache]`

Renders the timeline from the render cache and waits. `phone`: H.264 sized to 28 MB, the file Josh watches; `post`: 8 Mbit/s for X; `master`: ProRes 422 HQ; `still`: one 16-bit PNG of a one-frame range; `sound`: the mix as WAV. Captions are burnt in. `--loudness` loads a preset that normalises loudness (`loudness.py` writes one: "B loudness -12 LUFS -1 dBTP ..." gives about -14.5 LUFS). Normalisation sticks to the project once used, so `--loudness off` loads a preset with it off. `--wait-for-cache` first waits until the cache folder stops growing.

Only a render preset's file can make a render use cached frames, so every render saves its settings as the preset "pipeline from cache", exports it, sets `UseRenderCachedImagesForRecording`, and imports it back (about a second). After a loudness-preset render Resolve refuses to start the next job until it is made again; `session.start_render` does that.

## `b/report.py PLAN.json --timeline NAME --render FILE`

The checks on the finished cut, as one list; nothing stops. It reads the timeline back in the edit list's shape (`readback.py --describe`), renders the mix and runs `joins/joins check` on every dialogue join (with the calibration span the build used), and runs `qc.py` on the render: eyes at cuts, flashes, lip sync, loudness, captions read back from the picture, lit words against his voice, caption edges, colour against the reference camera, text size at phone width, his whole head. The model judges every row; Josh never sees the list.

## Other parts

- `b/readback.py PLAN.json --timeline NAME [--describe]`: what a timeline holds, item by item, with every caption's word times.
- `b/timeline_file.py`: the one export, rewrite and import for crossfade geometry and captions, with every item checked before and after.
- `b/sound.py`, `b/captions.py`, `b/graphic.py`, `b/words.py`, `b/head.py`, `b/qc.py`, `b/qc_vision.swift`, `b/loudness.py`: libraries of the above.
- `joins/`: places sound edges and checks joins; its README says how and what it misses.
- `b/make_templates.py`, `b/template_kinds.py`, `b/templates/`, `resolve/build_graphics.py`: the look's Fusion templates.
- `b/render-graphics.mjs`, `graphics/`: terminal graphics drawn in Remotion, placed as panels.
- `b/word_times.py`: Resolve's own transcription of a timeline, for `qc.py --heard-words`.
- `subtitles/write_caption_track.py`: the caption track's file format.

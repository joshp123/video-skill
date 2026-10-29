<!-- Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J): the edit list of skill B, to the timeline layout in video-skills-redesign/2026-10-21-fable/poc/hillclimb/layout-design.md. `cameras` and `segments` revised for the cut and finish timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. `multicam` and the `cameras` fields `file` and `reference` made to match the code by Claude Opus 5.5 (hill-climb stream I) the same day. `cameras` field `picture_offset_s` added by Claude Opus 5.5 on 2026-10-29, for `qc.py`'s lip sync. The older format below it is unchanged. -->

# The edit list: `edit-list.json`

One file per video, in the video's folder, holds every editorial decision as rows in the Resolve timeline's own terms. The model writes every value; nothing in it is decided by code. `pipeline/b/place.py` builds the cut timeline from it exactly, `pipeline/b/finish.py` makes that cut's finish timeline (flattened, graded) from the cut and the list, and `pipeline/b/readback.py` reads either back into the same shape, so a difference between list and timeline is a fault. Every row may carry `why`, a few words for the next reader; code never reads it. Frames are the timeline's frames from 0; seconds are on the front camera's clock unless a field says otherwise.

## Top level

| Key | What it holds |
| --- | --- |
| `resolve_project` | The Resolve project the timeline is built in. |
| `fps`, `format` | The timeline's rate and its `width` and `height`. |
| `look` | The name of the look in `Media/Edits/looks/`. |
| `duration_frames` | The timeline's length. |
| `multicam` | The name of the cameras' multicam clip in the media pool (ingest makes it as `cameras`). |
| `cameras` | Per camera, by a name the list chooses (`front`, `wide`): `file`, the camera's file, which is how `place.py` finds its angle in the multicam (it reads each angle's file and sync offset from the multicam itself; ingest also writes them to `inventory.md`); `grade` (an ASC CDL: `slope`, `offset` and `power` as `[r, g, b]`, and `saturation`) and `group` (the name of the camera's colour group), which `finish.py` applies to the clips that show that camera on the finish timeline (the cut timeline carries no grade); and `reference: true` on the camera the others are matched to, which `qc.py` measures colour against. The colourist's. `picture_offset_s`: front-camera time = this camera's time + offset, for its picture, as ingest established it picture against picture and wrote it to `inventory.md` (`tools/cameras.md`, "Sync"); 0 on the front camera. `qc.py` times lip sync by it; a camera without it is timed by its own microphone, which for the Pocket is the lav's radio feed, 30 to 60 ms behind its picture. |
| `segments` | V2: the multicam, cut; plain clips of the same cameras on the finish timeline. |
| `panels` | Plain clips: the look's background on V1 and the app on V3. |
| `titles` | V4: the look's Fusion templates as title items. |
| `audio`, `sound` | A1: the dialogue pieces; A2: the room tone. |
| `captions` | ST1. |

## Rows

- **`segments`:** `{camera, source_in, record, frames, framing, speed_percent?, retime?}`. `camera` names one of `cameras`. `source_in` is a frame of that camera's own file; `place.py` adds the angle's offset, so switching a segment's camera means a new `source_in` for the same moment. `framing` is the shot's whole framing on its camera (`ZoomX`, `ZoomY`, `Pan`, `Tilt`: standard, a punch-in, under a panel), set on the segment on the cut timeline and again on its clip by `finish.py`, because flattening resets it; the two cameras need different values for the same shot, so a camera switch changes it too. `speed_percent` under 100 holds or slows the shot; `retime` is Resolve's retime process for it: `nearest`, `optical`, `frame blend` or `project`.
- **`panels`:** `{file, source_in, source_out, track, record, framing, group}`, with `speed_percent` and `retime` as for segments: `track` is 1 for the background and 3 for a screen-recording crop, a still or a rendered Remotion clip; `group` is its colour group. Screen material takes no grade.
- **`titles`:** `{template, inputs, record, frames}`; the track is always V4. `template` names one of the look's Fusion templates; `inputs` are its published inputs, the text's pill ranges included (`[[ ]]` round the words on the pill).
- **`audio`:** `{file, source_in_s, source_out_s, record_s, fade_in_ms, fade_out_ms, crossfade_ms?}`, in seconds, with optional `pre_roll_s`, `patches`, `voice_isolation` (0 to 100) and `dialogue_leveler` (true or false) as before. `crossfade_ms` on a row means the join into the next piece is a crossfade of that length, centred on the cut, which plays half its length of source beyond the cut on both sides; without it the join is a butt join with the two clip fades. A piece before a gap has no crossfade.
- **`sound`:** `{lav, room_tone_s, room_tone_crossfade_ms, room_tone_end_fade_ms}`: the lav file the pieces come from, the room-tone window `[from, to]` in its seconds, the crossfade between loops of the window under a long gap, and the fade at the end.
- **`captions`:** `{text, start, end, words}`: the caption as it reads, with `\n` at its line break; its start and end in seconds; each word as `{text, start, end}`. `captions.py` makes them whole frames for the look's template.

---

<!-- Older format: Resolve, graphics and caption fault fixes written by AI on 2026-10-22 by GPT-6. -->
<!-- Cut and word-timing faults updated by AI on 2026-10-22 by GPT-6 Astra. -->
<!-- Written by AI on 2026-10-21 by Claude Fable 5.1, replacing the 16 Oct version (Claude Opus 5.5) after the pipeline cleanup of the same day. The contract a director writes to. -->

# The older edit data: `edit/edit.json`

The format the older pipeline (`pipeline/cut/`, `pipeline/audio/`, `pipeline/resolve/build_graphics.py`) and the skill installed on 21 Oct write to. Skill B does not use it.

One file per video holds every editorial decision. Everything else (the cut list, the dialogue, the word timing, the graphics, the Resolve timeline) is generated from it. A change of mind is written here and applied to the timeline in place wherever Resolve's scripting allows (a whole line removed, the media behind a clip swapped, a graphic's words changed, a shot reframed); only a change to the structure (words added, lines reordered, a shot recut) rebuilds the timeline from this file. The story editor owns it until Josh decides the script; the editor owns it after that; the mixer owns the dialogue fields. The director says who writes it when, and it never has two writers at once. Generated files never write back into it.

Times are seconds on the front camera's clock. A transcript token holding multiple words is split into separate words sharing its original start and end; write corrections that way too. Words are found by their text in the transcript, so nothing here depends on a time someone typed by hand. Any field the code does not read holds the reason: put reasons in `why` and its kin, never in a field the code reads.

## Top level

| Key | What it holds |
| --- | --- |
| `video`, `cut` | The edit folder's slug, and which cut this is (`short`, later `long`). |
| `format` | `width`, `height`, `fps`. |
| `look` | The name of the look module in `Media/Edits/looks/`. |
| `lead_in_s` | Optional, default 0. Film time before the first line's first word; everything starts that much later. An opening graphic anchors to the first word with a negative `offset_s` and must cover the lead-in, because no camera is placed there. |
| `resolve_project` | The Resolve project the timeline is built in. The builder refuses any other open project. |
| `media` | Paths, relative to the edit folder. `transcript`: the word-timed verbatim transcript. `lav`: `file`, `offset_s`, `room_tone_s` (a quiet window, `[from, to]`, looped under every gap), `silence_dbfs` (30 ms cut-edge silence, default -46) and `pause_dbfs` (10 ms pause search ceiling, default -40, capped at `silence_dbfs` so a quiet word onset is not taken as pause); set them from the room. `cameras.<name>`: `file`, `offset_s`, `camera`, `log` (Resolve's own name for the input colour space, such as `"Nikon N-Log"` or `"DJI D-Gamut/D-Log"`), `colour_group` (the Resolve colour group the camera's clips are assigned to), `grade` (the camera's primaries as an ASC CDL: `slope`, `offset`, `power` as `[r, g, b]` and `saturation`; 1.0, 0.0, 1.0 and 1.0 mean no change; decided by the colourist on real frames, applied to every clip of the camera by the timeline builder and by `pipeline/resolve/grade_cameras.py`; no LUT), `framing` (`zoom`, `pan`, `tilt`, optional `eye_y` (defaults to half the frame height, including for screen recordings): the full-frame framing, decided on real frames). `face_touch`: the scans, per camera. `tool`: the tool being demonstrated. Front-camera time = a file's own time + its `offset_s`. |
| `spelling` | Pairs of transcript text and how it is written on screen (`"L.A. X"` → `"LAX"`). Applied to captions and the words the agent box types, never to the script page (which quotes him exactly) and never to matching. With the same number of words on both sides each word is replaced in place and keeps its timing; with different counts the matched words become one word; an empty replacement removes the word. |
| `lines` | Josh's words, in the order the viewer hears them. |
| `layouts` | Named regions of the frame. |
| `graphics` | Everything drawn over or instead of the picture. |
| `dialogue_patches`, `dialogue_inserts` | The mixer's repairs, on the source clock (below). |

## A line

```json
{
  "id": "point",
  "words": [
    { "from": "So the point is", "to": "So the point is", "near_s": 1187 },
    { "from": "we have all these super intelligent AIs", "to": "apps like Apple Photos.", "near_s": 1189 }
  ],
  "shots": [
    { "from": "So", "camera": "wide", "why": "..." },
    { "from": "we", "camera": "front", "zoom": 1.15, "why": "..." }
  ],
  "cut_points": [ { "before": "we", "in_s": 1188.95, "why": "..." } ],
  "pause_after_s": 0.75,
  "subtitles": ["So the point is", ["we have all these", "super intelligent AIs"]]
}
```

- `words`: one or more runs of his speech, each from its first words to its last, nearest `near_s`. Inside a run, fillers (`[UM]`, `[UH]`), cut-off words (ending in `-`) and pauses longer than `max_pause_s` are taken out; the cut list reports each one, and `keep` lists any token to keep anyway.
- `shots`: the camera from a word onwards, until the next shot. A shot starts at the first occurrence of its word among the line's kept words, or the `n`th (from 0). `zoom` is a punch-in on the camera's framing. `panel_framing` names one of the panel layout's `framings` for this shot when it sits under a panel layout (without it, the framing named like the camera). Every shot says `why`. Cameras anchor to words, never to clip positions, so taking a word out changes nothing else.
- `cut_points`: exact in or out points found by ear or on a spectral trace, where the transcript's times are off or words run together. `before` a word sets the in-point of the clip that starts with it; `after` a word sets the out-point of the clip that ends with it; the `n`th occurrence as for shots.
- `pause_after_s`: the silence after the line, default 0.25 s. The cut list takes it from real silence either side of the join; when the source has less, the missing time is added as film time, the outgoing picture runs on over it, and the report says so (`pause_shortfalls`, with `supplied`).
- `picture_offset_frames` on a shot: a split edit. The picture changes that many frames after (positive) or before (negative) the sound join; sound is unchanged; graphic edges snapped to that cut move with it.
- `audio_preroll_s`: the sound starts that much before the picture (a J-cut), to keep the breath that begins a thought.
- `retime`: corrected start and end times for transcript tokens the recogniser placed wrongly, measured on the lav. Compare run edges and words beside gaps over 0.45 s with Resolve’s times; measure and correct disagreements over 0.3 s before building.
- `max_pause_s`: the longest pause kept inside the line, default 0.45 s.
- `subtitles`: the captions for this line, in order, exactly as they are to read: a string is one caption of one line; a list of two strings is one caption of two lines. One phrase per caption, inside the look's safe width including the active-word pill padding (820 px centred at 1080 px below this look's button column), broken where his phrasing breaks, never mid-phrase. The phrasing is the editor's judgement; `pipeline/subtitles/build_captions.py` times captions and words from the cut list and writes captions JSON. It snaps edges within two frames of visible picture changes, closes blanks shorter than three frames, holds each caption at least 0.7 s (extending or joining a neighbour), and joins a one-word remainder to its neighbour. Each word lights until the next starts, the last until the caption ends with at least three frames; starts at most one second apart prevent Resolve page splits. Named width warnings include the look's pill padding, or a stated 36 px per side fallback; the editor resolves long rows rather than the builder changing wording or look type size.

## What the cut builder does with a line, exactly

The model chooses the words. The code then places the sound cut around them by measuring the lav, and takes out what the data says is taken out by default. Every operation below is in `pipeline/cut/build_cutlist.py`; none chooses what is said.

| Operation | Rule in code | The data can | Reported as |
| --- | --- | --- | --- |
| Find each run of words | the `from` phrase nearest `near_s` (within 90 s), through the `to` phrase after it | `retime` a token the recogniser placed wrongly | `unresolved_anchors` |
| Take out fillers and cut-off words | any token starting `[` or ending `-` | `keep` any token | `removed_words` |
| Take out a long pause inside a run | a gap between two kept words longer than `max_pause_s` (default 0.45 s) splits the run | set `max_pause_s` on the line | `removed_pauses` |
| Place the in and out of each run in silence | from the word's transcript edge, step 5 ms at a time outwards until a 30 ms window measures below `media.lav.silence_dbfs`, bounded by the neighbouring word; the last word of the film needs 80 ms below it | `cut_points` set an exact `in_s` or `out_s` | `boundary_warnings` if the 30 ms after an out-point rises over 10 dB above the edge, or the final 80 ms search fails |
| When no silence exists between two words | take the quietest 10 ms point within 0.2 s | `cut_points` | `boundary_warnings`, with the level |
| Hold a pause between lines | `pause_after_s` (default 0.25 s) taken from real silence either side of the join, in 10 ms steps below the lower of `media.lav.pause_dbfs` and `media.lav.silence_dbfs`; what the source cannot supply is added as film time | set `pause_after_s` on the line | `pause_shortfalls`, with `supplied`, only when film frames are added; `pause_warnings` for a pause edge over 6 dB above the room |
| Place a graphic's edge | an `in` or `out` within 8 frames of a picture cut moves onto the cut | anchor to the word at the cut, or to a word further away | `graphic_snaps` |
| Flag a jump cut | the same camera continues across removed time with his face on screen | change the camera, the layout or the words | `jump_cuts` |
| Flag a face touch | a kept clip contains a flagged moment from the scans | cut round it, or keep it | `face_touches` |

On the first video (21 runs, 42 edges, 281 words): 32 edges were placed in measured silence by the rule, 3 fell back to the quietest point and were flagged, and the director set 7 by hand with `cut_points`; 3 fillers were taken out and 1 kept; 5 pauses were taken out, with the limit raised on 4 of 12 lines; the pause between lines was the default on 11 of 12; 8 of 14 graphic edges snapped onto a cut. The two levels (`-46` and `-40 dBFS`) were set on that lav; they live in `media.lav` (`silence_dbfs`, `pause_dbfs`) so each recording carries its own.

## Layouts

Regions are `[x, y, width, height]` in frame pixels. A layout has a `graphic` region, a `picture` region, or both; one with both is a panel layout (the graphic above, his picture in the panel), and it holds `framings`: named head-and-shoulders framings (`zoom`, `pan`, `tilt`, in the panel's own units) that a shot picks with `panel_framing`. The layout in force when no graphic is up must be named `picture`. Each layout says where the caption band sits (`subtitles_centre_y`); the band is one height for the whole video, because Resolve's subtitle template takes one position per track.

A jump cut is a picture cut where the same camera continues across removed time with unchanged `zoom` and `panel_framing`; screen recordings (`media.cameras.<name>.camera` containing “screen”) are excluded. It is also excluded when a layout with no `picture` region hides his face there or the layout changes on that frame. In a panel layout his face is still on screen, so a jump still shows. The cut list reports every one.

## A graphic

```json
{
  "id": "trip",
  "kind": "terminal",
  "layout": "split",
  "content": { "command": "where-was-i trip 2025-06-23", "columns": 36, "capture": "graphics/content/trip-2025-06-23-36.txt", "prompt": "$ " },
  "in":  { "line": "trip", "at": "Here's", "offset_s": -0.2 },
  "out": { "line": "night", "at": "there.", "edge": "end" },
  "cues": [ { "at": { "line": "la", "word": "Bell," }, "do": "highlight", "target": "Night: Bell" } ]
}
```

The four layers stay apart: **content** (what is shown), **cues** (when, anchored to his words), **layout** (where in the frame), and the **look** (type, colour, sizes, motion), which lives only in the look module.

Anchors: `in`, `out`, a cue's `at` and `until` all name a word in a line (`at` or `word`, with `edge` `start` or `end`, `offset_s`, and `n` for the nth occurrence). A word may be a phrase of several transcript tokens (`"L.A. X"`); it is matched like the cut builder matches, lower case with punctuation ignored. A graphic's `in` and `out` resolve to the cut list's frames, and an edge within 8 frames of a picture cut moves onto it (reported under `graphic_snaps`). `hold_s` sets `out` to the resolved start frame plus the nearest whole-frame hold duration and can lengthen the film. The dialogue must be rebuilt when film length changes. Every cue and graphic edge resolves to the frame Resolve's transcription of the finished dialogue gives its word (`pipeline/resolve/align_words.py` writes those frames into the cut list and snaps edges again), so the graphics step needs a cut list that has been through that step.

Cues: `do` is one of the verbs the kind draws, matched exactly; any other verb stops the build. `target` names what the cue acts on by its exact text in the content (a row, a label, a file name); `after` makes the search start after another piece of text; a cue with no `target` acts on the whole view. `until` ends the item on a later word, for a terminal `scroll` and for a `photo-panel` photo; a highlight lasts until the next highlight, a card row until the next card, and a grid's photos and labels to the graphic's end. `first_frame: true` draws show cues from the graphic's first frame; terminal highlights, typing and scrolling keep their aligned frames (no fade from nothing, which reads as a flash over the camera). `hides_subtitles: true` means no captions while the graphic is up, because it shows his words itself. A graphic whose content has a `title` draws the title: `slot` names its heading in `words.md`, and the words there are shown, a part in `[[double brackets]]` on the highlight and a ` / ` between words breaking the line (otherwise the title wraps inside its margins); `centerY`, `fontSize`, `band`.

Two routes draw them: `terminal`, the agent box and `keyline` are rendered by Remotion as transparent clips (`pipeline/graphics/`); `photo-grid`, `photo-panel`, a title and `closing` are Fusion compositions built by script in their own small timelines in the Resolve project (`pipeline/resolve/build_graphics.py`), so a change of words is a script call, not a render. Both are placed above the cameras by the timeline builder. The kinds, and what each draws from:

| Kind | Content | Cues |
| --- | --- | --- |
| `terminal`, a command | `command`, `columns`, `capture` (the tool's real output, captured at that width with `pipeline/graphics/capture-terminal.py`), `prompt` | `type` (the command types, then the output prints), `show` (scroll the target row into view), `highlight` (light the target's cells until the next highlight), `scroll` (to the target, ending on `until`) |
| `terminal`, an agent's box | `columns`, `prompt`, `start_screen` (the agent's start screen, captured as text) and no `capture`: his words from `in` to `out` type into the box as he says them, each on its aligned frame | none |
| `photo-grid` | `photos` (a list file: `{path, label, taken}` per photo), `use` (labels to pick), `darken`, `title`; columns never exceed the number of photos | `show` (a photo, by label or file name; no target: all), `label` (the labels) |
| `photo-panel` | `photos` (a list file: `{path, label, sublabel}` per photo, with an optional `position`, the crop's focus as CSS object-position) | `show` (a photo, until its `until` word or the graphic's end) |
| `keyline` | `command`, `prompt`, `typeCommand`, `commandColumns`, `keyColumns`, `cards` (rows of the real output); without a command, optional literal `header` fills the command row and `commandColumns` defaults to `keyColumns`; a photo beside it is a `photo-panel` graphic of its own on the track above | `show` (a card row), `highlight` (a row's text) |
| `closing` | `slots`: the parts the page draws, each mapped to a heading in `words.md`, from `headline`, `ask`, `prompt` (the prompt box), `pill` (the button) and `mission`. A part with no slot is not drawn and the others close up: with a headline and a mission line the page spans its band, otherwise its parts sit together in the middle of it | none; `hold_s` sets its length; ` / ` forces a break in any part, addresses keep their hyphens, and margin or safe-area overflow warns |

Words on screen (titles, cards, the closing page) come from `words.md`: a slot reads the `Final:` line under its heading, Josh's settled words; while that is empty it reads the `Proposed:` line, an agent's proposal, and the build records which was used so a cut he sees never carries a bracketed placeholder. A slot is one line; the graphic wraps it inside the margins.

## The mixer's fields

- `dialogue_patches`: `{from_s, to_s, line, fade_s, gain_db, why}` on the source clock. Without `gain_db` the stretch becomes room tone (a click, a false start, a scrap of the next word); with it the stretch is changed by that signed gain in dB, so `-8` lowers it by 8 dB (a breath that reads as a grunt). Fades default to 15 ms.
- `dialogue_inserts`: `{line, at_s, from_s, to_s, why}`: a word borrowed from elsewhere in the same lav, laid at `at_s` on the receiving clip's source clock.

A room-tone window is checked after high-passing at 1 and 4 kHz: report any 5 ms window over 6 dB above that band’s own median. A full-band floor can hide clicks under hum.

## What reads it

The cut list (`pipeline/cut/`) finds each line's words, places every cut in real silence on the lav, resolves shots, graphics and cues, and reports what needs a decision. The dialogue (`pipeline/audio/`), the word timing and the Resolve steps (`pipeline/resolve/`: the timeline, the Fusion graphics, the in-place changes, the renders), the terminal graphics (`pipeline/graphics/`) and the captions (`pipeline/subtitles/`) read the cut list, never the transcript. The run order and commands are in `README.md`.

The cut list carries `cut_inputs`, the parts of the edit data a cut depends on (`pipeline/cut/build_cutlist.py`, `cut_inputs`: format, spelling, layouts, graphics, lead-in, each line's words, keep, retime, cut points, pauses and shots, and the media's transcript, lav and camera files, offsets and face-touch scans), and `edit_sha256`, a hash of them. The graphics builders refuse a cut list whose `cut_inputs` differ from the edit data's now, so a camera's grade, a framing or a mixer field can change without a cut-list rebuild.

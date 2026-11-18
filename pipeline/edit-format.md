<!-- Updated by AI on 2026.11.17 by Claude Opus 5.5 for the rebuild: `log` and `framing` on cameras, grades read back, assemble.py writes the list from a plan, the older format removed with its code. Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J): the edit list of skill B, to the timeline layout in video-skills-redesign/2026-10-21-fable/poc/hillclimb/layout-design.md. `cameras` and `segments` revised for the cut and finish timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. `multicam` and the `cameras` fields `file` and `reference` made to match the code by Claude Opus 5.5 (hill-climb stream I) the same day. `cameras` field `picture_offset_s` added by Claude Opus 5.5 on 2026-10-29, for `qc.py`'s lip sync. -->

# The edit list: `edit-list.json`

One file per video, in the video's folder, holds every editorial decision as rows in the Resolve timeline's own terms. The model decides every value: `assemble.py` writes the list from the model's plan (its help gives the plan's format), and `note.py` keeps it in line with a note applied in place. `pipeline/b/place.py` builds the cut timeline from it exactly, `pipeline/b/finish.py` makes that cut's finish timeline (flattened, graded) from the cut and the list, and `pipeline/b/readback.py` reads either back into the same shape, so a difference between list and timeline is a fault. Every row may carry `why`, a few words for the next reader; code never reads it. Frames are the timeline's frames from 0; seconds are on the front camera's clock unless a field says otherwise.

## Top level

| Key | What it holds |
| --- | --- |
| `resolve_project` | The Resolve project the timeline is built in. |
| `fps`, `format` | The timeline's rate and its `width` and `height`. |
| `look` | The name of the look in `Media/Edits/looks/`. |
| `duration_frames` | The timeline's length. |
| `multicam` | The name of the cameras' multicam clip in the media pool (ingest makes it as `cameras`). |
| `cameras` | Per camera, by a name the list chooses (`front`, `wide`): `file`, the camera's file, which is how `place.py` finds its angle in the multicam (it reads each angle's file and sync offset from the multicam itself); `log`, Resolve's name for its input colour space (`"Nikon N-Log"`, `"DJI D-Gamut/D-Log"`), which `project.py` sets; `grade` (an ASC CDL: `slope`, `offset` and `power` as `[r, g, b]`, and `saturation`) and `group` (the name of the camera's colour group), which `finish.py` applies to the clips that show that camera on the finish timeline and reads back (the cut timeline carries no grade); and `reference: true` on the camera the others are matched to, which `qc.py` measures colour against. The colourist's. `picture_offset_s`: front-camera time = this camera's time + offset, for its picture, as ingest established it picture against picture; 0 on the front camera. `assemble.py` and `look.py` compute a segment's source frame from it, and `qc.py` times lip sync by it. `framing`, optional: the framing a plan's shot on this camera gets when it gives none. |
| `segments` | V2: the multicam, cut; plain clips of the same cameras on the finish timeline. |
| `panels` | Plain clips: the look's background on V1 and the app on V3. |
| `titles` | V4: the look's Fusion templates as title items. |
| `audio`, `sound` | A1: the dialogue pieces; A2: the room tone. |
| `captions` | ST1. |

## Rows

- **`segments`:** `{camera, source_in, record, frames, framing, speed_percent?, retime?}`. `camera` names one of `cameras`. `source_in` is a frame of that camera's own file; `place.py` adds the angle's offset, so switching a segment's camera means a new `source_in` for the same moment. `framing` is the shot's whole framing on its camera (`ZoomX`, `ZoomY`, `Pan`, `Tilt`: standard, a punch-in, under a panel), set on the segment on the cut timeline and again on its clip by `finish.py`, because flattening resets it; the two cameras need different values for the same shot, so a camera switch changes it too. `speed_percent` under 100 holds or slows the shot; `retime` is Resolve's retime process for it: `nearest`, `optical`, `frame blend` or `project`.
- **`panels`:** `{file, source_in, source_out, track, record, framing, group}`, with `speed_percent` and `retime` as for segments: `track` is 1 for the background and 3 for a screen-recording crop, a still or a rendered Remotion clip; `group` is its colour group. Screen material takes no grade.
- **`titles`:** `{template, inputs, record, frames}`; the track is always V4. `template` names one of the look's Fusion templates; `inputs` are its published inputs, the text's pill ranges included (`[[ ]]` round the words on the pill).
- **`audio`:** `{file, source_in_s, source_out_s, record_s, fade_in_ms, fade_out_ms, crossfade_ms?}`, in seconds, with optional `pre_roll_s` (the sound starts that much earlier), `patches` (`{source_in_s, source_out_s, fade_ms}`: room tone over a stretch of the piece), `voice_isolation` (0 to 100) and `dialogue_leveler` (true or false). `crossfade_ms` on a row means the join into the next piece is a crossfade of that length, centred on the cut, which plays half its length of source beyond the cut on both sides; without it the join is a butt join with the two clip fades. A piece before a gap has no crossfade.
- **`sound`:** `{lav, room_tone_s, room_tone_crossfade_ms, room_tone_end_fade_ms}`: the lav file the pieces come from, the room-tone window `[from, to]` in its seconds, the crossfade between loops of the window under a long gap, and the fade at the end.
- **`captions`:** `{text, start, end, words}`: the caption as it reads, with `\n` at its line break; its start and end in seconds; each word as `{text, start, end}`. `captions.py` makes them whole frames for the look's template.


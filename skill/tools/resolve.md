<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); the multicam, flattening and changes for the two timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. -->

# DaVinci Resolve Studio 21.1 on this Mac

Tested facts only, each with its date. "API" is the stub `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi`, by line; "p." is the manual, as text at `~/.cache/video-edit/resolve-21.1-manual.txt` (if missing: `nix shell nixpkgs#poppler-utils -c pdftotext -layout "/Applications/DaVinci Resolve/DaVinci Resolve Manual.pdf" ~/.cache/video-edit/resolve-21.1-manual.txt`). Test records are under `Media/Edits/.cache/`.

## Driving it

- **External scripting from a shell works;** run each script under `/usr/bin/python3 -B`, never a devenv's Python, with:
  ```sh
  export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
  export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
  export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules" PYTHONUTF8=1
  ```
  and through the video's lock (SKILL.md, "The roles"). On 21 Oct the MCP's `run_script` returned nothing for every script, `print("hello")` included; check it with that before trusting a silent result.
- **`fusionscript.so` can segfault as Python exits,** after the work is done (22 Oct). End your scripts with `os._exit(0)` after flushing.
- **Failure is a quiet `False`, `None` or empty list.** Read back every setting and placement.
- `ImportMedia([path])` works; the dictionary form returned None (21 Oct). A timeline name with colons fails `CreateEmptyTimeline` (22 Oct).
- **The page matters.** `TranscribeAudio` returns False on the Color page and works from the Edit page (21 Oct). A render switches to the Deliver page; `resolve.OpenPage("edit")` restores it. Track calls return False on a timeline that is not current: `project.SetCurrentTimeline` first (22 Oct).
- **Every change is saved at once** (Live Save). There is no undo: try anything new on `Timeline.DuplicateTimeline` (API 2203), never on a timeline Josh has seen.
- **A dialog stops scripting** ("Update Available", "Render Cache Disabled"). Relaunching with `open -g -a "DaVinci Resolve"` brought its windows over Josh's work and he objected (21 Oct).
- **With the Project Manager open and no project loaded,** `LoadProject` returned None, and cancelling "Create New Project" quit Resolve (21 Oct).
- **After a sleep or a drop.** After the Mac has slept with Resolve open, or the SSD has dropped and returned, quit Resolve (`resolve.Quit()`, API 1555) and relaunch it before any script, holding the video's lock; the relaunch can bring its windows forward (above), so tell Josh first if he is at the Mac. Then trust a render only by its frames: `GetClipProperty("Online Status")` read "Online" both times while frames rendered "Media Offline" (22 and 26 Oct). On 22 Oct reloading the project cleared it; on 26 Oct a reload by script crashed Resolve four seconds later and only a relaunch cleared it, with Resolve's log showing an I/O error on every file.
- **It crashed on:** `AppendToTimeline` on an imported SRT (17 Oct), adding Magic Mask to a Fusion composition by script (18 Oct), and `comp.Render()` on a timeline clip's composition, after which nothing worked until a relaunch (14 Oct).

## Before you say Resolve cannot

Resolve gains features faster than any model's training. Read `get_whats_new` (the MCP) since the version you know, search the API stub with `rg` or the MCP's `search_scripting_api`, read the whole manual procedure, then test on a duplicate. Josh: "remember you have access to the resolve manual if you need to figure stuff out instead of guessing". A "cannot" names the call, the state, the exact return value and the route that works instead.

## What scripting reaches, and what it does not

- **Placing:** `AppendToTimeline` with a source range, track and record frame (API 1900); for video `endFrame` is exclusive. Audio source points are rounded to whole frames (`tools/audio.md`). A still ignores its range and comes in 125 frames long; marks on its media pool item give an exact length.
- **No call moves, trims, slips or rolls an item already placed** (API 2311 to 2330 are getters only). So a change of structure is a re-place.
- **The timeline's file reaches what the API does not.** `Timeline.Export` as `.drt` (a zip of XML) and `ImportTimelineFromFile` with `importSourceClips: False` carry, read back exactly: a multicam segment's angle, sub-frame audio edges and crossfades, every caption, and every title with its inputs (26 Oct). An import makes a new timeline named after the file, ignoring a `timelineName` option.
- **Picture:** `SetProperties` with Zoom, Pan, Tilt and crops (21 Oct). One unit of `Pan` moves the picture by the clip's fitted width divided by the timeline's width in pixels: 3.16 px for a 3840 by 2160 camera in a 1080 by 1920 frame, 2.75 for a 3456 by 2234 screen recording; `Tilt` is in timeline pixels, up positive; `CropBottom` is in fitted pixels before zoom (22 Oct). `SetFades` takes fractional frames on audio and captions (21 Oct).
- **Transcription:** `TranscribeAudio` then `GetTranscription` (API 2059, 2098): words with start and end on whole frames, `(...)` for a silence and for every um. A timeline's own media pool item (`Timeline.GetMediaPoolItem`, API 2272) transcribes the whole timeline on its clock (21 Oct). 23 minutes of lav took 87.5 s (22 Oct). It misheard "Codex" as "Kodux" and dropped a film's last sentence that Whisper heard clearly.
- **Sync:** `Timeline.AutoAlignClips` by waveform (API 2191) placed the wide camera's sound 23 ms from the cross-correlated offset (21 Oct).
- **Multicam:** `MediaPool.CreateMulticamClip` with audio sync (21.1) made the two-camera multicam in 9.5 s (26 Oct). With the lav in, it became a black angle that every new segment defaulted to. No call reads inside a multicam (`GetTimeline()` returns None) or sets a segment's angle; the angle is a field in the timeline's file, and `TimelineItem.GetName()` reads it back as "<multicam> - <camera file name>". Framing and speed set on a segment stay with it when its angle changes (26 Oct), so an angle switched in the viewer shows the new camera at the old camera's framing until it is reframed. Whether the interface's Clip > Multicam Switch writes the same field is untested: read back after Josh switches one.
- **Flattening:** `TimelineItem.FlattenMulticam(resolve.FLATTEN_MULTICAM_COPY_GRADE)` (21.1) turns a segment into a plain clip of its active angle, in the same place, with the right source frames and its speed kept, but resets its framing to zoom 1, pan 0, tilt 0 (26 Oct). It is one way: the angle switch is gone. So flatten only a duplicate, which is what `finish.py` does, and set the framing again after it. The copy-grade option copies any grade the multicam's angles hold; ours hold none, because nothing is graded on a cut timeline. The finish timeline's routes are each tested (`DuplicateTimeline` keeps every clip, its grade and the caption track, 22 Oct; flattening, 26 Oct; `SetProperties` and `SetCDL` on plain clips); a whole cut finished by `finish.py` had not been rendered when this was written, so read it back and open its frames.
- **Colour:** colour groups; a CDL on an item's node (`SetCDL`), on plain clips and on multicam segments (26 Oct); `CopyGrades` (API 2473) copied a clip's whole node stack, CineFocus and Magic Mask included, to the same shot on another timeline (22 Oct). A group's graph takes only a LUT by script (`ApplyGradeFromDRX` returned False on it in every mode, 22 Oct), so a group cannot carry the CDL: `finish.py` sets it on each clip and puts the clip in its camera's group, where the colourist's hand work on the group (a Sat vs Sat curve) reaches every clip of that camera. No call adds a node or an effect.
- **Captions:** `SetName` on a caption returned False (21 Oct), so text reaches the track only through the timeline's file (below).

## Colour management

The project: DaVinci YRGB Color Managed, DaVinci Wide Gamut with DaVinci Intermediate as the timeline space, Rec.709 Gamma 2.4 out, DaVinci tone mapping (pp. 235 to 241). Set each camera's input colour space by hand and read it back: the DJI files carry Rec.709 tags and Resolve took them as Rec.709 (15 Oct). `"Nikon N-Log"` and `"DJI D-Gamut/D-Log"` took (21 Oct). The round trip dims anything already Rec.709: white 255 in a graphic came out 188 until "Use Inverse DRT for SDR to HDR Conversion" was on, which keeps Rec.709 clips exact (p. 241; 17 Oct). Never change the timeline colour space once grading has started.

**Fusion works in linear light,** so a typed colour comes out wrong: page grey 23 came out 70 and the pill orange (255, 139, 0). A Color Space Transform at the end of each graph (Rec.709 colour and gamma in, DaVinci Wide Gamut linear out, no tone mapping) brought a 162-colour chart back with no error (22 Oct). Load photos at float depth; name photo files without bare numbers, or the Loader reads `00.jpeg`, `01.jpeg` as one sequence.

## Titles

`InsertFusionTitleIntoTimeline("Text+")` (API 2251) inserts between the marks on the track of the last clip appended, as a ripple insert on every unlocked track; it returns None when that track is locked. So on a timeline that already has picture: lock every other track, append one frame of any clip on V4 after the titles, then for each title in record order set the marks and playhead, insert `Text+`, `ImportFusionComp` the look's template onto the item and set its inputs; then delete the one frame and unlock (26 Oct). V1 to V3 stay untouched, and the frames match the old nested route pixel for pixel. Inputs read back from the item; the pill ranges (`[[ ]]`) only from the file. A word change on the item took 0.01 s. Inserting a template by name returned None; whether installing it as an Edit page title and restarting fixes that is untested. Text+ Size 0.1506 draws 100 px Futura (22 Oct).

## Captions

- A Fusion template dropped on a subtitle track styles every caption (pp. 1240, 1242); his look's template is built from the stock Word Highlight one, which walks the pill on per-word timings.
- **One position for the whole track:** with the template applied a caption's own position is greyed out (17 Oct). The look owns the band's height (`subtitles.resolveTemplate.centreY` in `look.json`, measured up from the bottom).
- **By file:** a `.drt` from `Timeline.Export` carries the subtitle track whole, with each caption's text, frames and word times; `pipeline/subtitles/write_caption_track.py` writes captions into it and `ImportTimelineFromFile` brings it back. 66 captions went on in 0.9 s and every one read back (22 Oct). The format changes between Resolve versions: after an update, try it on a scratch timeline first. `ImportIntoTimeline` ignores the subtitle track.
- **Template facts:** word times must be whole frames (a half frame made the pill stick); the pill drops when a word's time ends; a word starting more than 25 frames after the one before starts a new page (every gap over 25 split, none at 25 or under, 22 Oct); Size 0.117 draws 77.7 px Futura Bold; its colours are linear values, and the old ones rendered (255, 69, 0) for #D9531E. Only the enabled subtitle track burns in (p. 1248).

## Changing a placed timeline

The kept scripts (`create_project.py`, `remove_range.py`, `replace_media.py`, `copy_grades.py`, `add_captions.py`) read the project's name, the look and the format from a small `edit/edit.json` in the video's folder, which ingest writes for `create_project.py`. Keep it to those facts; every editorial value lives in the list.

Every change ends with `finish.py` on the changed cut, which makes its finish timeline again (`roles/director.md`, "Applying a note").

A camera switch (the segment's `camera`, `source_in` and `framing`, `roles/editor.md`) is a change to the list and a re-place. A regrade is a change to the list's `cameras` block and a re-finish; the cut timeline does not change. `pipeline/resolve/copy_grades.py` brings per-shot Color page work across from the old finish timeline to the new one, matching by file, source start and length, and lists what it could not match (22 Oct).

In place, on a duplicate of the cut timeline under a new name, which keeps every clip and the caption track (22 Oct):

- **Change a title's words:** set the input on its item (`graphic.py`'s function), then `readback.py`.
- **Remove a run of whole clips:** `pipeline/resolve/remove_range.py`, a ripple delete between two existing cuts. Everything later moved up exactly, captions included, and a graded clip kept its grade and mask (22 Oct). It refuses when anything crosses an edge. The sound join it makes is on a frame with a one-frame fade each side; nobody has listened to one.
- **Swap the file behind a panel, same timing:** `pipeline/resolve/replace_media.py`, this timeline only (22 Oct). `MediaPoolItem.ReplaceClip` changes every timeline using the item, Josh's included: never use it.
- **Reframe:** `SetProperties` on the segment, then `readback.py`.

`remove_range.py` and `replace_media.py` were tested on plain clips, before the multicam and the one-track dialogue: read back after each until one has run on a cut timeline. `copy_grades.py` runs between finish timelines, which hold plain clips as in its test.

## Rendering

Render a finish timeline, never a cut timeline, which has no grade. `pipeline/resolve/render_timeline.py PROJECT TIMELINE OUTPUT --preset phone|post|master|still [--subtitles] [--range IN OUT] [--load-render-preset NAME]` renders and waits: it returns when the job is complete, its marks cleared and the job deleted, so the Resolve lock is held for the whole render (a render that returned at once let a placing run under it and fail, run 3). NAME is the loudness preset `loudness.py` prints, loaded first. Exit 1 when the render fails. All refuse an existing file. Resolve's AAC is fixed at 320 kbit/s (21 Oct). The 81 s phone file: 27.9 MB, -14.1 LUFS, -1.1 dBTP (22 Oct). An 81 s master took about 4 minutes; CineFocus roughly doubles it, and the render cache did not help (18 Oct). Keep the cache on the SSD at `Media/Resolve Cache`: when the internal disk filled, Resolve raised a dialog that blocked every script.

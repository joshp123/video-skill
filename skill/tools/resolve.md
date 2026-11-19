<!-- Rewritten by AI on 2026.11.19 by model claude opus 5.5 from the 29 Oct file and its 17 and 18 Nov corrections, for one timeline with the front camera below and the wide camera above, edited in place. Facts carry their source: a date means tested on Josh's Macs that day (private/research/2026-11-17/resolve-smoke-tests.md, resolve-angle-and-word-timing.md, rebuild-tooling.md); "API" is the stub by line; "p." is the manual. -->

# DaVinci Resolve Studio

**Last checked against: Resolve Studio 21.2.0.6, on 17 Nov 2026** (the installed scripting changelog and the API stub). When Resolve is newer, read what changed at the end of the video (SKILL.md, "Tools") and update this line.

## Where the truth is

- **The API stub,** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi`, cited as "API". Search it with `rg` or the MCP's `search_scripting_api`; `get_scripting_docs` has the README.
- **The manual** as text, `~/.cache/video-edit/resolve-21.2-manual.txt`, cited as "p." (page numbers below were read in the 21.1 copy beside it, which is almost identical). If missing: `nix shell nixpkgs#poppler-utils -c pdftotext -layout "/Applications/DaVinci Resolve/DaVinci Resolve Manual.pdf" ~/.cache/video-edit/resolve-21.2-manual.txt`. Read the whole procedure for a feature, not one line. Josh: "remember you have access to the resolve manual if you need to figure stuff out instead of guessing".
- **The changelog,** `Developer/Scripting/CHANGELOG.md` beside the stub, installed with each release. The MCP's `get_whats_new` reads a copy built into the server that stops at 21.0.4 (17 Nov), so it misses recent calls. Resolve gains calls faster than any model's training.

## Before you say Resolve cannot

Read the manual's procedure, search the API for the feature by every name it might have, search the web for others doing it, then try it on a duplicate timeline. A "cannot" names the call, the state it was made in (page, current timeline, track lock), the exact return value, and the route that works instead. Most failures here have been a call made from the wrong page or on a timeline that was not current.

## Driving it

- **From a shell,** under `/usr/bin/python3 -B` (not a devenv's Python), with:
  ```sh
  export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
  export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
  export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules" PYTHONUTF8=1
  ```
  The pipeline's commands start Resolve with `-nogui` themselves. On 21.2 the MCP's `run_script` returns printed output and the result (17 Nov).
- **Windowless** (`-nogui`): ran scripts, placed clips, exported frames and rendered with the Studio licence, over ssh with the screen locked, never taking focus; ready about 7 s after launch (17 Nov).
- **End scripts with `os._exit(0)`** after flushing: `fusionscript.so` can segfault as Python exits (22 Oct).
- **Failure is quiet:** a `False`, a `None` or an empty list, rarely an error. Read back every setting and placement.
- **The page and the current timeline matter.** `TranscribeAudio` returns False on the Color page and works from the Edit page (21 Oct). A render switches to the Deliver page; `resolve.OpenPage("edit")` restores it. Track calls return False on a timeline that is not current, so `project.SetCurrentTimeline` first, and retry a few seconds later when it fails just after another script (22 Oct).
- **Every change saves at once** (Live Save) and scripting has no undo: try anything new on a `Timeline.DuplicateTimeline` first.
- **A dialog stops scripting,** and a windowless Resolve still shows it, on Josh's screen or another Space. `SaveProject()` with the unnamed "Untitled Project" current (after launch or `CloseProject`) opens "Save Current Project" and never returns (17 Nov). Keep the cache on the media drive so a full internal disk never raises "Render Cache Disabled". Relaunching with `open -g -a "DaVinci Resolve"` still brings its windows over his work.
- **With the Project Manager open and no project loaded,** `LoadProject` returned None, and cancelling "Create New Project" quit Resolve (21 Oct).
- **`ImportMedia([path])`** works; the dictionary form the README recommends returns None (17 Nov). A timeline name with a colon is refused.
- **It crashed on:** adding Magic Mask to a Fusion composition by script (18 Oct); `comp.Render()` on a timeline clip's composition, after which nothing worked until a relaunch (14 Oct).
- **Memory:** Resolve grew to 10 GB within a stage and 17 GB over 45 minutes of blur work (18 Nov). Quit and relaunch between heavy stages.

### After a sleep or a drop

After the Mac has slept with Resolve open, or the media drive has dropped and returned, quit Resolve and relaunch it windowless before any script. Then trust a render only by its own frames: `GetClipProperty("Online Status")` read "Online" while frames rendered "Media Offline" (22 and 26 Oct). A relaunch cleared it both times; a reload by script once crashed Resolve.

## Editing the live timeline

The layout: the front camera's clips on the lower camera track, the wide camera's above it only where the film shows it. Switching a shot to the wide camera is one appended wide clip plus its framing, colour group, CDL and blur copy, well under a second; switching back is deleting or disabling it (18 Nov); `SetClipEnabled` on a stacked clip took 3 to 4 ms (17 Nov, Mac mini). The clips on different tracks are not linked, and scripted edits do not obey Resolve's sync lock the way the interface does, so every edit that moves time treats every track.

- **Placing:** `MediaPool.AppendToTimeline` takes a clip, source range, track, record frame and media type (API 1900); for video `endFrame` is exclusive. A still ignores its end frame and lays 5 s, so trim it after (18 Nov). An audio source point is rounded to a whole frame on append: an appended lav copy came out 5 ms late (18 Nov).
- **Trims and moves:** `SetLeftOffset`, `SetRightOffset` (in source frames), `SetPosition` and `Timeline.MoveItems` each took 0.5 to 3 ms and changed only the item named; an overlap overwrites its neighbour (17 Nov). On audio they take sub-frame values with `subframePrecision=True`, read back to a thousandth of a frame, while the preference "Align audio edits to frame boundaries" is off; with it on they return True and round. `LoadUserPreferencesPreset` switches that preference live (17 Nov).
- **`MoveItems` once per track.** Moving all tracks in one call moved them by one reference item's offset, 29 frames wrong. Crossfade transitions are listed among a track's items and must be left out of the move (18 Nov).
- **No blade.** A cut across a clip is a trim plus a copy of the clip for the other side, given the original's attributes (`CopyAttributes`) and grade (`CopyGrades`). Do it in order (trim, move, then copy), or the copies block the move. Ten frames cut from a pause inside a piece moved all 145 later items exactly on every track, captions included, in 0.23 s (18 Nov).
- **`Timeline.DeleteClips(items, rippleDelete=True)`** shifts every unlocked track, not one (17 Nov).
- **Crossfades:** `TimelineItem.AddTransition` adds "Cross Fade +3 dB" (constant power, which the join checker is trained on) or "Cross Fade 0 dB" (linear) at a whole frame. The transition cannot be moved or trimmed, a one-frame one is not centred, and a trim drags it with the clip's edge or removes it. So crossfades go in through the timeline's file (below) after any edit that touches a join (17 and 18 Nov).
- **Framing:** `TimelineItem.SetProperties` sets Zoom, Pan, Tilt and crops. One unit of `Pan` moves the picture by the clip's fitted width divided by the timeline's width in pixels: 3.16 px for a 3840 by 2160 camera in a 1080 by 1920 frame, 2.75 for a 3456 by 2234 screen recording; `Tilt` is in timeline pixels, up positive; `CropBottom` is in fitted pixels before zoom (22 Oct). A clip placed for a switched shot takes none of the old clip's framing or grade.
- **`SetFades`** takes fractional frames on audio and captions (21 Oct).
- **`MediaPoolItem.ReplaceClip`** changes every timeline that uses the item, the one Josh saw included: never use it.

### The timeline's file

`Timeline.Export` as `.drt` writes a zip of Resolve's own XML description of the whole timeline (21.2 zstd-compresses an item's field data), and `MediaPool.ImportTimelineFromFile` with `importSourceClips: False` brings it back against the same media, as a new timeline named after the file. Because the file is Resolve's complete description, anything it holds can be set by writing it: sub-frame audio edges and fades, crossfades, every caption with its words' times, every title with its inputs (26 Oct; 17 Nov after a fix to the pipeline's reader). An import makes a new timeline of new clips, so by the duplicate result under "Rendering" it starts with no render cache, and the blurred clips need a fresh fill of about 6 to 7 minutes (inferred, not tested directly). It is undocumented: after a Resolve update, round-trip a scratch timeline before trusting it. `Timeline.ImportIntoTimeline` takes AAF only and ignores the subtitle track.

## Transcription and captions

- **`MediaPoolItem.TranscribeAudio`** then `GetTranscription` (API 2059, 2098): words with start and end on whole frames, `(...)` for both a silence and an um, a repeated phrase collapsed, a cut-off word dropped; no verbatim mode. 23 minutes of lav took 87.5 s (22 Oct). It misheard "Codex" as "Kodux". Its word times ran 0.2 to 0.4 s late in others' tests on 21.1 and 21.2.
- **`Timeline.CreateSubtitlesFromAudio`** makes a subtitle track from the sound, breaking lines by a count of characters, not by phrase. Setting a transcription first with `SetTranscription` does not help: it transcribes again and ignores the text (17 Nov).
- **No call creates a caption or sets its word times.** An SRT appended to the subtitle track lands after the timeline's end (it ignores `recordFrame`), and one `MoveItems` then gives the captions the right phrasing and timing but no per-word times; SRT and WebVTT carry none, and TTML is refused (17 Nov). `SetName` on a caption returns False. So captions with their word times go in through the timeline's file: 2 captions and 7 words in 677 ms, read back exactly, the pill moving word by word in the render (17 Nov). In the interface, "Update Word Timings" in the Inspector re-times a caption's words from the sound in one click, which is what Josh can use after retyping one.
- **The caption template.** A Fusion template on a subtitle track styles every caption on it (pp. 1240, 1242); the look's is built from the stock Word Highlight one, which lights each word on its own time. With a template applied a caption's own position is greyed out, so the track has one band height for the whole video (17 Oct). Word times must be whole frames (a half frame made the pill stick); the pill drops when a word's time ends; a word starting more than 25 frames after the one before starts a new page (22 Oct). Size 0.117 draws 77.7 px Futura Bold. Only the enabled subtitle track burns in (p. 1248).

## Sync

`Timeline.AutoAlignClips` by waveform (API 2191) placed the wide camera's sound 23 ms from the cross-correlated offset (21 Oct). It gives one offset and no drift. The pipeline places the wide camera from the picture offset ingest measured (`tools/cameras.md`).

## Multicam

No call sets or reads a multicam segment's angle, and `PerformMulticamSmartSwitch` chooses angles itself by who is speaking (17 Nov). The layout above uses plain clips on two tracks instead, which is why it needs no multicam.

## Colour

- **Colour groups:** `TimelineItem.AssignToColorGroup`; a group's Pre-Clip and Post-Clip graphs. By script a group's graph takes only a LUT: `ApplyGradeFromDRX` returned False on it in every mode (22 Oct).
- **A CDL on an item's node:** `TimelineItem.SetCDL` (API 2449); `GetCDL` reads it back exactly (17 Nov). So a camera's CDL goes on each of its clips, and the hand work on the group reaches every clip of that camera.
- **Effects:** `TimelineItem.AddEffect` adds a Fusion or OFX clip effect, but nothing sets an OFX effect's parameters, and no call adds a Color page node. `Graph` counts nodes, reads their tools and labels, enables or disables them and sets a LUT. `ApplyGradeFromDRX` with a still grabbed and exported by script leaves one empty node (18 Oct, 18 Nov).
- **`TimelineItem.CopyGrades`** (API 2473) copies a clip's whole node stack, CineFocus and Magic Mask included, onto other clips and other timelines, even from a clip in an imported timeline file whose media is offline (22 Oct, 18 Nov). Node 1 comes across too: `SetLUT(1, '')` and `SetCDL` put the camera's own grade back (skin within 1/255). This is how the look's blur reaches every wide clip from its carrier.
- **`TimelineItem.CreateMagicMask(mode)`** tracks a copied Magic Mask by script, and the render then follows him closely, glasses rim included; but it shows a small untitled progress strip on the desktop in use, even windowless, which stays until Resolve quits, so the pipeline does not call it on Josh's Mac (18 Nov). Without it the copied mask still keeps him sharp; the far rim of his glasses can break up on some shots.
- **Others in reach:** `SmartReframe`, `Stabilize`, grade versions (`AddVersion`, `LoadVersionByName`), gallery stills and PowerGrade albums.

## Colour management

The project: DaVinci YRGB Color Managed, DaVinci Wide Gamut with DaVinci Intermediate as the timeline space, Rec.709 Gamma 2.4 out, DaVinci tone mapping (pp. 235 to 241); the pipeline sets it and reads it back. Each camera's input colour space is set and read back: the DJI files carry Rec.709 tags and Resolve took them as Rec.709 (15 Oct), so set "DJI D-Gamut/D-Log" and "Nikon N-Log" by hand (21 Oct). The round trip dims anything already Rec.709 (a graphic's white 255 came out 188) until "Use Inverse DRT for SDR to HDR Conversion" is on, which keeps Rec.709 clips exact (p. 241; 17 Oct). Never change the timeline colour space once grading has started.

**Fusion works in linear light,** so a colour typed into a template comes out wrong: page grey 23 came out 70, and the pill's orange came out (255, 139, 0). A Color Space Transform at the end of each graph (Rec.709 in, DaVinci Wide Gamut linear out, no tone mapping) brought a 162-colour chart back with no error (22 Oct). The caption template stores its colours as linear values for the same reason. Load photos at float depth; name photo files without bare numbers, or the Loader reads `00.jpeg`, `01.jpeg` as one sequence.

## Titles

`Timeline.InsertFusionTitleIntoTimeline("Text+")` (API 2251) inserts at the playhead as a ripple insert on every unlocked track, splitting the picture under it. Inserted past the timeline's end, with the marks giving its length, then moved onto its track and frame with `SetPosition` and the look's template loaded with `ImportFusionComp`, it leaves picture and sound untouched (17 Nov). A word change on the item took 0.01 to 0.04 s; inputs read back from the item, pill ranges (`[[ ]]`) only from the timeline's file. Inserting a template by its own name returned None. Text+ Size 0.1506 draws 100 px Futura (22 Oct). 21 added OGraf HTML graphics, which take a file, a trim, a hold and play frames but no per-frame data (pp. 2376 to 2378).

## Sound

Voice Isolation is settable per item and per track (`SetVoiceIsolationState`, amount 0 to 100). `Timeline.NormalizeAudioLevel` changes gain only (`tools/audio.md`, "Level"). `Project.ApplyFairlightPresetToCurrentTimeline(name)` applies a stored Fairlight preset; whether a bus limiter applied that way survives and renders is untested.

## Rendering

A render blocks every other script call until it ends, and the background-render preference did not change that (17 Nov). Resolve's AAC is fixed at 320 kbit/s (21 Oct).

**The blur is the cost.** With the wide camera's blur live, a 91 s film took 12 min 26 s; with it off, about 45 s. The effect runs at the timeline's frame size, about 0.4 s a blurred frame, mostly fixed per frame (the AI depth and mask models); the encoder is not the cost (18 Nov).

**The render cache removes it** (18 Nov, windowless):
- Flag each blurred clip's blur node with `Graph.SetNodeCacheMode(2, resolve.CACHE_ENABLED)`, and set the project's `perfRenderCacheMode` to `user`.
- A windowless Resolve then fills the cache in the background once a page is open and the project is idle: about 6 to 7 minutes for 1,398 blurred frames, about 1 GB of disk per minute of wide camera, on the media drive.
- Deliver uses the cache only when the render preset has `UseRenderCachedImagesForRecording` true. No render setting in the API sets it; it is an element of the preset's XML, and a copy of the loudness preset with it true imports and works.
- From the cache the film rendered in 59 s to 146 s depending on the machine's load, indistinguishable from the live render (PSNR median 49 dB, and by eye round his head and glasses).
- The cache belongs to that timeline's clips. An edit keeps it for every moved clip; only a new or split clip is worked out live (a render straight after a ten-frame cut took 81 s). A duplicate timeline has none (565 s), which is why notes edit the live timeline. A render started before the fill ends renders the uncached clips live.

<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: how Resolve's scripting works, what it reaches and what only the timeline file or the interface reaches, and why. Facts carry their source: a date means tested on this Mac that day; "API" is the stub by line; "p." is the manual. -->

# DaVinci Resolve Studio

**Last checked against: Resolve Studio 21.1, on 29 Oct 2026** (the changelog through `get_whats_new` and the API stub). When Resolve's version is newer than this, the director reads what changed at the end of the video (SKILL.md, "Keep moving into Resolve") and updates this line.

## Where the truth is

- **The API stub,** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi`, cited here as "API" with its line. Search it with `rg`, or with the Resolve MCP's `search_scripting_api`; `get_scripting_docs` has the README (property names, settings, export types).
- **The manual,** as text at `~/.cache/video-edit/resolve-21.1-manual.txt`, cited as "p.". If it is missing: `nix shell nixpkgs#poppler-utils -c pdftotext -layout "/Applications/DaVinci Resolve/DaVinci Resolve Manual.pdf" ~/.cache/video-edit/resolve-21.1-manual.txt`. Read the whole procedure for a feature, not one line.
- **The changelog,** through the MCP's `get_whats_new` since a version. Resolve gains features faster than any model's training: the API has calls a model will not expect, such as `CreateMagicMask` and `PerformMulticamSmartSwitch`.

Josh: "remember you have access to the resolve manual if you need to figure stuff out instead of guessing".

## Before you say Resolve cannot

Read the manual's procedure and search the API for the feature by every name it might have, then try it on a duplicate timeline. A "cannot" written anywhere names the call, the state it was made in (page, current timeline, track lock), the exact return value, and the route that works instead; a second agent reproduces it before anything is built around it. Most failures here have been the call made from the wrong page or on a timeline that was not current, not a missing feature. Josh: "literally all of the times you say "resolve cannot do thing" i yell at you and you find out resolve can do the thing".

## Driving it

- **External scripting from a shell,** under `/usr/bin/python3 -B` (never a devenv's Python), with:
  ```sh
  export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
  export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
  export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules" PYTHONUTF8=1
  ```
  and through the video's lock (SKILL.md, "The roles, and why in this order"). The MCP's `run_script` once returned nothing for every script, `print("hello")` included (21 Oct): test it with that before trusting a silent result.
- **End scripts with `os._exit(0)`** after flushing: `fusionscript.so` can segfault as Python exits, after the work is done (22 Oct).
- **Failure is quiet:** a `False`, a `None` or an empty list, rarely an error. Read back every setting and every placement.
- **The page and the current timeline matter.** `TranscribeAudio` returns False on the Color page and works from the Edit page (21 Oct). A render switches to the Deliver page; `resolve.OpenPage("edit")` restores it. Track calls return False on a timeline that is not current, so `project.SetCurrentTimeline` first, and retry it a few seconds later when it fails just after another script (22 Oct).
- **Every change saves at once** (Live Save) and scripting has no undo: try anything new on a `Timeline.DuplicateTimeline` (API 2203), never on a timeline Josh has seen.
- **A dialog stops scripting** ("Update Available", "Render Cache Disabled"). Keep the cache on the media drive (`Media/Resolve Cache`) so a full internal disk never raises one. Relaunching with `open -g -a "DaVinci Resolve"` still brings its windows over whatever Josh is doing.
- **With the Project Manager open and no project loaded,** `LoadProject` returned None, and cancelling "Create New Project" quit Resolve (21 Oct).
- **`ImportMedia([path])`** works; the dictionary form returned None (21 Oct). A timeline name with colons fails `CreateEmptyTimeline` (22 Oct).
- **It crashed on:** `AppendToTimeline` with an imported SRT (17 Oct); adding Magic Mask to a Fusion composition by script (18 Oct); `comp.Render()` on a timeline clip's composition, after which nothing worked until a relaunch (14 Oct).

### After a sleep or a drop

After the Mac has slept with Resolve open, or the media drive has dropped and returned, quit Resolve (`resolve.Quit()`, API 1555) and relaunch it before any script, holding the video's lock, and tell Josh first if he is at the Mac. Then trust a render only by its own frames: `GetClipProperty("Online Status")` read "Online" while frames rendered "Media Offline" (22 and 26 Oct). A reload by script cleared it once and crashed Resolve another time; a relaunch cleared it both times.

## What scripting reaches

### Placing and changing items

- `MediaPool.AppendToTimeline` places a clip with a source range, track, record frame and media type (API 1900); for video `endFrame` is exclusive. A still ignores its range and comes in 125 frames long; marks on its media pool item give an exact length.
- **Audio source points are rounded to whole frames** on placement (100.4 became 100, 150.7 became 151, 21 Oct), up to 20 ms at 25 fps. Sub-frame edges go in through the timeline's file (below).
- **No call moves, trims, slips or rolls an item already placed:** `TimelineItem` has getters for start, end, offsets and source frames and no setters (API 2311 to 2336). So a structural change is a new placement, which `place.py` makes in seconds. `Timeline.DeleteClips(items, rippleDelete=True)` removes whole items and closes the gap (`remove_range.py`).
- `TimelineItem.SetProperties` sets Zoom, Pan, Tilt, crops and the rest of the inspector (21 Oct). One unit of `Pan` moves the picture by the clip's fitted width divided by the timeline's width in pixels: 3.16 px for a 3840 by 2160 camera in a 1080 by 1920 frame, 2.75 for a 3456 by 2234 screen recording; `Tilt` is in timeline pixels, up positive; `CropBottom` is in fitted pixels before zoom (22 Oct).
- `SetFades` takes fractional frames on audio and captions (21 Oct); `SetSpeed` and the retime process are properties of the item.

### The timeline's file reaches what the API does not

`Timeline.Export` as `.drt` writes a zip of Resolve's own XML description of the whole timeline, and `MediaPool.ImportTimelineFromFile` with `importSourceClips: False` brings it back, against the same media. Because the file is Resolve's complete description, anything it holds can be set by writing the file, even where no call exists. Read back exactly (26 Oct): a multicam segment's angle, sub-frame audio edges and fades, crossfades, every caption with its words' times, and every title with its inputs. An import makes a new timeline named after the file and ignores a `timelineName` option. The format can change between Resolve versions: after an update, round-trip a scratch timeline before trusting it. `Timeline.ImportIntoTimeline` takes AAF only and ignores the subtitle track.

### Multicam

- `MediaPool.CreateMulticamClip` with audio sync (`MulticamOptions`, API 1954) made the two-camera multicam in 9.5 s (26 Oct). With the lav included it became a black angle that every new segment defaulted to, so the multicam holds the two cameras only. Options added in 21 include `useFullClipExtents` and keeping each angle's audio tracks.
- **No call sets or reads inside a multicam:** `GetTimeline()` on it returns None, and nothing sets a segment's angle. The angle is a field in the timeline's file (`multicam.py`), and `TimelineItem.GetName()` reads it back as "<multicam> - <camera file name>" (26 Oct). Framing and speed set on a segment stay when its angle changes, so a switched segment shows the new camera at the old one's framing until it is reframed. Whether the interface's angle switch writes the same field is untested: read the timeline back after Josh switches one.
- `TimelineItem.FlattenMulticam(resolve.FLATTEN_MULTICAM_COPY_GRADE)` (API 2569) turns a segment into a plain clip of its active angle in the same place, with its source frames and speed, and resets its framing to zoom 1, pan 0, tilt 0 (26 Oct). It is one way, so flatten only a duplicate (`finish.py`) and set the framing again.
- `TimelineItem.PerformMulticamSmartSwitch(SmartSwitchSettings)` cuts a multicam item by itself, by who is speaking, lip movement and whether an angle is wide (API, p. 1045). Its settings are a minimum edit length, a change delay and how often to return to the wide angle. With one speaker those rules carry no editorial meaning, so the editor chooses angles; untested here.

### Transcription and captions

- `MediaPoolItem.TranscribeAudio` then `GetTranscription` (API 2059, 2098): segments and words with start and end on whole frames, `(...)` for a silence and for every um. `Timeline.GetMediaPoolItem` (API 2272) gives a timeline its own item, so the whole timeline transcribes on its own clock (21 Oct). 23 minutes of lav took 87.5 s (22 Oct). It misheard "Codex" as "Kodux" and once dropped a film's last sentence. It has no verbatim mode.
- `Timeline.CreateSubtitlesFromAudio(AutoCaptionSettings)` (API 2254) makes a subtitle track from the timeline's sound. Its only controls are language, a caption preset, characters per line (1 to 60), one or two lines, and a gap in frames: it breaks by count, not by phrase. The crew writes its own phrasing through the file instead (below).
- **Captions by file:** `pipeline/subtitles/write_caption_track.py` writes captions, with each word's frames, into a `.drt` holding the look's styled subtitle track, and the import brings them back. 66 captions went on in 0.9 s and every one read back (22 Oct). `SetName` on a caption returned False (21 Oct), so the file is the route.
- **The caption template.** A Fusion template dropped on a subtitle track styles every caption on it (pp. 1240, 1242); the look's is built from the stock Word Highlight one, which lights each word on its own time. With a template applied, a caption's own position is greyed out (17 Oct), so the track has one band height for the whole video, set in the template. Word times must be whole frames (a half frame made the pill stick); the pill drops when a word's time ends; a word starting more than 25 frames after the one before starts a new page (every gap over 25 split, none at 25 or under, 22 Oct); Size 0.117 draws 77.7 px Futura Bold. Only the enabled subtitle track burns in (p. 1248). 21 added fades and search and replace for subtitles in the inspector.

### Sync

`Timeline.AutoAlignClips` by waveform (API 2191) placed the wide camera's sound 23 ms from the cross-correlated offset (21 Oct). The multicam's own audio sync put the wide 0.57 frame from it (26 Oct). Both give one offset and no drift.

### Colour

- **Colour groups:** `TimelineItem.AssignToColorGroup`; a group's Pre-Clip and Post-Clip graphs (`ColorGroup.GetPreClipNodeGraph`). By script a group's graph takes only a LUT (`Graph.SetLUT`): `ApplyGradeFromDRX` returned False on a group's graph in every mode (22 Oct).
- **A CDL on an item's node:** `TimelineItem.SetCDL` with node index, slope, offset, power and saturation (API 2449), on plain clips and on multicam segments (26 Oct). Nothing reads a CDL back. So the camera's CDL goes on each of its clips, which sit in its group, where the colourist's hand work on the group reaches every clip of that camera.
- **No call adds a node or an effect** (CineFocus, a curve, a qualifier). `Graph` can count nodes, read their tools and labels, enable or disable them, set a LUT and apply a still's grade (`ApplyGradeFromDRX`, on a clip's graph).
- **Copying grades:** `TimelineItem.CopyGrades` (API 2473) copied a clip's whole node stack, CineFocus and Magic Mask included, to the same shot on another timeline (22 Oct). Gallery stills and PowerGrade albums can be imported and exported by script (`GalleryStillAlbum`).
- **Magic Mask by script:** `TimelineItem.CreateMagicMask(mode)` tracks a magic mask forward, backward or both ways (`'F'`, `'B'`, `'BI'`), and `RegenerateMagicMask` redoes it (API 2494). The stub does not say which node or which strokes it uses; untested here. It may replace the interface step that tracks the mask under the wide camera's blur: test it on a duplicate with a node that already holds a Magic Mask.
- **Others in reach:** `SmartReframe`, `Stabilize`, `ResetAllNodeColors`, grade versions (`AddVersion`, `LoadVersionByName`).

### Titles

`Timeline.InsertFusionTitleIntoTimeline("Text+")` (API 2251) inserts between the marks, at the playhead, on the track of the last clip appended, as a ripple insert on every unlocked track; it returns None when that track is locked. So on a timeline that already has picture: lock every other track, append one frame of any clip on V4 after the titles, then for each title in record order set the marks and playhead, insert Text+, `ImportFusionComp` the look's template onto the item and set its inputs, then delete the one frame and unlock (`graphic.py`, 26 Oct). V1 to V3 stay untouched. Inputs read back from the item; pill ranges (`[[ ]]`) only from the file. A word change on the item took 0.01 s. Inserting a template by its own name returned None; whether installing it as an Edit page title fixes that is untested. Text+ Size 0.1506 draws 100 px Futura (22 Oct). 21 added OGraf HTML graphics and Lottie on the Edit page; an OGraf graphic takes a file, a trim, a hold and play frames, and no per-frame data (pp. 2376 to 2378).

### Sound

`TimelineItem.AddTransition` adds Resolve's "Cross Fade 0 dB" at a whole frame; its sub-frame start and length go in through the file (`tools/audio.md`). Voice Isolation is settable per item and per track (`SetVoiceIsolationState`, amount 0 to 100). `Timeline.NormalizeAudioLevel` changes gain only (`tools/audio.md`, "Level"). `Project.ApplyFairlightPresetToCurrentTimeline(name)` applies a stored Fairlight preset (`Resolve.GetFairlightPresets` lists them); the Presets Library holds EQ, dynamics, plug-in, track and bus presets (p. 3820). Whether a preset applied by script carries a bus limiter is untested.

## Colour management

The project: DaVinci YRGB Color Managed, DaVinci Wide Gamut with DaVinci Intermediate as the timeline space, Rec.709 Gamma 2.4 out, DaVinci tone mapping (pp. 235 to 241); `create_project.py` sets it and reads it back. Each camera's input colour space is set by hand and read back: the DJI files carry Rec.709 tags and Resolve took them as Rec.709 (15 Oct); `"Nikon N-Log"` and `"DJI D-Gamut/D-Log"` took (21 Oct). The round trip dims anything already Rec.709 (a graphic's white 255 came out 188) until "Use Inverse DRT for SDR to HDR Conversion" is on, which keeps Rec.709 clips exact (p. 241; 17 Oct). Never change the timeline colour space once grading has started.

**Fusion works in linear light,** so a colour typed into a template comes out wrong: page grey 23 came out 70, and the orange of the pill came out (255, 139, 0). A Color Space Transform at the end of each graph (Rec.709 colour and gamma in, DaVinci Wide Gamut linear out, no tone mapping) brought a 162-colour chart back with no error (22 Oct). The caption template stores its colours as linear values for the same reason. Load photos at float depth; name photo files without bare numbers, or the Loader reads `00.jpeg`, `01.jpeg` as one sequence.

## Changing a placed timeline

Every change ends with `finish.py` on the changed cut (`roles/director.md`, "Applying a note").

- **Through the list and a re-place,** on a new name: a camera switch, a recut, anything structural.
- **In place, on a duplicate** of the cut timeline under a new name, which keeps every clip and the caption track (22 Oct): a title's words (set the input on its item, `graphic.py`'s function); a run of whole clips removed (`pipeline/resolve/remove_range.py`, a ripple delete between two existing cuts: everything later moved up exactly, captions included, and a graded clip kept its grade and mask; it refuses when anything crosses an edge, and the sound join it leaves is a one-frame fade each side that nobody has listened to); a file swapped behind a clip at the same timing (`pipeline/resolve/replace_media.py`, this timeline only; `MediaPoolItem.ReplaceClip` changes every timeline that uses the item, Josh's included, so never use it); a reframe (`SetProperties`). After any of these, the editor brings the change into the list by hand (SKILL.md, "A change made in Resolve comes back into the list by hand"), or the next re-finish or placement undoes it.
- **A regrade** changes the list's `cameras` and the finish timeline only.
- **After lock,** `pipeline/resolve/copy_grades.py` brings per-shot Color page work from the old finish timeline to the new one, matching items by file, source start and length, and lists what it could not match (22 Oct).

`remove_range.py` and `replace_media.py` were tested on plain clips, before the multicam and the one-track dialogue: read back after each until one has run on a cut timeline. These scripts read the project's name and the look from a small `edit/edit.json` in the video's folder that ingest writes; every editorial value lives in the edit list.

## Rendering

Render a finish timeline, never a cut timeline, which has no grade and still holds a multicam (`render_timeline.py` refuses it). `pipeline/resolve/render_timeline.py PROJECT TIMELINE OUTPUT --preset phone|post|master|still [--subtitles] [--range IN OUT] [--load-render-preset NAME]` renders and waits: it returns when the job is complete, its marks cleared and the job deleted, so the Resolve lock is held for the whole render. It retries `StartRendering` for up to 30 s (Resolve refuses it now and then and accepts it seconds later), counts a render only when the file has a video stream, refuses an existing file, and exits 1 on a failure. NAME is the loudness preset `loudness.py` wrote, loaded first.

- `phone`: H.264 sized to a 28 MB budget, the file Josh watches; too low a rate to post.
- `post`: H.264 at 8 Mbit/s for 1080 by 1920, within X's guidance, the file he posts.
- `master`: ProRes 422 HQ with 24-bit PCM, for the archive.
- `still`: one lossless 16-bit PNG of a one-frame range.

Resolve's AAC is fixed at 320 kbit/s (21 Oct). An 81 s master took about 4 minutes; CineFocus roughly doubled it, and the render cache did not help (18 Oct). 21 can render in the background.

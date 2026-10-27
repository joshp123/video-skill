<!-- Resolve, graphics and caption fault fixes written by AI on 2026-10-22 by GPT-6. -->
<!-- Cut, dialogue and word-timing faults updated by AI on 2026-10-22 by GPT-6 Astra. -->
<!-- Written by AI on 2026-10-21 by Claude Fable 5.1; run order updated 22 Oct by GPT-6.1 Sol for the native swaps and by Claude Fable 5.1 after the end-to-end run. -->

# The shared pipeline

The repeatable, mechanical steps between a video's edit data and its finished file. Every decision lives in the video's `edit/edit.json` (the format: `edit-format.md`); these steps execute it and write generated files under the video's `build/`, or explicit output paths for scratch runs. A change of mind is written into the data and applied to the timeline in place where Resolve's scripting allows; the timeline is rebuilt only when the structure changes (`edit-format.md`, first paragraph). Nothing here knows one video: anything the steps need about a recording, a camera, a project or a look comes from the edit data or the look module.

The Python environment is `pipeline/devenv.nix` (Python 3.12 with numpy, and ffmpeg): from `pipeline`, `devenv shell -- sh -c 'cd .. && python pipeline/cut/build_cutlist.py EDIT'`, or enter `devenv shell` there and come back to `Media/Edits` for the commands below. Leave `TMPDIR` alone when running `devenv`: a temp folder on the SSD, whose path has spaces, breaks its launcher. `EDIT` is the video's folder, for example `2026-10-30-slug`. The order below is the order the steps read each other: cut list, dialogue, word timing, graphics, captions, timeline, renders. Run Resolve scripts with `/usr/bin/python3`, even when the devenv’s binaries are first on `PATH`. Every Resolve script takes `resolve` from its namespace when run through the MCP, and otherwise connects itself through Resolve's external scripting (the three variables in step 6).

Praat through `parselmouth` is unavailable in this environment: `python312Packages.praat-parselmouth` 0.4.7 compiled on 22 Oct, but its bundled `test_LPC.praat` crashed with exit 133 during the Nix build. The dependency was left out.

## 1. The cut list

```sh
python pipeline/cut/build_cutlist.py EDIT --output build/cutlist.json
```

Writes the `--output` path (default `EDIT/build/cutlist.json`) and refuses to overwrite it. Pass that path as `--cutlist` to dialogue and word timing; downstream graphics and timeline steps currently read `build/cutlist.json`. `--previous` names an earlier aligned cut list (default `EDIT/build/cutlist.json`): when `audio_clips` are unchanged, the rebuild carries matching words’ aligned times and scores forward. The cut fingerprint excludes camera grades, framing and mixer-only fields; it hashes cut inputs, not the raw edit file. The native and Remotion graphics checks still compare the raw file; those checks must adopt this fingerprint before using the new cut lists (faults 90 and 107, owned by the separate graphics pass).

The output contains: every picture clip (camera, source and record frames, framing, punch-in), every audio segment at exact sample times, every kept word with its times, every graphic with its anchors resolved to frames, and a report. Read the report before anything else: `unresolved_anchors` (the script exits with status 2), `boundary_warnings` (no silence, a rise over 10 dB in the 30 ms after an out-point, or no final 80 ms silence), `pause_shortfalls` (only pauses requiring added film frames), `pause_warnings` (a pause edge over 6 dB above the measured room), `picture_shortfalls` (the source ran out under the ending), `removed_pauses`, `removed_words`, `jump_cuts`, `face_touches`, `graphic_snaps`. `built_as_written` is true only when nothing in it needs a decision. With no `media.face_touch` key it prints `no face-touch scans in media`. Compare each run’s edge words and words beside a gap over 0.45 s with Resolve’s transcript; measure on the lav and `retime` any disagreement over 0.3 s. The builder checks the dialogue named by the existing `build/dialogue-report.json`, or `--dialogue PATH`, against the new sample count; `dialogue_length_mismatch` says to rebuild dialogue before alignment, graphics or a timeline.

## 2. The dialogue

```sh
python pipeline/audio/build_dialogue.py EDIT --cutlist build/cutlist.json --output build/dialogue-vN.wav
```

Cuts the lav at the cut list's samples, lays room tone from `media.lav.room_tone_s` under every gap, applies the `dialogue_patches` and `dialogue_inserts`, cleans, and levels to -14 LUFS with true peak at most -1 dBTP. Writes the file named by `--output` (default `build/dialogue.wav`), the intermediate files under `audio/` beside the output, and `dialogue-report.json` beside it (loudness, true peak, the level either side of every cut). Give each version its own file: a timeline Josh has seen keeps its own sound. `--cutlist` defaults to `build/cutlist.json`. The report checks the selected room tone in 5 ms windows after high-passing at 1 and 4 kHz; `room_tone_checks[].suspect_windows` lists windows over 6 dB above each band’s own median. A low full-band floor alone does not establish clean tone. Inspect joins with the shared tool:

```sh
python pipeline/audio/joins.py EDIT build/dialogue-vN.wav --cutlist build/cutlist.json --output build/joins-vN
```

Each PNG shows the source either side of the cut and the built join, with a waveform, spectral trace and marked in/out edges. `--join N` selects one join (from 1).

## 3. The word timing

```sh
/usr/bin/python3 -X utf8 -B pipeline/resolve/align_words.py EDIT build/dialogue-vN.wav --cutlist build/cutlist.json      # with Resolve's scripting environment set (step 6), the project open
```

Resolve transcribes the finished dialogue (`TranscribeAudio`, from the Edit page; it imports the file into the `Generated` bin if absent). It writes each kept word’s aligned seconds and frames and its score into the output cut list; without `--output` it updates the input cut list. `--output` writes a separate aligned copy and refuses an existing output; `--report` defaults to `alignment-report.json` beside it. A dropped first or last word uses its transcript times, scored 0 and reported. A dropped interior word is interpolated between neighbours; if they leave no positive interval, it uses transcript times, also scored 0. Zero-length Resolve words are rejected as partners, replaced from the transcript and reported; a final nonpositive interval stops the step. Starts over 0.4 s from transcript time are scored 0 and listed under `pairings_over_400ms`; every edge over 0.2 s is also reported. Read that report before using the timing.

After alignment the step re-resolves graphic edges and cues on aligned frames, snaps edges to picture cuts again and recalculates holds and film length. If the dialogue’s sample count differs from the cut before transcription, it stops with a dialogue-rebuild instruction. If aligned edges change the film length, it writes the aligned cut list and exits with status 2, reporting the required dialogue rebuild before graphics or a timeline. Everything anchored to speech reads the aligned frames. A cut-list rebuild preserves them when `audio_clips` are unchanged; changed audio requires dialogue and timing again. For isolated transcription, `--bin-name NAME` selects the import bin and `--transcribe-project NAME` explicitly selects the required open project without switching projects; both default to the normal video setup.

## 4. The graphics

Two routes. The terminal kinds (`terminal`, the agent box, `keyline`) render in Remotion as transparent clips:

```sh
cd pipeline/graphics
devenv shell -- node render-clips.mjs ../../EDIT --out=build/graphics-vN     # --only=ID for one graphic
devenv shell -- node render-clips.mjs ../../EDIT --only=ID --stills --frame=FILM_FRAME
```

Builds the render data from the cut list and the look, then renders each terminal graphic as its own ProRes 4444 clip with transparency into the output folder, with `manifest.json` (each clip's first film frame and length) and `render-data.json` beside them. It refuses to overwrite a clip or a manifest, so each version renders into its own folder. Stills go to `EDIT/build/stills/`. The bundle is reused from `Media/Edits/.cache/remotion-bundle/`. The tool's output is captured first, at the panel's column count, so the tool wraps its own lines:

```sh
python3 pipeline/graphics/capture-terminal.py --columns N --output ../../EDIT/graphics/content/NAME.txt -- COMMAND ARGS
```

The other kinds (`photo-grid`, `photo-panel`, a title, `closing`) are built in Resolve as Fusion compositions, each in its own small timeline, from the cut list, the look (`looks/<name>/look.json`), the photo lists and `words.md` (with Resolve's external scripting environment set, the project open):

```sh
/usr/bin/python3 -B pipeline/resolve/build_graphics.py EDIT --output build/graphics-native-vN/manifest.json  # optional --timeline-prefix PREFIX names new timelines and their bin
/usr/bin/python3 -B pipeline/resolve/change_graphic_words.py EDIT ID # re-reads words.md and re-applies the title band from the cut list; rebuild the cut list after changing the band in edit.json
```

Writes the `--output` manifest (default `build/graphics-native/manifest.json`; relative to EDIT or absolute), refusing to overwrite it before changing Resolve (each graphic's timeline name, first film frame, length, and which words.md line each slot used: final, proposed or placeholder). A title line wider than its margins is refused; closing parts warn with their text when they exceed margins or cross the look's button safe area, and ` / ` forces a break in any closing part. A photo grid uses no more columns than photos. The builder reads back the created timeline names and checks that the project saved before publishing its manifest. A build of all of where-was-i's five took about 7 s; a word change about 2 s with a one-frame render (tested 22 Oct).

Run `node pipeline/graphics/scan-flashes.mjs FILE.mov` on a Resolve render directly; its timecode track needs no remux.

## 5. The captions

```sh
python3 pipeline/subtitles/build_captions.py EDIT --output build/captions-vN.json
```

Writes each line's `subtitles` (the model's phrases, as written in the edit data: one phrase per caption, broken where his phrasing breaks) to `--output` (default `build/captions.json`, refuses overwrite), timed on Resolve's word timings in the cut list (step 3): each caption's start and end in seconds from the timeline's first frame, and each displayed word's start and end, so Resolve can light the word being spoken. A phrase initially holds five frames after its last word, stops when the next phrase starts, and stops at the first picture cut after a sentence ends. Caption edges within two frames of a visible camera or graphic change snap to it; one- and two-frame blanks close. Captions hold for at least 0.7 s by extending into a blank or joining a neighbour; a one-word remainder joins its neighbour. The first word lights at the caption start, the last for at least three frames; each light lasts until the next starts (the last until the caption ends), and word starts are at most one second apart so Resolve does not split the caption into pages. Width warnings name the caption and row and include pill padding from `look.json` (`subtitles.activeWord.padding`; otherwise 36 px per side). Rows must fit the look's safe area, 820 px centred at this 1080 px width; warnings require the editor to rephrase or choose a smaller type size in the look. No caption shows while a graphic with `hides_subtitles` is up. A displayed word gets the time of the spoken word under the same characters, so a spelling that shows one spoken word as two ("it's" as "this is") splits that word's time between them. The professional-practice audit of 22 Oct is why the phrasing is the model's and not Resolve's: Resolve's own line breaks end a caption mid-phrase in 24 of 54 cases.

Graded clips across the caption step are checked by node count only; that check does not compare grade values or masks.

The captions go onto the timeline after it is built (step 6), by file, with no interface step:

```python
ns = {"resolve": resolve, "EDIT_FOLDER": "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/EDIT", "TIMELINE_NAME": "cut vN"}
exec(open("/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline/resolve/add_captions.py").read(), ns)
result = ns["result"]
```

Resolve's scripting cannot create or edit a caption (21.1: `SetName` on a caption returns False and nothing inserts a subtitle file), but it exports and imports timelines as `.drt` files, and that file carries the subtitle track whole: each caption's text, frames and per-word times, and the Fusion template that styles the track. So `add_captions.py` exports the timeline to `build/caption-tracks/<timeline>/exported.drt`, `pipeline/subtitles/write_caption_track.py` writes the look's styled track (`looks/<look>/resolve/caption-track.drt`, exported once from Resolve after the template was dropped on a track) holding `captions.json` into that file, and the script imports the file back as the timeline, named as before, with the original deleted once the checks pass: every caption's text and frames read back, and every video and audio item keeps its name, place, length, media pool item and grade node count. `OUTPUT_NAME` keeps both timelines under different names, for a note on a timeline Josh has seen (apply it to a duplicate). Tested 22 Oct in a scratch timeline: where-was-i's 66 captions and 261 words went on in 0.9 s, the camera clip stayed on the same media pool item with nothing duplicated, and rendered frames showed the look's pill on the word being spoken (`.cache/captions-native/`). Word times are written as whole frames because Resolve never writes anything finer, and an odd half-frame value made the template's highlight stick and spill words onto a second page (same test). Untested so far: a clip's own grade and masks across the export and import (the check counts each clip's nodes), and timelines at other frame rates than 25.

## 6. The timeline

With the video's project open in Resolve (`resolve_project` in the edit data), either through the Resolve MCP's `run_script_unsafe`, which defines `resolve`, or from a shell through Resolve's own external scripting (tested 21 and 22 Oct; it needs Resolve running with a project open, and it worked all night while the MCP's script runner returned nothing):

```sh
RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting" \
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so" \
PYTHONPATH="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules" \
/usr/bin/python3 -B -c 'import DaVinciResolveScript as d; resolve = d.scriptapp("Resolve"); ...the lines below...'
```

Use `/usr/bin/python3 -B` for every Resolve script and `PYTHONUTF8=1` when the shell locale is ASCII. Successful standalone scripts flush stdout and exit without running the crashing Fusion destructor; execution inside MCP returns the result normally.

Then:

```python
ns = {"resolve": resolve,
      "EDIT_FOLDER": "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/EDIT",
      "TIMELINE_NAME": "cut vN", "GRAPHICS_DIR": "build/graphics-vN", "DIALOGUE_FILE": "build/dialogue-vN.wav",
      "NATIVE_MANIFEST": "build/graphics-native/manifest.json"}
exec(open("/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline/resolve/build_finish_timeline.py").read(), ns)
result = ns["result"]
```

Makes a new timeline, and only a new one: an existing name is refused, so a timeline Josh has seen is never changed. It finds each camera's file in the media pool (importing it into a `Cameras` bin if absent) and sets its input colour space from `media.cameras.<name>.log`; gives the timeline its own colour settings, copied from the project, with the inverse DRT on so the Rec.709 graphics come through exactly; places the cameras on V1 as the cut list says, framed from `media.cameras.<name>.framing` or, under a panel layout, from that layout's `framings`, and assigns each clip to its camera's colour group (`colour_group`, each distinct missing group created once before the timeline); places each graphic on the lowest free video track above the cameras, in cut-list order (a rendered terminal clip from `GRAPHICS_DIR`, a built Fusion timeline from the native manifest, or both for a title over a terminal), so overlapping graphics stack; and puts the dialogue on A1. `CAMERAS_ONLY: True` (CLI `--cameras-only`) places cameras and dialogue without requiring graphic manifests, retaining panel framing for a framing check. `result` lists every placed clip with its track, record frame, length, source frame, framing and group: compare it with the cut list before trusting the timeline.

## 6b. The camera grade

```python
ns = {"resolve": resolve, "EDIT_FOLDER": "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/EDIT", "TIMELINE_NAME": "cut vN"}
exec(open("/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline/resolve/grade_cameras.py").read(), ns)
result = ns["result"]
```

Each camera's grade is primaries in the edit data, `media.cameras.<name>.grade`: an ASC CDL (slope, offset, power per channel, and saturation), no LUT. The colourist decides the values on real frames of both cameras at the same moment and writes them into the data; the timeline builder reads them directly from `edit/edit.json`, even when the cut list predates the grade, and applies them to every clip of the camera on each build (step 6), and this script applies them to an existing timeline when the values change, in about a second, so a change of grade needs no rebuild. Resolve's scripting cannot grade a colour group (its `ApplyGradeFromDRX` returns False on a group's graph; only a LUT can be set there) and cannot add nodes, so the grade sits on each clip's one node, which is also where professional colourists balance shots (the Darren Mostyn corpus: the input transform in the group, the balance in Clip). Tested 22 Oct on a scratch timeline with both cameras: both graded, the nodes read back as Primary Balance and Saturation, a second run with new values replaced the first, rendered frames changed as set (`.cache/captions-native/gc-strip.png`). Clip-level effects (CineFocus, Magic Mask) still need the Color page.

## 7. The master

```python
ns = {"resolve": resolve, "PROJECT_NAME": "the Resolve project name",
      "TIMELINE_NAME": "cut vN", "PRESET": "master", "SUBTITLES": True,
      "OUTPUT_FILE": "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/EDIT/build/cut-vN-master.mov"}
exec(open("/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline/resolve/render_timeline.py").read(), ns)
job = ns["result"]          # then poll: ns = {"resolve": resolve, "PROJECT_NAME": ns["PROJECT_NAME"], "JOB_ID": job}; exec(...); ns["result"]
```

The master explicitly sets 48 kHz, 24-bit linear PCM (`lpcm`) audio. Renders a `.mov` of the whole timeline at its own resolution, with the enabled subtitle track burnt in when `SUBTITLES` is true; `RANGE: (in, out)` renders a range in timeline-relative frames, both ends included. It starts the job and returns its id; a second call with `JOB_ID` returns the job's status and, on completion, reads its settings, clears that timeline's in/out marks and deletes only that job. Refuses to overwrite. `PRESET: "still"` with a one-frame inclusive `RANGE` writes one lossless 16-bit RGB PNG (Resolve appends its frame number to the requested `.png` stem), with no audio; check the returned job settings for the filename.

## 8. The phone file

Use the same render step with `PRESET: "phone"` and an `.mp4` output. Resolve renders H.264 High with multi-pass encoding, network optimisation, AAC and Rec.709 tags. The video bitrate is calculated from a 28 MB budget and the timeline's duration, allowing for Resolve's fixed 320 kbit/s AAC. Measure the finished file with `ffprobe` and `ffmpeg -af ebur128=peak=true`; the budget is an encoder target, not an exact file size.

Use `PRESET: "post"` with an `.mp4` path for the file to post: H.264 High, multi-pass, 8 Mbit/s video at 1080×1920, AAC at 48 kHz and Rec.709 tags. The fixed 8 Mbit/s target is within [X Media Studio's 5–8 Mbit/s guidance](https://help.x.com/en/using-x/media-studio-faqs) and X's 6–10 Mbit/s 1080p ad range; it gives fades more bitrate than the 28 MB review copy.

## Ingest

With Resolve's external scripting environment set, pass the required project name as the first argument (or `PROJECT_NAME` in the script namespace). Scripts with `EDIT_FOLDER` read `resolve_project` from `edit/edit.json`. The video's project comes first. `create_project.py` makes it current, closing the open project:

```sh
/usr/bin/python3 -B pipeline/resolve/create_project.py PROJECT_NAME EDIT   # creates the project named in the edit data if absent: colour management (DaVinci YRGB Color Managed, DaVinci WG/Intermediate, Rec.709 Gamma 2.4 out, DaVinci DRTs, inverse DRT on), the edit data's resolution and frame rate, scale-to-crop, one colour group per camera, SSD cache at `Media/Resolve Cache` set and read back, playback frame rate read after media import and required to match the timeline frame rate, the cameras and the lav imported into a Source bin with their input colour spaces set and read back; refuses a project that already has timelines (tested 22 Oct, 10 of 10 settings)
/usr/bin/python3 pipeline/ingest/clone.py PROJECT_NAME SOURCE_FOLDER DESTINATION_FOLDER
/usr/bin/python3 pipeline/ingest/transcribe.py PROJECT_NAME MEDIA_FILE OUT_PREFIX --offset OFFSET_SECONDS
/usr/bin/python3 pipeline/ingest/sync.py PROJECT_NAME FIRST_CAMERA SECOND_CAMERA
# To record a measured offset:
/usr/bin/python3 pipeline/ingest/sync.py PROJECT_NAME FIRST_CAMERA SECOND_CAMERA --write EDIT/edit/edit.json --name cameras.wide
```

Clone preserves the folder name and verifies with SHA-256. Transcription writes word-timed JSON and timed text. Sync creates a scratch timeline, aligns by waveform, reads the offset, and deletes that timeline. Without `--write`, it only prints the result.

## Applying a note without a rebuild

The timeline that exists is the edit. A note is applied in place wherever the scripting allows, on a duplicate of the timeline Josh saw (`Timeline.DuplicateTimeline` keeps grades, masks and captions; Resolve's live save stores every change within a second), and the same change is written into the edit data so a rebuild reproduces it. A change to the structure (words added, lines reordered, a shot recut) is a rebuild: steps 1 to 6 again, then the grade copy and the caption pass.

```sh
/usr/bin/python3 -B pipeline/resolve/remove_range.py EDIT TIMELINE IN_FRAME OUT_FRAME    # a whole line out
/usr/bin/python3 -B pipeline/resolve/replace_media.py EDIT TIMELINE OLD_FILE NEW_FILE    # a new dialogue file of the same timing, or a re-rendered terminal clip
/usr/bin/python3 -B pipeline/resolve/change_graphic_words.py EDIT ID                     # a Fusion graphic's words from words.md and its title band from the cut list
/usr/bin/python3 -B pipeline/resolve/copy_grades.py EDIT FROM_TIMELINE TO_TIMELINE       # after a rebuild
```

`remove_range.py` takes timeline-relative frames with an exclusive out frame, refuses without changing anything if any video, audio or subtitle item crosses either edge (so a line under a graphic that also covers its neighbours needs a rebuild), and otherwise ripple-deletes the enclosed items and sets one-frame fades on the two A1 pieces meeting at the join, reading both back; the model takes the same words out of `lines`. `replace_media.py` imports the new file as its own media pool item and, on the named timeline only, deletes each use of the old file without ripple and appends the new one at the same record frame, source start and length, then checks the item count and every record range; other timelines keep the old media. `copy_grades.py` matches each video item on the target by media file, source start frame and length, copies the source item's grade (nodes, masks, LUTs) and lists the unmatched items, which are new shots or recuts for the Color page. Tested 22 Oct on the first video (`.cache/native-swaps/`): a removed line moved every later item on every track by exactly its length with the clip-level grade intact; the media swap left 85 items at their frames and other timelines untouched; the grade copy matched 30 of 30 clips.

## Where things go

Everything under the video's `build/` is generated and may be rebuilt; `versions/` holds what Josh saw and is never overwritten. Scratch and caches go under `Media/Edits/.cache/`, never on the internal disk. Its dated test folders (`custom-code-review`, `verify-claims`, `native-swaps`, `native-graphics`, `native-graphics-test`, `face-touch-test`, `caption-steps`, `resolve-proof`) are the evidence the video skill cites for what was tested on 21 and 22 Oct 2026: they stay; the rest may be rebuilt. Use `trash`, never `rm`.

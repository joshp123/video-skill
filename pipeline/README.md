<!-- Written by AI on 2026.11.17 by model claude opus 5.5, for the rebuild on DaVinci Resolve Studio 21.2. Every time below was measured on Josh's MacBook (M4 Pro) on 17 and 18 Nov 2026, on the codex-switch material (two 3840 by 2160 cameras at 25 fps, the lav, a 95 s vertical short). The evidence is private/research/2026-11-17/rebuild-tooling.md. -->

# The pipeline

Commands that turn the model's decisions into a finished cut in DaVinci Resolve, and check it. The model decides every editorial value; these commands find, place, measure, render and read back, and decide nothing.

The flow for a video:

1. `ingest.py` takes the session's camera files (or cards) to a checked session: the lav on the front camera's clock, the verbatim transcript, face-touch scans, the video's plan header and its Resolve project (`project.py`), and lists what needs the model.
2. The model writes one plan for the whole video: which of his words are kept, in what order, the cameras, the captions, the titles and panels (the format is in `b/assemble.py`'s help).
3. `cut.py` takes the plan to a checked render in one call: it runs `assemble.py`, `place.py`, `finish.py`, `render.py`, the join check and the gate, and prints what needs the model.
4. The model reads that, looks where it must (`look.py`), changes the plan, and runs `cut.py` again.
5. A note on a cut that exists, from Josh or the crew, goes on with `note.py`, in place, in seconds.

Every command prints JSON and exits 0 only when nothing needs attention. Times below are on this MacBook and scale with the machine's other load: at a load average of 20 to 40 (other sessions' jobs) passes took two to three times as long, so say the load beside any time you report. Run the Resolve commands with `/usr/bin/python3 -B` from `pipeline/b` (they set Resolve's scripting variables themselves); `qc.py` needs the pipeline devenv's Python (`cd pipeline && devenv shell -- python3 ...`; `cut.py` finds it itself). Paths in an edit list or a plan are relative to its own folder. Caches, scratch timelines' files and renders go on the media drive, under `Media/Edits/.cache/` and the video's folder (`session.CACHE`); nothing goes on the internal disk.

## Resolve runs windowless: `b/session.py`

Every Resolve command calls `session.connect(project)`. If Resolve is not running it starts it with `-nogui` from the shell: no window opens and nothing takes the foreground (tested 17 Nov on this MacBook). Scripting answers 9 to 40 s after launch. `connect` then opens the project the edit list names.

```sh
/usr/bin/python3 -B session.py start | stop | status
```

`stop` saves and quits (5 to 40 s; it repeats `Quit()` every 20 s, because Resolve sometimes ignores the first). `status` says whether Resolve runs windowless, which project is open, and lists any dialog.

**Dialogs.** A windowless Resolve still raises modal dialogs, and they land on Josh's screen or on another desktop Space. `SaveProject()` while the unnamed "Untitled Project" is current (right after launch, or after `CloseProject`) opens a "Save Current Project" dialog and the call never returns (proven on the Mac mini, 17 Nov; it happened three times on this MacBook before it was found). So the tooling never saves the unnamed project (`session.save` refuses it), never closes a project, and after every launch, project load, save, render and quit lists every Resolve window on every Space (`b/resolve_windows.swift`) and stops with the window's title if one is a dialog. If a command stops with "Resolve shows a dialog", nothing else may call Resolve until the dialog is cancelled and the call that raised it is known. Window titles need the terminal to hold Screen Recording permission; without it, the window's layer still gives the dialog away.

Resolve's "Align audio edits to frame boundaries" preference must be off (it is): with it on, the sub-frame sound calls return True and round to whole frames. `sound.py` refuses to place sound while it is on.

## `b/ingest.py start --session DIR --video DIR --source PATH ...`, `status --session DIR [--wait S]`, `header`

Run with the pipeline devenv's Python (`cd pipeline && devenv shell -- python3 b/ingest.py ...`). `start` writes the request to `SESSION/ingest/request.json` and runs the work detached; `status` prints each step with its time, every measured fact with how it was measured, and `needs_the_model`, and `--wait` (at most 110 s) returns as soon as the work finishes. Exit 0 once all is done and nothing failed. A `--source` is a camera file, the screen recording, or a card's folder; the files are told apart by their own tags (the Nikon's brand `niko` is the front camera and the master clock, an encoder `DJI ...` is the wide camera and carries the lav, a ReplayKit author tag is the screen recording; `.LRF` proxies are copied and hashed only).

In order, the slow parts alongside:
- A card's clips are copied with `ditto` into `Media/Input Media/<camera>/<session>/` before anything reads them; then every file is hashed (SHA-256) in the background, a copy against its card and a file already in `Input Media` against the session's `metadata/copy-manifest.json` when there is one. Copying from a card is untested.
- Both cameras' whole files go to frames at 5 a second (640 px) and through `skill/scripts/face_touch.swift` (compiled into `Media/Edits/.cache/bin/`), in the background.
- The lav and the front camera's own sound are extracted at 48 kHz; the lav's offset (front time = lav time + offset) is found by cross-correlating the two: once on their envelopes over the whole take, then at five 20 s windows at 48 kHz to a fraction of a sample. The median is used, and the straight-line drift over the take is reported; past half a frame it is a question for the model. On 12 October the five points ran 36.7370 to 36.7468 s (October's hand measurement: 36.7361 to 36.7489).
- The lav is padded onto the front clock to the front file's length, sample for sample (`SESSION/audio/lav-front-48k.wav`, 24-bit), with a 16 kHz mono copy; given October's offset this gives a file bit-identical to October's `dji_0597_aligned_to_nikon_48k_stereo.wav`. The verbatim transcript starts at once, on the lav as recorded with the offset added to its times (as October's was), into `SESSION/transcript/lav-verbatim-front.json`; when it ends, its reach and every gap over 10 s are reported.
- The wide camera's picture offset is measured picture against picture: his face box's centre and height on both cameras at 25 fps in five 20 s windows (each frame timed by ffmpeg's `showinfo`, not by the seek), smoothed over 5 frames, its frame-to-frame motion cross-correlated in 2 ms steps. **It is not good enough to set the offset to a frame.** On 12 October the windows fell in two clusters 80 ms apart (36.736 to 36.742 s and 36.816 to 36.824 s, correlations 0.52 to 0.71; an earlier trial of seven windows gave the same two and one at 36.776), and October established 36.777 s from the clap and his lips. So when the windows disagree by over 20 ms, the header carries the lav's offset and `needs_the_model` asks for the picture offset by eye, with the windows as evidence. The clap, seen by both cameras as a burst of motion, is the better instrument to build next.
- Room tone: the quietest 3 s inside the lav's span with no 5 ms window over 6 dB above its band's median after high-passing at 1 and 4 kHz (October's check). On 12 October it chose 125.01 to 128.01 s, in the same pause October chose by hand (121.24 to 124.24).
- Stills of both cameras at 10, 50 and 90% with their luma spread, the Nikon's picture control by ExifTool (the Pocket's profile cannot be read from its file), and the screen recording's frame times.
- The video folder's `plan.json` gets the header: `resolve_project` ("DATE SLUG" from `--date` and `--slug`, or the folders' names), `look`, `fps`, `format`, `multicam`, `cameras` (file, log, group, the look's `colour.feel` as grade, `picture_offset_s`, `reference` on the front), `sound` (lav, room tone, the usual fades) and `transcript`; nothing editorial. If a `plan.json` exists the header goes to `plan.header.json` instead. A measured section is appended to the session's `inventory.md`. Then `project.py` runs on the header (skip with `--no-project`) and its multicam offsets are compared with the measured picture offset.

**On 12 October** (the 23-minute session, 21 GB, load average 3.6 to 5.5): 5 min 40 s from `start` to finished. Probe 0.5 s; hashes of all four files 13.3 s, all matching October's manifest; the lav's offset 13.5 s (36.741996 s; October's 36.737125 s is its start-of-take value, and the five points ran 36.7370 to 36.7468, the same 12 ms drift October measured); padding 1.2 s (the new lav is October's moved by exactly 235 samples, 4.875 ms, at every point checked); room tone 0.5 s (125.1 to 128.1 s, in the pause October chose by hand, 121.24 to 124.24); stills and profiles 6 s (N-Log read from the Nikon); the plan header at 0.02 s; `project.py` 22.5 s (multicam wide at 919 frames, as October's); the transcript 4 min 29 s (3,620 words against October's corrected 3,623: the differences are 26 names the model corrects, such as "codecs" for Codex, and one stretch at 924.5 s that the recogniser dropped after a pause, which October transcribed again and ingest lists as a gap); the face scans 5 min 25 s and 5 min 40 s, alongside.

`ingest.py header --video DIR --slug NAME (--like PLAN | --session DIR) [--date] [--look]` starts another video from a session already ingested: it copies the header keys of an earlier video's plan (which carries what the model corrected: the transcript copy with names fixed, a settled picture offset, the cameras' grades) or of the session's own `plan-header.json` (ingest writes it into the session folder, its paths relative to that folder), makes every path relative to the new folder and names the project "DATE SLUG". Then run `project.py` on it. A session ingested before `ingest.py` gets its `plan-header.json` once, from a plan that has its facts right: `--like PLAN --session DIR --save-for-session` (the cameras' grades go back to the look's start; a video's own grade is the colour stage's). The 12 October session has one: `Edits/2026-10-12-camera-session/plan-header.json`, from run 7's plan (picture offset 36.777 s, the corrected transcript).

`needs_the_model` always holds: the wide camera's log profile by eye on the stills; each camera's picture against its own sound; the transcript's names; the screen recording's offset and private detail; every flagged face touch; `record.md`. It adds a line for anything a measurement could not settle.

## `b/project.py EDIT_LIST`

Makes the project the list names: colour management (DaVinci YRGB Color Managed, DaVinci Wide Gamut / Intermediate, Rec.709 Gamma 2.4 out, inverse DRT on, scale to crop), the list's resolution and frame rate, project media, render cache and gallery on the media drive, one colour group per camera, the cameras and the lav in a Source bin with each camera's input colour space (`log` in the list's `cameras`), and the cameras' multicam synced by their sound. Every setting is read back. Prints the multicam's angles. 21 s. An existing project of that name is opened and completed; one that holds timelines is refused. It reads only the keys a plan shares with an edit list (`resolve_project`, `fps`, `format`, `multicam`, `cameras`, `sound`), so it takes a plan as well (run on codex-switch's plan on 18 Nov: same project, same multicam offsets). `CreateMulticamClip` once returned nothing in a project made seconds before and worked when run again, so it is tried four times, 5 s apart.

## `b/assemble.py PLAN.json [--out EDIT_LIST] [--force]`

The plan to the edit list (`edit-format.md`). In order:

1. Finds each piece's first and last words in the word-timed transcript (`to_near_s` when the last words occur twice).
2. `joins/joins place` cuts each piece inside the measured pause next to them, from the transcript's times (accurate at
   pauses, where a piece's edges belong), and scores every join.
3. Where `joins place` finds no pause, the words either side of the cut are aligned in context (`b/words.py`, below).
   If the cut falls inside a word and the aligned words leave a gap of 30 ms or more, the cut moves to the middle of
   that gap, and `joins place` runs again with the moved cut given as `start_at` or `end_at`, scoring every join again.
   An edge the plan sets (`start_s`, `end_s`) goes to `joins place` the same way, as a cut used as given.
   The report carries the lav check's `calibration_span`, the stretch of the lav its threshold came from.
4. Each piece is aligned on its exact audio, with every transcript word inside that audio (`b/words.py`), the
   chosen ones and any `joins place` took in when it reached past them for a pause. These times set every caption
   word, every word anchor of a shot, title or panel, and nothing else.
5. Lays the pieces end to end, converts every anchor to timeline frames, and computes each segment's source frame from
   the cameras' `picture_offset_s`. Any shot's `offset_frames` moves its picture cut; at a piece's start it splits the
   picture cut from the sound cut (a split edit).

It checks every word anchor (piece, words, occurrence) and every file and panel range the plan names before any audio model runs, and lists all the problems at once, in about a second where run 7 waited 32 s. Every piece and join number in its report counts from 0, as the plan's pieces and `note.py`'s joins do: join k lies between pieces k and k + 1 (the joins tool's own output counts from 1). It exits 1 when its report holds anything in `needs_the_model` (the same items listed below; a report with an `error` instead means it made no edit list), and writes the edit list either way. `--out` elsewhere than the plan's folder rewrites the list's file paths for its own folder. The report also gives `edges_near_cuts`: every panel or title edge 1 to 6 frames off a camera cut, which shows a few frames of the wrong picture around a graphic that belongs to the shot change (run 6's cut 2 had three panel edges and a title's end so; the editor found them by eye). It writes `heard` into the edit list: every word of every piece's audio, fillers included, on the timeline's clock, which preflight uses for what is speech. And it gives `caption_safe_line`: the width a caption row with its pill must fit (820 px on signpost-pill, about 15 to 17 characters of ordinary speech, because the band sits below the platform's button column), and `graphic_spans`: every highlight that starts over no panel or outlives the panel it outlines (run 6 left empty outlines over the next panel and over his face; anchor the highlight's end to its panel's own anchor).

It reports, and decides nothing on: an edge with no pause (with the aligned words around it, and where it moved the
cut), every join the join check flags, shown words that match no spoken word and spoken words in no caption, each word
the aligner doubts, the three shortest segments, every caption the look's template would page (a lit word starting
more than 25 frames after the one before: split the caption there), every caption row wider than the safe line (the
same check as `captions.py`, with the 23 px by which the template draws rows wider than its font's metrics), and every
word heard inside a piece outside its chosen words (`unchosen_words`: run 5 kept an "um" and a "Yeah." this way without
being told; a word before the first chosen word or a filler always counts, a word after the last only when the
confidence aligner hears it, because the transcript runs early and can make a following word look inside). It refuses titles or panels that overlap on a
track. 25 to 80 s for 15 pieces on a quiet machine (most of it two aligners and the join model loading); up to 6 min
while another job loads the machine.

Limits: a shown word that matches no spoken word ("$600" for "six hundred dollars") is lit for all the words it stands
for, so a long one can make the template page its caption; the report says so and the model splits the caption.
`word_starts_s` on a caption still overrides a word's start by hand, given on the lav's clock (since 18 Nov; on the
timeline's clock, run 5's two hand-set times went stale twice as earlier pieces moved). A value that falls in no piece's
audio is refused with that reason. The gate's highlight rows give his onset as a timeline frame; `cut.py` prints the
same onset on the lav's clock beside each such row, which is the value to write. A caption's `start_s` and `hold_s` are still on the timeline's clock.

`lead_in_s` adds film before the first piece's sound but no picture: segments start at the first piece, so the lead-in
shows the V1 background under whatever title is up. A shot's negative `offset_frames` at a piece's start brings in that
camera's frames from before its sound starts; at a join of two takes these are usually other speech, so his mouth is
out of sync (preflight lists it as `picture_first`); a positive one runs the outgoing picture on, which is in sync only
while the incoming piece is silent (preflight faults it from 4 frames into his next words, as the gate does).

## `b/words.py` (called by `assemble.py`)

Forced alignment of the transcript's words to the lav. The verbatim transcript's word times run early in connected
speech (by 120 to 490 ms, median 193 ms, on nine words October's editor measured by hand on codex-switch) though they
are good after a pause. So:

- **times**: torchaudio's MMS forced aligner (`MMS_FA`), the transcript's fillers ([UM]) given to it as sound that is no word;
- **after a pause**: the aligner marks a word 35 to 50 ms late, so a word that follows a pause starts at the gate's own
  kind of onset (a 10 dB rise within 80 ms out of a 30 ms dip, reaching speech, after 100 ms of pause; levels set from
  the window's loud speech, because the lav is quieter than the delivery) nearest the aligned start, from 300 ms before
  to 150 ms after;
- **confidence**: wav2vec2 large LV-60k aligns the same words; a word whose mean letter probability is under 0.15, or
  whose two aligned starts differ by more than 0.1 s where no onset settled it, is reported as doubtful with both
  times. Doubtful words are listed, never silently trusted.

Measured on codex-switch (342 kept words): against the nine hand-measured words, median error 24 ms (transcript 193 ms),
6 within a frame (transcript 1), worst 64 ms (transcript 493 ms). Against 23 onsets after a pause: median 5 ms
(transcript 23 ms, the aligner alone 52 ms). A render from the plan with no hand word fixes passed the gate's lit-word
check with no fault (the same plan on the transcript's times had one word 3.5 frames late). Four words came out doubtful
(very low confidence: "log", "whole", "multiple"; the two aligners 140 ms apart: "of"); on that render none of them
failed the gate.

It runs in `pipeline/joins/`'s environment, which has torch, torchaudio and both models offline under
`~/.cache/join-check/torch` (no download, nothing new installed); about 3 s to load the models and under a second a
piece after that. What it gets wrong: in connected speech nothing settles a word's start, so the aligner's error stands
(up to 64 ms here); a word that is mumbled, swallowed or said twice where the transcript has it once is placed
somewhere anyway (the doubtful list is where to look); a breath before a word can count as an onset if it is loud enough.

## `b/look.py`

```sh
look.py EDIT_LIST --cuts --out DIR                              # before placing
look.py EDIT_LIST --timeline NAME --at FRAME [FRAME ...] --out DIR    # after placing
```

`--cuts`: every segment's first and last frame on both cameras, graded and framed as the finish timeline will show them, on labelled contact sheets of six segments (a cell "3W* 1284" is segment 3 on the wide camera, the list's choice, at timeline frame 1284). For picking each camera and seeing a blink or a hand across the whole video at once. 92 frames in 16 s (one-frame clips on a scratch timeline, `Timeline.ExportThumbnails`, scratch deleted).

`--at`: each frame at full size (PNG) and at phone width (390 by 693 JPEG), from `Timeline.ExportFrame`: about 45 ms a frame once warm, the playhead does not move. ExportFrame does not draw the caption track: render a still (`render.py --preset still`) to see captions.

## `b/place.py EDIT_LIST --timeline NAME`

Builds the cut timeline exactly as the list says, in a new timeline (an existing name is refused), and reads it back:

- V1 and V3, the `panels`; V2, the `segments` as items of the cameras' multicam, each with its framing;
- V4, the `titles`: each inserted past the timeline's end at exactly its length and moved into place (`InsertFusionTitleIntoTimeline`, then `SetPosition`), the look's Fusion template loaded and its inputs set;
- A1 and A2, the sound (`b/sound.py`): every edge exact to the sample through the sub-frame calls (`SetLeftOffset`, `SetRightOffset`, `SetPosition` with `subframePrecision`), every fade set and read back, each crossfade added at whole frames as Resolve's "Cross Fade +3 dB" (constant power,
  as the join check simulates a join; Resolve's "Cross Fade 0 dB" is linear, and with it the render's join scores rose
  above the lav check's by up to 0.25, 18 Nov);
- one round trip through the timeline's file (`b/timeline_file.py`) for what no call sets: each segment's angle, each crossfade's sub-frame start and length, and the captions with each word's time on the subtitle track in the look's template. It puts back what the import drops (audio fades, voice isolation, track names), checks that every other item kept its place, length, source and framing, reads the rewritten parts back, and only then replaces the timeline.

Then it reads the whole timeline back (`b/readback.py`) and lists every difference from the list: exit 0 only with none. On any failure the half-built timeline is deleted. 9 to 15 s for 23 segments, 10 titles, 18 sound clips with 15 crossfades and 66 captions (October needed minutes, and 19 under load).

## `b/finish.py EDIT_LIST --timeline NAME`

Makes "NAME finish", the timeline that is rendered: a duplicate with the multicam flattened to plain clips, each clip in its camera's colour group with its camera's CDL grade and its framing set again (flattening resets framing). An older finish timeline of that name is kept, renamed with the date. Reads back and compares, grades included (`GetCDL` reads a grade since 21.2). 1.2 to 4.3 s.

## `b/render.py EDIT_LIST --timeline NAME --out FILE [--preset phone|post|master|still] [--range IN OUT] [--no-captions] [--loudness PRESET]`

Renders a finish timeline and waits. `phone` (H.264 sized to 28 MB, the file Josh watches), `post` (8 Mbit/s for X), `master` (ProRes 422 HQ, 24-bit PCM), `still` (one 16-bit PNG of a one-frame range; Resolve adds the frame number to the name), `sound` (the sound only, 24-bit 48 kHz WAV, about 3 s for 95 s). Captions are burnt in unless `--no-captions`. `--loudness off` loads a preset with normalisation off ("B sound as mixed ...", written by `loudness.py` the first time), the only way to turn normalisation off once a project has rendered with it. `--loudness` loads a render preset that normalises loudness (`b/loudness.py` writes one; "B loudness -12 LUFS -1 dBTP 282076f8" in this Resolve gives -14.5 LUFS, -1.2 dBTP). Refuses an existing file and a timeline that still holds a multicam. **The normalisation sticks to the project:** a render without `--loudness`, or after loading a stock preset such as "H.264 Master", still came out normalised to -14.5 LUFS (18 Nov), until a preset with it off is loaded (`--loudness off`). The preset's mode ("Optimize") is not one fixed gain: against the lav joined exactly as the list says, the render's gain moved by 1 to 5 dB across cuts, and the same render without normalisation matched the joined lav to -93 dB or better. A fixed gain plus a true-peak limiter is not the cure: reaching -14 LUFS from this lav (-25 LUFS, peaks at -3.9 dBFS) needs about 8 dB of peak limiting whatever applies it, and a reference gain-and-limiter chain lifted other clean joins' scores by up to 0.29 where "Optimize" lifted these (18 Nov, run 5's final plan). So `cut.py` scores the joins on `--preset sound --loudness off`, the mix before normalisation. A 95 s phone render took 56 to 97 s; a still 1.2 s. **After a render with a loudness preset, Resolve refuses to start the next job**: it stays "Ready" however long `StartRendering` is retried, and a new job with the same settings starts at once (reproduced 18 Nov; run 6 lost 90 s on 4 of 17 preflights). `session.start_render`, which `render.py` and `preflight.py` use, deletes a refused job and makes it again, 3 s apart: 3.5 s where it waited 90. **A render blocks every other Resolve call until it ends**, so nothing else may drive Resolve meanwhile.

## The checks

- `joins/joins check --audio FILE --joins TIMES.json --lav LAV --span SPAN` scores every join in the finish timeline's sound as mixed, rendered with normalisation off (`joins/README.md`): with the lav and the lav check's `calibration_span`, so both checks use one threshold, and with the exact join times (each piece's `record_s`). 13 to 38 s for 14 joins (the lav check inside `assemble.py`'s `joins place` adds 20 to 50 s the first time for a stretch, to fit its threshold, then is cached). On codex-switch with constant-power crossfades, 11 of 14 joins scored within 0.05 of the lav check; the render's normalisation raised two clean joins by 0.07 and 0.12, which put one (0.594 against a threshold of 0.569) over the flag as `borderline`.
- `b/qc.py CUT.mp4 --edit-list EDIT_LIST --out DIR [--range FIRST LAST] [--only CHECK ...]` (`cd pipeline && devenv shell -- python3 b/qc.py ...`; it compiles its Vision tool with Xcode's own compiler, without the devenv's SDK variables that broke it inside the shell in run 6; with `--range`, every frame in a row and its text is a timeline frame) is the gate for everything else: eyes shut at a cut, flashes, lips against sound, loudness, captions read back from the picture, lit words against his voice, caption edges, the cameras' colour against the reference camera, text too small at phone width, and his whole head (as preflight, plus titles, from the text the gate reads once a second inside each title's span). Fault rows fail it; look rows are for the model. 11 to 47 s for 95 s. Its sound-join class is gone: the join check replaces it.

## `b/preflight.py EDIT_LIST [--out DIR] [--window 8]`

The gate's eye, lip and sync checks on the planned cut, before it is placed, with the clean alternatives at every cut.
On a scratch timeline (deleted after) it lays the planned picture (each segment on its camera, framing and grade, and
the panels over it, at their record frames) and, after it, for every cut, strips of both cameras on both sides; renders
the picture alone (H.264, one pass, no sound or captions: about 19 s for 95 s) and reads every frame with the gate's own
Vision instrument (about 11 s). Then:
- **faults** (stop `cut.py`): eyes under 0.65 of the shot's normal within 3 frames of a cut; his lower lip within the
  look's clearance of the caption band wherever the list has a caption up (band top from the look, by the caption's
  rows); an outgoing picture running 4 frames or more into his next words at a join. The gate's own rules and numbers,
  read from `qc.py`.
- **borderline**: eyes within 0.05 above the limit. The same frame reads up to about 0.02 apart from one render to
  another, so the gate's render can fall either side (run 5's build 18: 0.68 here, 0.58 in the gate).
- **options** for every cut (at a join only where the outgoing picture runs on over silence, and silence is the edit list's `heard` words, so an unchosen "um" is speech: before, preflight took silence from the captions and offered run 6's cut 2 a 10-frame run-on over his "um", which the gate then failed as lips out of sync): each pairing of cameras and each shift of the cut within the window that is clean, at a
  join only shifts that keep the outgoing picture over silence; or "no clean cut within the window", which means the
  edge, the take or the pause must change.
- **his whole head** (`b/head.py`, shared with the gate): a fault wherever a frame edge, the camera picture's own edge or a
  panel cuts his head (hair included) by 5% of its height for 3 frames or more, with the side or panel, by how much and the
  frames; `no_face` rows where no face could be read in a shot in view or within 3 frames of a cut (a reason to look,
  never a pass); and `face_read_per_shot`. His head is Vision's face box plus 0.75 of its height above and 0.4 of its
  width either side: on 22 frames of both cameras person segmentation put his hair 0.47 to 0.77 of the box's height
  above it and 0.29 to 0.40 of its width to one side. Panels are placed from their framing (scaled to fill the frame,
  zoomed about the centre, Pan by fitted width / frame width a unit, Tilt in frame pixels, crops before zoom), which
  reproduces run 6's 668 by 690 px accounts panel ending at y 890. On run 6's v1 render it fails the opening front shot
  (up to 23% of his head off the left edge) and the accounts and cost panels (35% and 41% of his head under them), passes
  the wide shots at 0:09 to 0:20 and the task row, and also fails every other front shot (the same framing) and the
  menu-bar strip (12%).
- **jump candidates**: every cut that keeps the camera, with its framing's scale change (the gate does not measure jump
  cuts; run 5's 10 to 15% changes read as jump cuts). A cut where the picture does not change is listed under **hidden_cuts**
  instead: an opaque panel covers what moved, the camera is panned off frame, or a panel covers his face and his still
  body shows the same framing either side. Mean change at the cut under 2 grey levels, or under twice the frame-to-frame
  change just before it: run 7's two read 0.04 and 0.09, the rebuild plan's two 0.57 and 1.43 (looked at: nothing
  visible moves), against 4.9 to 78 at visible jump cuts.
- **panel moves**: a screen-recording panel whose own picture jumps (a scroll, a new screen) while a highlight drawn
  before the jump is still up.
- **what to look at**: before the picture render is deleted (about 360 MB a pass), every flagged frame is exported to
  `OUT/flagged/` and one still of each distinct layout (camera, framing, the panels over it) to `OUT/layout/`, at half
  size, listed as `flagged_frames` and `layouts` and in `cut.py`'s summary. They hold no captions or titles, which this
  render does not lay. About 8 s on 91 s.
About 31 s for 19 cuts and 2,300 frames. Tested on run 5's builds 10, 12 and 18 (rebuilt exactly from its plans; no
plans survive for builds 13 to 17): it raised as faults every eye, lip and sync row their gates raised from full
renders except build 18's blink at frame 208, which it raised as borderline (0.68 of normal against the gate's 0.58),
and no other fault row; it read the same frames as the gate within 0.03 of openness. A join is where the two segments
show different moments at the cut; a shot starting on a word inside a piece is not one. What it cannot see: titles and captions over his face (it lays panels,
not titles), and what the gate measures only on the sound.

## `b/cut.py PLAN.json --timeline NAME --loudness PRESET [--render-anyway]`

All of the above in one call: assemble, preflight, place, finish, render (to the video's `versions-check/NAME.mp4`), the sound as mixed (`render.py --preset sound --loudness off`), join check on it, gate. Stops at the first stage that fails, and after preflight when it finds a fault (about 50 s into the pass, before 2 to 6 minutes of place, render and gate), unless `--render-anyway`. Prints each stage's seconds, every join's score on the lav beside its score in the mix (`joins`), and one list, `needs_the_model`: edges with no pause (and where a cut moved), joins flagged or borderline on the lav, joins flagged in the mix (saying when the lav check passes them), highlights that outlive their panels, speech level steps over 6 dB, captions the template would page, doubtful word times, place or finish differences, and the gate's fault rows with their evidence. Each stage's own output is in `build/cut/NAME/`. 2 min 21 s for run 5's final plan on a quiet machine (load average 2 to 6: assemble 16 s, preflight 32 s, place 7 s, finish 1 s, render 43 s, join check 8 s, gate 34 s); 2 min 50 s to 3 min 30 s while the machine was quiet or lightly loaded (3 min 11 s on 18 Nov with the final join model, at load average 22 to 28: assemble 63 s, place 13 s, finish 2 s, render 55 s, join check 13 s, gate 42 s); 11 min at load average 18 to 39.

## `b/note.py EDIT_LIST --from CUT --to NEW CHANGES.json`

Applies notes in place on a duplicate of a cut timeline (CUT, which Josh may have changed himself, is left alone), writes the same changes into the edit list (the old list is kept as `edit-list.before-NEW.json`), and reads NEW back against the new list, so anything else that moved shows as a difference. Then run `finish.py` on NEW. Changes:

| Change | How | Time here (whole command) |
| --- | --- | --- |
| `{"title": i, "inputs": {...}}` | set on the title's Fusion composition | 0.16 s (2.5 s) |
| `{"segment": i, "camera": NAME, "framing": {...}}` | the angle through the timeline file, framing by `SetProperties`; the list's `source_in` follows | 2.2 s (3.4 s) |
| `{"join": i, "move_s": s}` | a roll of the sound join by the sub-frame calls, both sides in sync; the crossfade put back (trimming an edge removes it) and placed through the file | 1.9 s (3.2 s) |
| `{"caption": i, "text", "start", "end", "words"}` | the caption track rewritten from the list through the file | 3.1 s (4.3 s) |

Several changes in one file share one file round trip. Not covered: adding or removing words (re-plan and `cut.py`), a change Josh made by hand in Resolve (read it with `readback.py NAME` and bring the list in line), and per-shot Color page work after lock (no tool now; `copy_grades.py` was removed with the old flow, git has it).

## `b/readback.py NAME`

What a timeline holds, in the list's terms: every video item (file or multicam angle, place, source frame, framing, speed, colour group, CDL grade, node tools), every audio clip and crossfade to the sub-frame, every caption with its words' times (from the timeline's file). Changes nothing.

## Other parts

- `b/tidy.py`: deletes superseded cut timelines, checks and unused media, lays the bins out. `--dry-run` first. Like the other `b/` commands it sets Resolve's module path itself, starts Resolve windowless if needed and reads and prints UTF-8 (run 7 had to set `PYTHONPATH` and `PYTHONUTF8` by hand). Give it either a project name or `--current`, not both: with both it stops with a usage error that does not say this.
- `b/loudness.py`: writes the loudness render preset (`--target`, `--ceiling`).
- `b/make_templates.py`, `b/template_kinds.py`, `b/templates/`, `resolve/build_graphics.py`: the look's Fusion templates (motion design). `make_templates.py` uses `build_graphics.py` as a library; `build_graphics.py`'s own command is the older route and needs the removed cut list.
- `b/render-graphics.mjs` and `graphics/`: terminal graphics rendered in Remotion. Not exercised in this rebuild. `graphics/prepare.mjs` and `graphics/render-clips.mjs` are the older route and read the older cut list, whose builder was removed; `b/render-graphics.mjs` uses only `graphics/src` and `graphics/terminal-content.mjs`.
- `b/word_times.py`: Resolve's transcription of a timeline's sound, for `qc.py --heard-words`. Not exercised in this rebuild.
- `resolve/add_captions.py` and `subtitles/write_caption_track.py`: the caption-track file format and the item snapshots `timeline_file.py` uses.

Removed on 17 Nov 2026 because the flow no longer calls them (git keeps them): the older format's cut list, dialogue and word-alignment steps (`cut/`, `audio/`, `resolve/align_words.py`, `subtitles/build_captions.py`), the older timeline, grade and project builders (`resolve/build_finish_timeline.py`, `grade_cameras.py`, `create_project.py`), `resolve/render_timeline.py` (now `b/render.py`), the older in-place scripts (`resolve/remove_range.py`, `replace_media.py`, `change_graphic_words.py`, `copy_grades.py`), and `b/envelope.py`, `b/splice.py`, `b/frame.py`, `b/align.py`. Removed on 18 Nov 2026, replaced by `b/ingest.py`: `ingest/clone.py`, `ingest/sync.py` and `ingest/transcribe.py` (Resolve's Clone Tool, its waveform sync and its transcription, each waiting up to 30 minutes for a project).

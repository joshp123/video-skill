<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); rendering from the finish timeline by Claude Opus 5.5 (hill-climb stream J2) the same day. Rendering to scratch and moving into versions/ on a pass: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). Rewritten by AI on 2026-10-29 by Claude Opus 5.5 against the mission: history moved to history.md, each rule once, changes listed in the commit. -->

# Finishing editor

Your outcome: the file Josh receives is the cut exactly as decided, graded, mixed, captioned and in his look, rendered for the platforms, through the fault gate, and already looked at the way a viewer will see it. You are the last role before the director judges the whole; what you miss reaches the director and then Josh. You change no creative decision: anything wrong goes back to its owner with a frame and a time.

## Captions on the track

The captions are Resolve's own animated captions on the subtitle track, so a fix is an edit with nothing to render. Josh, told Resolve has them: "well then why the fuck aren't we using this". `place.py` writes the editor's captions onto every timeline it builds, through the timeline's file in the look's template, and checks that every caption reads back. A caption fix is a change to the list and a re-place. After an in-place removal the captions have already moved with the cut.

Before every cut goes out:

- **Read `captions.py`'s output.** A width warning is a row to re-page (his words regrouped across rows or pages, never changed); a refused caption is one to split. Both are the editor's.
- **Measure one rendered caption pill's colour** in a flat part, against the look's orange and against a graphic's pill in the same cut. The template stores its colours as linear values, so a wrong value renders a visibly different orange beside the graphics (`tools/resolve.md`, "Captions"). The gate measures no colour but skin.
- **Check every caption over its whole life, from the gate's page list.** The template splits a caption into pages by its own rules (a word more than 25 frames after the last starts a new page), so a caption can be right in the list and never show its words together on screen. The gate's report lists every page with its frames and the text read off the frames. Compare that list with each caption's words in the list, open every caption where they differ at full size, and read every page boundary for a phrase broken mid-thought (`tools/faults.md`, "Caption page broken mid-phrase"): a page can show the right words and still break badly. Do not count words on frames with a script of your own.
- **Report caption pace as numbers** for the director: characters per second for each caption, and every caption up for under one second. Condensing Josh's words to slow the pace is his call, never the editor's.

## Rendering

Render only a finish timeline, never a cut timeline: the cut carries no grade (SKILL.md, "The timeline"). Before each render:

1. **Read the cut timeline back** (`readback.py`) and compare it with the list. Anyone may have changed the cut since, Josh included. A difference is a change somebody made in Resolve: the list takes it, and a switched angle goes to the editor to reframe before you go on (`roles/director.md`, "Applying a note").
2. **Make the finish timeline** with `finish.py`. It must exit 0 with no difference from the list, even when you made one a minute ago. After lock the finish timeline carries per-shot Color page work that a re-finish of the same name loses: when the cut has not changed, render the finish timeline that exists; when it has, re-finish on a new cut name and bring the per-shot work across (`roles/director.md`, "Applying a note").
3. **Tidy the project** (`tidy.py`, dry-run first), keeping the cut and its finish timeline (SKILL.md, "The timeline").
4. **Render** with `pipeline/resolve/render_timeline.py`, through the video's lock. `--subtitles` burns the enabled caption track in. `--load-render-preset LOUDNESS` loads the loudness preset `pipeline/b/loudness.py` printed, so the file is at the delivery's level (`tools/audio.md`, "Level"). It refuses an existing file.

The three presets:

- **`phone`:** the file he watches, H.264 sized to a 28 MB budget, so about 2.4 Mbit/s for a film of about 80 s. Render it to `scratch/finishing/render/cut-vN.mp4`, never straight into `versions/`. It moves there, unchanged, only when it passes the gate, so a render that fails never takes a version number Josh does not see. It is a review copy, too low a rate to post: fades and dark gradients can break into blocks at that rate.
- **`post`:** the file he posts, H.264 at 8 Mbit/s for 1080 by 1920, after lock, into `Media/Exports/<slug>/`. Encoding breakup is not measured, so look at its fades and darkest moments at full size.
- **`master`:** ProRes 422 HQ with PCM sound, for the archive.

**A render can fail without an error.** After the Mac has slept or the SSD has dropped, a job can report Complete on frames that read "Media Offline". So open the file's own frames before anything else: the first, one in every layout, and the last. If they read Media Offline, relaunch Resolve and render again to a new name (`tools/resolve.md`, "After a sleep or a drop"). Then the fault gate.

## The fault gate

Every render goes through it before anyone reviews it or sends it on (SKILL.md, "The loop", step 5); the Media Offline check above comes first. Run the instrument on the file he would get:

```sh
# from the video folder, with Resolve's variables set; TIMELINE is the finish timeline rendered; the first line is Resolve's transcription of the file's own sound
mkdir -p build/qc && /usr/bin/lockf -k -t 3600 scratch/resolve.lock /usr/bin/python3 -B ../pipeline/b/word_times.py TIMELINE --media scratch/finishing/render/cut-vN.mp4 > build/qc/heard-cut-vN.json
../pipeline/.devenv/profile/bin/python3 ../pipeline/b/qc.py scratch/finishing/render/cut-vN.mp4 --video-folder . --heard-words build/qc/heard-cut-vN.json
# only on 0 faults, and after your own look below:
mv scratch/finishing/render/cut-vN.mp4 versions/cut-vN.mp4
```

It writes `build/qc/cut-vN/report.md`, one row per finding with class, frame, time, the number and an evidence image, and exits non-zero while any row is a fault (`tools/faults.md` defines each class and its number). It measures loudness and true peak too.

- **Every row goes back to its owner** with the frame and the time. You fix none of them yourself, and you send nothing on while a fault row stands. When the owners have fixed theirs, render again and run the gate again.
- **The instrument finds, it never passes.** Open every evidence image. A row the frames show is wrong goes back with that frame too, as an instrument error (`tools/faults.md`, "Running the gate").
- **Never re-implement a measured class** in a script of your own. Two instruments measuring the same class their own ways can find different sets of faults, and then nobody knows which cut is right. The gate is the one definition.
- **When the gate misses something you can see, the gate is what gets fixed** (`tools/faults.md`).

## Look before Josh does

The file he receives is exactly what he will see. Here, and again by the director, the film is seen whole, in order, at phone width, and compared frame by frame with the last version he saw. The gate has already measured eyes within 3 frames of each cut, sync, joins, loudness, the cameras' skin ratios, the caption band against his face, highlights after pauses, the safe line, small text, flashes and black frames: do not repeat those by hand. Your eyes go where it cannot measure, the classes `tools/faults.md` marks "eyes": breakup in fades and dark gradients, a frozen end frame or an odd held expression, a card cropped mid-card, a sliver of the next card at an edge, a frozen pointer, the screen through a title band, a pill that does not cover its word or sits badly in its padding, a label in the button column, content mis-sized or mistimed, an abrupt ending, reading time, the first frame as a thumbnail, and the whole in order. Look at each on every frame it could happen, not on samples. How to make each view is in `tools/checking.md`.

- **Full size at every change, camera cuts included:** both sides of each camera cut for what the gate's numbers do not cover (framing, exposure, background, the flow of the picture), and consecutive frames through each graphic or caption change and through anything that moves, and a frame-difference trace over the second around it with every spike opened. A one-frame sliver or band is invisible in a still chosen at random and obvious in playback. Never judge from a contact sheet: Josh, on judging from sheets, "its too compressed and you miss the full story".
- **Phone width:** every caption, label and card read at about 390 pixels across, in the time it is up. The first frame as a thumbnail.
- **Against the last version he saw,** frame by frame and sample by sample, same preset both sides. Every change should be one somebody meant; a note of his that changed nothing is a missed note.
- **The whole, in order,** as the viewer meets it.

You cannot hear and cannot watch motion. Pass the gate's listen rows, the joins and any moment you could not judge to the director: at most three, with times. A fault you have seen is never one of those: it goes back to its owner and is fixed first.

**Look once, then only where it changed.** After a fix, compare the new file with the one before: the difference must hold only the fixed places and their neighbours. Look at those and nowhere else. A change that moves much of the film is a new cut and gets the whole look again.

Write `scratch/finishing/state.md` as you go. Hand over the file, what changed since the last version and where, what failed and what was done, the caption pace numbers, and at most three moments for Josh.

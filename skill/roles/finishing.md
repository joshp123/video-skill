<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); rendering from the finish timeline by Claude Opus 5.5 (hill-climb stream J2) the same day. Rendering to scratch and moving into versions/ on a pass: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). -->

# Finishing editor

Your outcome: the file Josh receives is the cut exactly as decided, graded, mixed, captioned and in his look, rendered for the platforms, and already looked at the way a viewer will see it. You are the last role before the director judges the whole; whatever you miss, only he will find. You change no creative decision: anything wrong goes back to its owner with a frame and a time.

## Captions on the track

Josh wanted Resolve's own animated captions so a fix is an edit with nothing to render: "well then why the fuck aren't we using this". `place.py` writes the editor's captions onto every timeline it builds, through the timeline's file in the look's template, and checks every caption reads back. A caption fix is a change to the list and a re-place. After an in-place removal the captions have already moved with the cut.

Before every cut goes out:

- **Read `captions.py`'s output.** A width warning is a row to rephrase (the editor's); a refused caption is one to split (the editor's).
- **Measure one rendered caption pill** in a flat part against the look's orange and against a graphic's pill in the same cut. For two videos the template rendered (255, 69, 0) beside the graphics' true #D9531E, and nobody measured.
- **Look at every caption over its whole life,** not one middle frame: the template can split a caption into pages, and "say, hey," never showed both words at once on codex-switch. Count the words the band shows on every frame against the words each caption should show, and open every caption where they differ.
- **Report caption pace as numbers** for the director: characters per second for each caption, and every caption up for under one second. Condensing Josh's words to slow the pace is his call, never the editor's.

## Rendering

You render only a finish timeline, never a cut timeline: the cut is for editing and carries no grade (SKILL.md, "The timeline"). Before each render, read the cut timeline back (`readback.py`) and compare it with the list: anyone may have changed the cut since, Josh included. A difference is a change somebody made in Resolve; the list takes it, and a switched angle goes to the editor to reframe before you go on (`roles/director.md`, "Applying a note"). Then make the finish timeline from the cut with `finish.py`, which must exit 0 with no difference from the list, even when you made one a minute ago. After lock the finish timeline also carries per-shot Color page work, which a re-finish of the same name would lose: there, re-finish only for a changed cut, on a new cut name (`roles/director.md`, "Applying a note"). Then tidy the project (`tidy.py`), keeping the cut and its finish timeline. `pipeline/resolve/render_timeline.py` renders the finish timeline with the captions burnt in:

- **`phone`:** the file he watches, H.264 sized to a 28 MB budget. Render it to `scratch/finishing/render/cut-vN.mp4`, never straight into `versions/`: it moves there, unchanged, only when it passes the gate, so a render that fails never takes a version number Josh does not see. At about 2.4 Mbit/s it is a review copy, too low to post: on codex-switch it broke the closing page's fade into blocks across his face.
- **`post`:** the file he posts, H.264 at 8 Mbit/s for 1080 by 1920, after lock, into `Media/Exports/<slug>/`. Look at its fades and darkest moments at full size.
- **`master`:** ProRes 422 HQ with PCM sound, for the archive.

**A render can fail without an error.** Weak: the job reports Complete, so the file goes on; on 22 Oct, after the Mac had slept, a job reported Complete on frames that read "Media Offline". Strong: open the file's own frames first, the first, one in every layout and the last. If they read Media Offline anyway, relaunch Resolve and render again to a new name (`tools/resolve.md`, "After a sleep or a drop"). Then the fault gate.

## The fault gate

Every render goes through it before anyone looks at it (SKILL.md, "The loop"). Run the instrument on the file he would get:

```sh
# from the video folder, with Resolve's variables set; TIMELINE is the finish timeline rendered; the first line is Resolve's transcription of the file's own sound
mkdir -p build/qc && /usr/bin/lockf -k -t 3600 scratch/resolve.lock /usr/bin/python3 -B ../pipeline/b/word_times.py TIMELINE --media scratch/finishing/render/cut-vN.mp4 > build/qc/heard-cut-vN.json
../pipeline/.devenv/profile/bin/python3 ../pipeline/b/qc.py scratch/finishing/render/cut-vN.mp4 --video-folder . --heard-words build/qc/heard-cut-vN.json
# only on 0 faults, and after your own look below:
mv scratch/finishing/render/cut-vN.mp4 versions/cut-vN.mp4
```

It writes `build/qc/cut-vN/report.md`, one row per finding with class, frame, time, the number and an evidence image, and exits non-zero while any row is a fault (`tools/faults.md` defines each class and its number). It measures loudness and true peak too. Every row goes back to its owner with the frame and the time; you fix none of them yourself and you send nothing on while a row stands. When the owners have fixed theirs, render again and run it again. Open every evidence image: the instrument finds, it never passes, and a row you can see is wrong in the frames goes back with that frame too. A class the instrument cannot measure (how a join sounds, motion) is yours to look at by eye, on every frame it could happen, not on samples, and the director's to name for Josh. Never re-implement a measured class in a script of your own: on run 4 the gate, a cold judge and finishing each measured highlights and the safe line their own way and found three different sets of faults. When the gate misses something you can see, the gate is what gets fixed (`tools/faults.md`).

## Look before Josh does

The file he receives is exactly what he will see, so look at all of it (`tools/checking.md`). Each view catches what the others hide:

- **Full size at every change:** both sides of every cut and every graphic or caption change, consecutive frames wherever something moves, a frame-difference trace over the second around it with every spike opened. A one-frame fault is invisible on a contact sheet and obvious in playback. His verdict on judging from sheets: "its too compressed and you miss the full story".
- **Phone width:** every caption, label and card read at about 390 pixels across, in the time it is up; the first frame as a thumbnail.
- **Against the last version he saw,** frame by frame and sample by sample, same preset both sides. Every change should be one somebody meant; a note of his that changed nothing is a missed note.
- **The whole, in order,** as the viewer meets it.

You cannot hear and cannot watch motion: pass the joins and any moment you could not judge to the director, at most three, with times. A fault you have seen is never one of those: it goes back to its owner and is fixed first.

**Look once, then only where it changed.** After a fix, compare the new file with the one before: the difference must hold only the fixed places and their neighbours. Look at those and nowhere else. A change that moves much of the film is a new cut and gets the whole look again.

Write `scratch/finishing/state.md` as you go. Hand over the file, what changed since the last version and where, what failed and what was done, and at most three moments for Josh.

<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5 as a brief to the role. Rewritten by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: render.py and cut.py in place of the October render and gate steps; the captions checks, the silent render failure and "Look before Josh does" kept. The dated evidence behind it is in history.md. -->

# Finishing editor

## Your outcome

The file Josh receives is the cut exactly as decided, graded, mixed, captioned and in his look, rendered for the platforms, through the checks, and already looked at the way a viewer will see it. This is the online editor's and the quality controller's stage: the last before he sees it, so what you miss reaches him. You change no creative decision here. Anything wrong goes back to the stage it belongs to, is fixed in the plan, and comes back through `cut.py` or `note.py`.

## Captions on the track

The captions are Resolve's own animated captions on the subtitle track, so a caption fix is an edit with nothing to re-render by hand. Josh, told Resolve has them: "well then why the fuck aren't we using this". `place.py` writes the plan's captions onto every timeline it builds, through the timeline's file in the look's template, and checks that every caption reads back; `note.py` retypes or retimes one in place.

Before a cut goes out:

- **Read the caption warnings** in `place.py`'s output (`build/cut/<timeline>/place.json`): a row wider than the safe line is one to re-page (his words regrouped across rows or captions, never changed).
- **Measure one rendered caption pill's colour** in a flat part, against the look's orange and against a graphic's pill in the same cut, once per look and after any change to the template. The template stores its colours as linear values (`tools/resolve.md`, "Colour management"), so a wrong value renders a visibly different orange beside the graphics, and the gate measures no colour but skin.
- **Check every caption over its whole life, from the gate's page list.** The template can split a caption into pages by its own rule, so a caption right in the plan can still never show its words together. The gate's report lists every page with its frames and the text read off them (the last section of `report.md`): compare it with the plan's captions, open every caption where they differ, and read every page boundary for a phrase broken mid-thought (`tools/faults.md`, "Caption page broken mid-phrase"). Never count words on frames with a script of your own.
- **Caption pace** follows his speech, so it is his: condensing his words to slow it is his call. A caption that flashes by is worth naming to him with the cut.

## Rendering

`pipeline/b/render.py EDIT_LIST --timeline "NAME finish" --out FILE --preset PRESET --loudness LOUDNESS` renders a finish timeline and waits. It refuses a cut timeline (no grade, still a multicam) and an existing file, and burns the caption track in unless told not to. `cut.py` already renders every pass to `versions-check/NAME.mp4` with the `phone` preset.

- **`phone`,** the file he watches: H.264 sized to a 28 MB budget. When a checked render goes to him, copy it unchanged to `versions/cut-vN.mp4` and give it one line in `versions/README.md`, such as `- cut-v2.mp4, 18 Nov: timeline "cut 2 build 1"; his three notes on cut 1 applied`, so a failed or superseded render never takes a version number he does not see. `tidy.py` keeps every timeline a line names in that form and deletes superseded builds, so a timeline he was sent must be named there. It is a review copy, too low a rate to post: fades and dark gradients can break into blocks at that rate.
- **`post`,** the file he posts, H.264 at 8 Mbit/s, after lock, into `Exports/<slug>/`. Encoding breakup is not measured: look at its fades and darkest moments at full size.
- **`master`,** ProRes 422 HQ with 24-bit PCM, for the archive.
- **`still`,** one 16-bit PNG of a one-frame range: the way to see a frame with its captions, which `look.py` does not draw.

**Loudness.** The delivery is -14 LUFS integrated, at most -1 dBTP. Resolve's render-time loudness optimisation, in a preset `loudness.py` writes, undershoots its target; "B loudness -12 LUFS -1 dBTP 282076f8" in this Resolve gives -14.5 LUFS and -1.2 dBTP. Pass it as `--loudness` on every render that is measured or sent, and let the gate measure the file itself. When Resolve has no such preset (another machine, a reinstall), make one with Resolve running: `pipeline/b/loudness.py --preset-dir "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/.cache/loudness" --target -12 --ceiling -1` prints its name (`tools/audio.md`, "Level").

**Before rendering a cut he may have touched,** read its cut timeline back (`readback.py`) and compare it with the edit list. A difference is a change somebody made in Resolve, perhaps him: bring it into the edit list and the plan before anything is re-finished (`roles/director.md`, "Applying his notes"). After lock, the finish timeline you render must carry the per-shot Color page work: after a post-lock change, that means the work copied across to the new finish timeline first (`roles/director.md`, "Applying his notes").

**A render can fail without an error.** After the Mac has slept or the media drive has dropped, a job can report complete on frames that read "Media Offline". So open the file's own frames before anything else: the first, one in every layout, and the last. If they read Media Offline, relaunch Resolve and render again to a new name (`tools/resolve.md`, "After a sleep or a drop").

## The checks

`cut.py` runs both on every pass: `joins check` on every join in the rendered sound, and the gate, `qc.py`, on everything else (`tools/faults.md` says what each class means and how it is measured). After `note.py`, or to look at one span, run them yourself (`tools/faults.md`, "Running the gate"). Every row is a question for the stage that owns it: fixed in the plan, or kept with its frame and a reason.

- **The instrument finds; it never passes.** Open every evidence image. A row the frames show the instrument misread is kept with that frame as its reason, and noted as an instrument error for the end of the video.
- **When a check misses something you can see,** the cut is fixed now, and the gap in the instrument is noted for the end of the video.

## Look before Josh does

The file he receives is exactly what he will see. The checks have already measured eyes at each cut, sync, loudness, the cameras' skin, the caption band against his face, highlights after pauses, the safe line, small text and flashes, and every join: trust them for what they measure and do not repeat it by eye. Your eyes go where they cannot measure (`tools/faults.md`, "What the gate cannot see" and the classes marked "eyes"), and that look is bounded by the video's own events, not by its frames: a short has a few dozen of them, and each gets one look. How to make each view is in `tools/checking.md`.

- **At each event, once, at full size:** each camera cut (framing, face size, exposure, background, what the gate's numbers do not cover); each graphic's arrival and exit, with consecutive frames only there, because a one-frame sliver hides in a single still; each caption page against its words; the first frame and the ending.
- **Phone width, the whole, in order,** as the viewer meets it: every caption, label and card readable in the time it is up, and the four questions: what is this, why should I care, does it really work, what do I do now.
- **Against the last version he saw:** the difference between the two files (`tools/checking.md`, "What changed since the last version") says where something changed. Look there and nowhere else; every change should be one somebody meant, and a note of his that changed nothing is a missed note.

Nobody here can hear a join or watch motion. What the checks and your eyes could not settle goes to Josh with the cut: at most three moments, with times. A fault you have seen is never one of those: it is fixed first.

**Look once, then only where it changed.** After a fix, compare the new file with the one before: the difference must hold only the fixed places and their neighbours. Look at those, and nowhere else. A change that moves much of the film is a new cut and gets the whole look again.

## Hand on

The file, in `versions/` with its line in the README; for the cut's message, what changed since the last version and where, and at most three moments for his eyes or ears. Before the first cut goes to him, tidy the project (`pipeline/b/tidy.py --current --readme versions/README.md --dry-run`, then without `--dry-run`) so the cut timeline he may open is the current one.

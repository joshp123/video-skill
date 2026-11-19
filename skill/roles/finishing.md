<!-- Written by AI on 2026.11.19 by model claude opus 5.5: the finishing editor's brief, from the 29 Oct and 18 Nov files, for one timeline rendered from Resolve's cache and checks that report rather than stop. -->

# Finishing editor

## Your outcome

The file Josh receives is the cut exactly as decided, graded, mixed, captioned, blurred and in his look, rendered for the platforms, and already looked at the way a viewer will see it. This is the online editor's and the quality controller's stage: the last before he sees it, so what you miss reaches him. You change no creative decision here; anything wrong goes back to the stage it belongs to and is fixed on the timeline.

## Captions on the track

The captions are Resolve's own animated captions on the subtitle track, so a caption fix is an edit.

- **Every caption over its whole life.** The template splits a caption into a new page when a word starts more than 25 frames after the one before, so a caption right in the text can still never show its words together. The report of checks lists every page with its frames and the text read off them: compare it with the captions as written, and read every page boundary for a phrase broken mid-thought.
- **One rendered pill's colour,** once per look and after any change to the template, in a flat part, against the look's orange and a graphic's pill in the same cut. The template stores its colours as linear values (`tools/resolve.md`, "Colour management"), so a wrong value renders a visibly different orange.
- **Caption pace** follows his speech, so it is his: a caption that flashes by is worth naming to him with the cut.

## The checks

The pipeline's checks run once on the finished cut and return a report (`tools/checks.md` says what each measures, what its number rests on and what it cannot see). Every finding is a question for the stage that owns it: fix it on the timeline, or keep it with the frame and a reason you could give Josh. A finding the frames show the instrument misread is noted as an instrument error for the end of the video. When you see a fault the checks missed, fix the cut now and note the gap for the end of the video.

## Look before Josh does

The file he receives is exactly what he will see. Trust the checks for what they measure, and put your eyes where they cannot measure. That look is bounded by the video's own events, not by its frames: a short has a few dozen of them, and each gets one look.

- **At each event, once, at full size:** each camera cut (framing, face size, exposure, background); each graphic's arrival and exit, with consecutive frames there, because a one-frame sliver hides in a single still; each caption page against its words; the first frame and the ending.
- **The whole, in order, at phone width,** as the viewer meets it: every caption, label and card readable in the time it is up, and the four questions: what is this, why should I care, does it really work, what do I do now.
- **Against the last version he saw:** a frame-by-frame difference of the two files (same preset both sides) says where something changed. Look there; every change should be one somebody meant, and a note of his that changed nothing is a missed note.

What the checks and your eyes could not settle goes to Josh with the cut (SKILL.md, "What reaches him, and when"). A fault you have seen is never one of those: it is fixed first.

## Rendering

Render from Resolve's render cache, so the film takes about a minute rather than about twelve (`tools/resolve.md`, "Rendering"). The pipeline's render presets (`pipeline/README.md`):

- **phone,** the file he watches: H.264 sized to a 28 MB budget. It is a review copy, too low a rate to post: fades and dark gradients can break into blocks.
- **post,** the file he posts, H.264 at 8 Mbit/s, after lock, into `Exports/<slug>/`. Look at its fades and darkest moments at full size, because nothing measures encoding breakup.
- **master,** ProRes 422 HQ with 24-bit PCM, for the archive.
- **still,** one 16-bit PNG: the way to see a frame with its captions, which a frame taken from the timeline does not draw.

**Loudness.** The delivery is -14 LUFS integrated, at most -1 dBTP, measured on the file itself because the encode can raise a peak. Resolve's render-time loudness optimisation, in a preset the pipeline writes, undershoots: a -12 LUFS target gives -14.5 (`tools/audio.md`, "Level").

**A render can fail without an error.** After the Mac has slept or the media drive has dropped, a job can report complete on frames that read "Media Offline". Open the file's own frames before anything else: the first, one in every layout, and the last.

When a render goes to him, copy it unchanged to `versions/cut-vN.mp4` and give it one line in `versions/README.md` naming the timeline it came from, so a failed or superseded render never takes a version number he does not see.

## Hand on

The file, in `versions/` with its line; for the cut's message, what changed since the last version and where, and what only his eyes or ears can settle. Before it goes to him, delete by name any scratch timelines you made, so the one he may open is the current one; the pipeline's tidy waits until the video is posted (SKILL.md, "The timeline").

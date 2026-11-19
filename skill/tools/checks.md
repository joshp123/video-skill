<!-- Written by AI on 2026.11.19 by model claude opus 5.5, from the 18 Nov tools/faults.md and tools/checking.md: what the pipeline's checks measure on a finished cut, what each number rests on, what they cannot see, and the views a person uses to look. How to run them is in pipeline/README.md. -->

# The checks, and looking

## What a fault is

A fault is something wrong in a cut that a professional editor would fix without asking: a cut on a blink, a clipped word, two cameras that do not match, a caption on his mouth, a card too fast to read. Taste is what a professional would ask him about. When unsure, ask whether a professional would fix it without asking.

Not faults, for the checks, for you or for a fresh reviewer:

- which lines are kept, their order, and the length;
- the camera for each line where both are clean, and how tight a punch-in is;
- the opening: a title over the product, or over him;
- a card's wording or design;
- captions word for word at his speaking rate where joining a short one would break the safe line;
- a kept breath with his eyes shut, when cutting it would cut on a blink;
- room tone at the end, or a fade to silence;
- two real recordings that show slightly different numbers or times a few minutes apart;
- a deliberate spelling Josh has been asked about.

## The report

The pipeline's checks run once on the finished cut and write a report: one finding per row, with its frames, time, number and evidence image. They measure the pixels and the sound of the rendered file, and use the timeline's description only to know where the cuts, sound pieces, captions and graphics are meant to be. Every finding is a question for you: fix it on the timeline, or keep it with the frame and the reason the frames show it is not a fault here. A finding the evidence shows the instrument misread (a hand taken for a blink, a book spine read as a caption) is an instrument error, noted for the end of the video. Never write your own copy of a check: two instruments measuring one thing their own ways disagree, and then nobody knows which cut is right.

Every limit is meant as a limit of what a viewer notices, set from cold judges' calls on real cuts or from a published norm. Several rest on only one or two judged cuts, so a finding near its limit is a place to look, not a verdict.

**Picture**
- **Eyes shut at a cut:** eye openness under 0.65 of that shot's median within 3 frames either side of a cut on his face. A downward glance at his screen lowers it as a blink does; the evidence strip settles it. The 0.65 has no separately judged basis.
- **Lips out of sync:** 4 frames or more where the picture's moment and the sound's differ by more than 60 ms while he speaks with his face on screen; 1 to 3 frames is a place to look (two judged cuts). It needs each camera's picture offset from ingest: a camera timed by its own microphone reads early when that microphone is the lav's radio feed.
- **His head cut off:** any part of his head, hair included, cut by the frame's edge or the camera picture's edge, or under a panel or title, by 5% of his head's height or more for 3 frames or more. His head is Vision's face box widened by an allowance for his hair.
- **No face read:** a stretch where Vision found no face, so nothing about his eyes, mouth or head was checked there. A reason to look, never a pass.
- **Camera colour mismatch:** on his skin (nose and inner cheeks), a camera's red/green more than 0.015 above the reference camera's, or its blue/green more than 0.015 from it. Rests on two judged cuts: a paler wide camera with blue/green level was passed, a warmer one failed at every change.
- **Flash:** a clip above the cameras on screen for under 3 frames. **Black frame:** mean level under 8 of 255, outside the first and last 3 frames.

**Sound**
- **Joins** are the join checker's (`tools/audio.md`).
- **Loudness:** -14 LUFS integrated within 1 LU, true peak at most -1 dBTP, on the whole delivered file only.

**Captions**
- **Caption on his face:** his lower lip less than the look's clearance above the band's top (`look.json`, `subtitles.faceClearance`). On two judged cuts, every frame a judge called "captions over his face" had the band within 113 px of his lip, and every frame passed had 130 px or more.
- **Caption past the safe line:** a caption's pill or letters into the platforms' button column or its mirror on the left.
- **Highlight late or early:** after a pause, the first lit word more than 3 frames from the onset of his voice (judged cuts called 4 frames late). Inside connected speech a closure inside a word and the gap between two words look alike on the level, so the check cannot fail there: the word aligner is the instrument, and the words it doubts are the places to look on the spectrogram.
- **Caption word with no sound:** a lit word he is not heard saying. It needs a transcription of the file's own sound.
- **Every caption page,** with its frames and the text read off it, for you to read for a phrase broken mid-thought.

**Graphics**
- **Text under the platforms' top bar:** a line whose top is above y 200 of 1920. **Text too small at phone width:** a line under 13 px tall at 390 px wide, while a panel or title is on screen. Text is read once a second, so a label near the top bar is checked by eye over its whole time on screen.

## What the checks cannot see

A face touch; face size and background across a camera change; a bare jump cut; his eyes anywhere but at cuts, including the frame a graphic leaves; whether a pill covers its word; a card's reading time; a card cropped mid-card or a sliver of the next one; encoding breakup in fades and dark gradients; the story at a join; pitch, breath and meaning at a join; motion. These are your eyes', at the stage that owns them and again at finishing.

## Views for looking

Instruments find where to look; only frames, looked at, pass anything. A contact sheet is for finding, never for judging: it shrinks away an eyelid, a fingertip at a cheek, a pill a few pixels off its word, a one-frame sliver.

- **Frames from the timeline,** graded and framed, without a render: the pipeline's frame tool or the MCP's `get_image`, at full size and at phone width (390 px wide). A frame exported this way matched a one-frame render to within 1 level in 255 (17 Nov). It does not draw the caption track: to see captions, render a one-frame still.
- **Frames from the camera files,** by source frame, with no Resolve: `ffmpeg -ss` before `-i` is frame-accurate on a constant-rate camera file, but check it once per file against `select=eq(n\,N)`, since a file with an unusual start time can be a frame out.
- **Consecutive frames** through anything that moves: one still can catch a transition halfway.
- **Side by side:** open a pair at 1300 to 1800 px wide or crop it at full size; a 2160 px pair shrunk by the viewer looks banded where full-size crops are smooth (22 Oct).
- **A frame-difference trace** (ffmpeg's `signalstats` `YDIF`, cropped to the card or panel) over the whole time a card or held highlight is up: a cut stands far above its neighbours (47 against 0.5 to 3, 22 Oct), and a spike where nothing should change is a sliver, a flash or content jumping.
- **Against the last version:** compare the two files frame by frame with the same preset on both sides (a phone render decodes about two levels darker than a master). Everything outside the intended change should be identical within encoding noise.

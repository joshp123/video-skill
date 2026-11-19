<!-- Written by AI on 2026.11.19 by model claude opus 5.5: the editor's brief, rewritten from the 29 Oct and 18 Nov files to the outcome, Josh's words, the facts of his rig and the practice a professional dialogue and picture editor brings. -->

# Editor

## Your outcome

Josh chose what the video says on the script page: his lines, in the order a viewer hears them. You make that play as if he said it once, well, to two cameras. Nobody sees or hears a cut, every line is on the camera that serves it, the proof on screen lands on the word that names it, and his speech is captioned so the video works muted.

Most of what Josh would call a fault is made or prevented here: a cut on a blink, a clipped consonant, a highlight a few frames late, a caption over his mouth, a hard sound join. None of those is taste, and none should reach him.

You come after the story and before colour, motion and finishing, as an editor works after the paper edit and before the grade and the online. Decide the whole cut from the text and the raw material first, then build it in one pass with the pipeline's first-cut builder (`pipeline/README.md`). An edit built one look and one change at a time costs hundreds of turns and hours of his waiting; one built from a complete set of decisions costs minutes.

## What you start from

- **The chosen script page:** his lines in viewing order, the real screen content under each, the caption tidy-ups he agreed, and what he left out.
- **The lav,** the only dialogue, padded onto the front camera's clock, so a lav second and a front-camera second are the same number. It is the rawest truth about where a word starts and ends; every transcript is an estimate of it.
- **The verbatim transcript,** which keeps every um, restart and cut-off word, so it shows each attempt at a line. Its word times locate a word and can be tenths of a second out (`tools/transcription.md`).
- **Both cameras,** with each camera's picture offset from `inventory.md`.
- **The face-touch scans** of both cameras.
- **The demo content** in `graphics/content/` and `content.md`: what each piece shows, which line it proves, and the exact text in it that can be lit.
- **Words on screen** in `words.md`.
- **The look** (`looks/<name>/look.json`): where the caption band sits, how wide a caption row may be, the parts of the frame the platforms cover, and how close his mouth may come to the band.
- **`record.md`,** for anything he has said about this video's pace, cameras, opening or ending.

## It plays as one take

He talks out of order; the cut must play coherently. The page fixed the lines and their order; you choose which attempt of each line plays and where it joins.

- **Keep his last complete take of a line** unless an earlier one is cleaner. He restarts because an attempt went wrong, so the last full run is usually the one he meant.
- **Never build one line from two attempts** when one clean run exists. Two attempts differ in energy, pitch, pace and distance from the lav, and a listener hears the seam even when the trace looks clean. The more of a line one piece carries, the fewer joins there are to hear.
- **A take he rejects aloud goes,** with the words he rejects it in ("no", "again", "let me redo that"). A restart on its own rejects nothing.
- **Read the words either side of every cut together,** as a viewer hears them. Inside a sentence, the sentence stays whole; between sentences, the second follows from the first. A join that does not read as one thought goes back to the story: look for his own link in the raw take (`roles/story-and-demo.md`).
- **Pace is his own speech, tidied.** Take out dead air, false starts, ums and repeated words where his meaning stands. Keep the pauses that carry meaning and the breath before a new thought.

## Nobody hears a cut

A listener tracks several things at once, and a cut is invisible when every one of them carries on across it. Nobody here can listen, so you prevent what an ear would catch, and the join checker measures what can be measured (`tools/audio.md`).

- **The room.** A gap never drops to digital silence or to a different noise: room tone from the same recording fills it.
- **How a word ends.** A voiced ending decays, and a final consonant has a release after its closure. A transcript's end time usually falls before both, so the edge goes in the pause after the decay, found from the level. The join placer does this; a weak consonant tail is what its checker catches least.
- **How a word begins.** A cut inside a plosive's closure (the silence before the burst of "p", "t" or "k") is safe; after the burst it clips. In connected speech there may be no silent point between two words: a cut there is heard, so choose another edge word or let the line play to a real pause.
- **Breath.** He breathes before a new thought. Take the breath away and the next sentence sounds spliced on. Keep it, and let the sound lead the picture where the picture allows (a J-cut).
- **Pitch and pause.** Before judging a join by pitch, look at how he ends a finished sentence in this take: speakers differ, and the textbook falling ending can be wrong for him. An unfinished-sounding end joined to a new sentence sounds like an interruption. Match the pauses he makes in this take; one fixed pause length makes him sound like someone else.
- **Energy.** Two stretches spoken with different energy, or at a different distance from the lav, sound like two recordings when they meet. Choose takes that sit together; a level step beyond about 6 dB between takes is heard.
- **Crossfades.** Every join is a short constant-power crossfade centred on the cut. Dialogue editors use 5 to 10 ms inside one take and 20 to 40 ms between takes. A crossfade plays half its length beyond the cut on both sides, so an edge cut tight against a click or a breath brings it back.

A join the checker flags comes back to you, never to Josh: move the edge into the pause, choose another edge word or another take, or keep it with a reason. Pitch, breath and meaning at a join are yours, by choosing takes and reading the words either side. When Josh has listened to a join and heard nothing wrong, it is done.

## Every line is on the camera that serves it

The front camera is eye contact: the promise, a claim, the ask. The wide camera shows gesture and him looking at his screen, and covers removed time. A punch-in on one camera is a deliberate cut inside one angle, to land a line or hide a jump. How much of each camera is a judgement for every line; alternating by position is no reason. Know the balance: seconds on each camera and on the tool.

A jump cut is never bare. When the same camera continues across removed time with his face on screen, his head jumps: change camera, punch in, or put the tool on screen over the join. Resolve's SmartSwitch chooses angles by who is speaking; with one speaker that says nothing about the story, so the choice stays yours.

## Clean frames

A viewer studies the first and last frame of every shot, and every frame where his face first appears, including the frame a graphic leaves and reveals him. On each of those his eyes are open (a glance down at his screen is fine), no hand is at his face, his mouth is not caught mid-grimace, and there is no blur from a head turn.

When the picture cut lands on a blink but the sound cut is right, move only the picture a few frames: a split edit. Watch the frames either side, because his mouth then moves to the outgoing words over the incoming sound. When every frame either camera has at that moment shows shut eyes, choose between a cutaway, letting the outgoing shot run on, another take, or dropping a word, a pause or a breath. That is your call while his meaning stands.

Cut every moment he touches his face, as a director would. Both cameras film the same moment, so a touch on one camera is a touch on both: cut round it, or cover it with the tool.

## The thumbnail and the ending

The first frame is the thumbnail, so it is the opening of the video, not a separate image. It says what this video is about, shows that a person is talking and what the tool is, and catches him with a natural expression, never an awkward one. What that looks like differs by video: when it is not obvious, show him a few first frames that differ in kind and let him pick by eye. Judge his expression at a size where you can see it, and search the whole take for it, not only the lines in the cut.

How the film ends is yours. The closing card holds long enough to read at phone size, and a viewer can act on it (`roles/motion.md`).

## The frame is built for a phone held upright

- **The same kind of shot has the same face size and eye line on both cameras,** so a change reads as one camera from two angles. Their lenses and positions differ, so they need different framing values: find this project's on real frames at full size.
- **His whole head, hair included, is inside the frame and clear of every graphic, in every shot.** The frame is an upright strip of a landscape picture, a third of its width, so slide it onto him shot by shot as he moves.
- **Sharpness has a limit you can work out.** From a 3840 by 2160 camera, a full-height 9:16 frame shows the source at 0.89 of its pixels, so a total zoom up to about 1.12 stays at native sharpness. Beyond that, judge the softness on a full-size frame.
- **Keep his hands in frame** when a gesture is the reason for choosing the wide camera.
- **Decide layouts with the cut:** him full frame; the tool above and him below; the tool, a photo or a card full frame. They decide which camera works and how long a line can stay on him.
- **The captions sit in one band for the whole video,** because the caption template takes one position for the subtitle track. Every layout keeps that band clear, over something dark enough for white type: light app footage goes in a panel above him. With a panel above him, his whole head fits under it with the look's clearance above the band; when it cannot, the tool takes the frame alone. If the band forces a layout you would not choose, say so to Josh with the cut: the band is part of the look, and the look is his.
- **What a viewer must read never sits under the platforms' top bar or in their button column,** over the whole time it is on screen.

## The proof lands on his word

Spot every graphic during the cut, because a graphic changes the cut: where it sits decides the camera, the framing and how long a line can run. The timing is yours, the design is the motion stage's and the content is the story's, kept apart so each changes alone. For each graphic decide its content, its layout and whether his face stays, when it comes in and leaves (on a camera cut or a spoken word; an edge a few frames from a picture cut reads as a mistake), what it lights on which of his words, and its reading time, counted from the first frame it is fully readable.

Anchor each graphic to his words rather than to frames, so it stays on its word when the cut moves.

## Captions read with his voice

You phrase and time every caption. Resolve's own captioning breaks lines by a count of characters, not by phrase, so the phrasing is yours, while the subtitle track, the template and its word highlight are Resolve's.

- **Phrasing.** One caption per phrase as it reads, broken where his phrasing breaks: no article left at the end of a row, no verb split from its object, no one-word orphan. One or two rows, each inside the look's safe line; on the signpost-pill look that is about 15 to 17 of his characters a row. Names spelt as the tool's README spells them. Numbers as professional subtitles write them: one to ten in words, larger in figures. A phrase wider than two rows cannot avoid a mid-phrase break at the look's type size: that goes to Josh with the cut, because the fix (smaller type, or accept the break) is a look decision.
- **His words, with only his tidy-ups.** A caption shows the words he says on the placed sound, plus the grammar tidy-ups he agreed on the page. A word the sound cut leaves out comes out of the caption too.
- **Timing.** A word lights on the frame his voice starts it and stays lit until the next word starts. In his look the pill walks the eye through his speech, so more than 3 frames early or late is a fault a viewer sees. Transcript times run early inside connected speech; the word aligner times captions on the placed sound, and a word it doubts is one to look at on the spectrogram.
- **Length.** A caption is never shorter than its words take to say. One up for under about half a second joins a neighbour when the joined phrase still fits the safe line.
- **Where captions hide.** No caption under a graphic that already shows his words, such as his request typing into an agent's box. An opening title held over his first words leaves them uncaptioned: start his words as the title leaves, or let the title carry them.

## Looking at the cut

Judge on full-size frames, one at a time, at full size and at phone width (390 px wide). A contact sheet is for finding where to look, never for judging: it shrinks away an eyelid, a fingertip at a cheek, a letter at a panel's edge. Frames come from the timeline without a render (`pipeline/README.md`, or the MCP's `get_image`), and from the camera files by source frame with no Resolve at all.

Before the cut moves on, read its words from start to end as a stranger hears them: every join reads as one thought, nothing is said twice, nothing refers to something not yet heard, and it ends on the ask.

The face-touch scans list candidate moments on each camera (`tools/cameras.md`). Open every one inside a kept shot, on both cameras.

## When he locks

The words, order, cameras, framing, layouts and graphic timings are fixed. A later change goes to him as an option, never silently.

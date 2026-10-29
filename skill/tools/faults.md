<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: what a fault is, how the gate measures each class and what it cannot see, and how to run it. Every number is checked against pipeline/b/qc.py. The dated calls behind the numbers are in history.md. -->

# Faults and the gate

## What a fault is

A fault is something wrong in a cut that a professional editor would fix without asking: a cut on a blink, a clipped word, two cameras that do not match, a caption on his mouth, a card too fast to read. Faults never reach Josh (SKILL.md, "The loop"). Taste is what a professional would ask him about, and is never a fault (below, "Not faults: taste"). When unsure, ask whether a professional would fix it without asking: if yes, it is a fault.

Each class below says what the viewer notices, the number that decides it, what that number rests on, and what measures it:

- **measured:** `pipeline/b/qc.py` measures it on the rendered file and fails the gate on it;
- **look:** the gate marks a place for a model to judge by eye, and does not fail on it;
- **listen:** a place only an ear can settle; nobody here can yet, so it is named for Josh;
- **eyes:** no instrument; the role that owns the class, finishing and the cold judge look for it.

Every number is a limit of what a viewer notices, set from cold judges' calls on real cuts or from a published norm, never a value measured on one recording. When a judge disagrees with the instrument, the number is reviewed. When the gate misses something a judge or Josh can see, the gate is what gets fixed.

## How the gate works

`qc.py` decodes the rendered file and reads the video's `edit-list.json`, the lav it names and the look's `look.json`. It never judges the list: it measures the pixels and the sound and uses the list to know where the cuts, the sound pieces, the captions and the graphics are meant to be.

- **Picture,** through `qc_vision.swift`: every frame read with AVFoundation and measured with Apple's Vision. For the largest face: its box, eye openness (eye height over eye width from the landmarks), nose and lip boxes, and the median skin colour of the nose and inner cheeks. For the caption band: its text lines and the lit pill's box, read again only when the band's white and orange pixels change. Once a second, every text line outside the band.
- **Sound,** decoded to mono at 48 kHz. Each sound piece of the list is found in the cut by matching its samples to the lav, so the gate knows each piece's real offset and level. A level trace every 5 ms finds word onsets in the cut's own sound.
- **Heard words,** when given (`--heard-words`, Resolve's transcription of the file's own sound by `word_times.py --media`), are paired in order with the lit caption words.

It writes `report.md`, `report.json` and an `evidence/` folder of images (frame strips, crops, level traces, spectrograms) into the video's `build/qc/<file name>/`, one row per finding with its class, frames, time, number and evidence. It exits 1 while any row is a fault. A row whose evidence shows it is wrong is an instrument error: log it with the frame, and fix the instrument, not the cut.

**What the gate cannot see:** a face touch; framing, face size and background across a camera change; a bare jump cut; his eyes anywhere but at segment starts; the content of a graphic and whether its pill covers its word; encoding breakup; the story at a join; how a join sounds; motion. Each role's file says which of these are its to look at, and finishing and the director look at all of them on the whole film.

## Running the gate

Any role runs it on the classes it is changing, through the video's lock for the Resolve steps, from the video's folder with Resolve's variables set (`tools/resolve.md`, "Driving it"). Never write a copy of its tests: two instruments measuring one class their own ways find different faults, and then nobody knows which cut is right.

**The level matters.** Every render the gate measures loads the delivery-loudness preset that `pipeline/b/loudness.py` wrote (`tools/audio.md`, "Level"). The sound tests measure levels; a render at the master's level can sit 11 dB under the delivery and pass or fail a different sound from the one Josh hears.

**A span,** in seconds for sound joins, frames for anything visual. `--range` takes timeline frames, both ends included:

```sh
L="/usr/bin/lockf -k -t 3600 scratch/resolve.lock /usr/bin/python3 -B"
$L ../pipeline/resolve/render_timeline.py PROJECT "NAME finish" scratch/ROLE/span.mp4 --preset phone --subtitles --range FIRST LAST --load-render-preset LOUDNESS
$L ../pipeline/b/word_times.py "NAME finish" --media scratch/ROLE/span.mp4 > scratch/ROLE/heard-span.json
../pipeline/.devenv/profile/bin/python3 ../pipeline/b/qc.py scratch/ROLE/span.mp4 --video-folder . --range FIRST LAST --heard-words scratch/ROLE/heard-span.json --only joins highlights
```

`--subtitles` burns the caption track in; without it the caption checks measure nothing. `--only` takes `eyes`, `sync`, `joins`, `loudness`, `captions`, `highlights`, `caption-edges`, `colour`, `text` and `flashes`. Loudness is never checked on a span. A span's phone render takes its bit rate from the span's length, so it encodes far better than the whole film and hides breakup: judge breakup on the whole file.

**The whole cut,** before anyone reviews it or it is sent on: finishing's commands in `roles/finishing.md`, "The fault gate". Without `--heard-words` the "caption word with no sound" class is not measured, and the report says so. A cut of about 100 s takes about a minute.

## Picture

**Eyes shut at a cut** (measured). His eyes are closed or closing within 3 frames either side of a cut on his face, so the cut reads as a cut on a blink.
- Decided by: eye openness below 0.65 of that shot's median.
- A cut on him is the first frame of each `segments` row. The pixels cross-check the list: a pixel cut on his face with no listed cut within 2 frames, or a listed cut the pixels do not show, is a "look" row, and so is the eye check at it. A hand across his face can make one.
- A downward glance at his screen lowers eye openness as a blink does; the evidence strip settles it.

**Lips out of sync, or a frozen picture while he speaks** (measured). We see his mouth from a different moment from the words we hear.
- Decided by: 4 frames or more where the picture's moment and the sound's moment differ by more than 60 ms, while the sound is at -30 dBFS or louder and his face is on screen. 1 to 3 frames is a "look" row: on the cuts judged so far, a cold judge did not count runs that short.
- The picture's moment comes from each segment's camera and source frame, and each camera's `picture_offset_s` in the list's `cameras` (picture measured against picture at ingest, `tools/cameras.md`). A camera without one is timed by its own microphone, and the report says so; on a camera whose microphone is the lav's radio feed, that reads its shots tens of milliseconds early. A judge checking by hand takes offsets from `inventory.md` for the same reason.

**Camera colour mismatch** (measured). The two cameras do not look like one camera from two angles.
- Decided by: on his skin (the nose and inner cheeks, the median of the pixels between the 20th and 95th percentile of lightness, per shot, then per camera), a camera's red/green ratio at most 0.015 above the reference camera's, and its blue/green within 0.015 of it. The reference is the camera `cameras` marks `reference`.
- Rests on two judged cuts: a wide camera paler than the front with blue/green level was passed; one warmer by more than these limits was failed on every camera change. Warmer is what the eye catches as a different room. One row per camera pair, listing every change between them.

**Flash** (measured). A clip on V2 or above on screen for under 3 frames, from the list.

**Black frame** (measured). A frame whose mean level is under 8 of 255, other than the first and last 3 frames.

**Picture breaks up** (eyes). Blocks or streaks from encoding, mostly in fades and dark gradients. The `phone` preset can break fades into blocks at its bit rate, so judge it on the `post` file at full size, and on a whole-film render.

**Frozen end frame or an odd held expression** (eyes). A held frame under speech is measured above; a held frame with no speech, and an ending that stares at a freeze of his face, are for eyes.

## Sound

**Clipped word at a sound join** (measured). A sound piece starts or ends inside his speech, so part of a word plays and is cut off. Either test decides it, measured on the lav through the piece's real offset and level:
- **A fragment.** The kept side holds a word's start or end within 250 ms of the edge (a rise of 10 dB or more out of a level under -33 dBFS), and the dropped side carries on at -25 dBFS or louder. 250 ms is about a syllable.
- **Through a word.** The lav is at speech level, -30 dBFS or louder, for the whole 40 ms around the edge.
- An edge where the source runs on unbroken into the next piece is not a join.

An edge just after an unvoiced consonant has to pass both tests at once: the dropped side under the fragment line, and a fade-in that ends before the next word's rise.

**Hard sound join** (measured; sometimes listen). The sound stops or starts more sharply than his voice does at that point. Decided by the steepest 20 ms change of level within 60 ms of the edge, against the lav's own change at the same moment. A fault when all hold:
- the step is 6 dB or more;
- the louder side is at -30 dBFS or louder, or 12 dB or more above the room tone within 100 ms of the edge (a weak word tail cut into room tone after a short fade sits under -30 dBFS and is still heard as a chop);
- the step is 10 dB or more steeper than the lav's.

A step 6 to 10 dB steeper than the lav's is a "listen" row.

**Loudness** (measured, whole file only). -14 LUFS integrated within 1 LU, true peak at most -1 dBTP (ffmpeg `ebur128`). Measured on the delivered file, because the encode can raise a peak.

**A join that sounds like an edit** (listen). A level trace and a spectrogram do not show it (`tools/audio.md`, "Seeing a join"). Until a listening route is established, name at most three such moments for Josh.

## Captions

**Caption word with no sound** (measured, needs `--heard-words`). A lit word he is not heard saying, such as a word left in a caption after the sound piece under it was cut short.
- Decided by: the lit words and the heard words aligned in order; a lit word with no heard partner within 2 s is a fault when at least half its lit frames are under -38 dBFS.
- A lit word with no partner over sound is a "look" row: usually an OCR slip or a spelling ("1" for "a", "$600" for "six hundred").

**Caption on his face** (measured). The caption band sits on his mouth or nose, or too close under his lip. Decided by the look: his lower lip's lowest point, from Vision's landmarks on every frame, at least `subtitles.faceClearance.lowerLipToBandTopPx` above the band's top (`look.json`). One row per run of frames.

**Caption past the safe line** (measured). A caption's pill or letters run into the button column (right of the look's `fusion.safeArea.buttonsLeft`) or past its mirror on the left, below `buttonsTop`. Decided on every frame: the white letters and orange pill across the middle half of each caption line's height, joined while the gap is 40 px or less. `captions.py` warns on the same line before the build.

**Highlight late or early** (measured after a pause; look inside connected speech). The pill lights more than 3 frames before or after he starts the word. In his look the pill walks the eye through his speech, so a viewer sees it miss.
- An onset is a rise of 10 dB or more within 80 ms, out of a dip of at least 30 ms, reaching speech, on the cut's own sound. After a pause (100 ms under -33 dBFS) a rise can only be a word's start, so the first word lit after a pause is measured against the rise nearest its lit frame, and more than 3 frames either way is a fault.
- Inside connected speech, a closure inside a word ("brea|king") and the gap between two words look alike on the level, so the gate cannot fail there. Where Resolve's heard word and a rise agree on an onset that the lit frame misses by more than 3 frames, and no rise sits at the lit frame, it writes a "look" row with a spectrogram: a yellow line at the lit frame, red at the rise. Judge each by reading the spectrogram against the words. Most are Resolve's word time running late; a few are real early highlights, typically on the word after a very short one.
- `align.py` gives the start of each known word on the placed sound (`roles/editor.md`, "Word times on the placed sound"). Once it is proven on his real voice and the gate reads it, this class becomes measured in connected speech too, at the same 3 frames, and the look rows go.
- The report lists every lit word with its first frame, as read by OCR.

**Caption page broken mid-phrase** (eyes; the report lists every page). A page ends inside a phrase: an article left at the end, a verb split from its object, the next sentence's first word, a one-word orphan page. Reading decides this, not a count.
- The report lists every page with its frames and the text read off them, and marks one-word pages as "look" rows. Resolve's template can split a caption into pages by its own rule (a word over 25 frames after the last), so compare the page list with the list's captions.
- A break no paging inside the safe line can avoid comes from a phrase wider than one row at the look's type size. It is not a fault: the director names it to Josh with the look (smaller type, or accept the break).

**Pill does not cover its word** (eyes). Josh: "your subtitles and pills and highlights on terminal stuff do NOT properly cover words and look WRONG". At full size on the frame it arrives: the whole ink covered, even padding, touching nothing else.

**Caption too short to read** (eyes). A caption is never shorter than its words take to say. One up for under about 0.5 s joins a neighbour when the joined page fits the safe line; when it cannot, it stays, and that is taste.

**Caption too fast to read** (eyes; the pace is taste). Captions follow his speech, so their pace is his; condensing his words to slow it is his call, raised by the director from finishing's pace numbers. About three words a second finds the captions worth reading again at phone width.

## Graphics

**Card or title too fast to read** (eyes until the gate measures it; a fault, because cards and titles are the crew's). Josh, on screens that did not stay up: "honestly this is all too fast to see".
- Decided by: fully readable for less than about a third of a second per word plus half a second, counted from the first frame its text is fully readable (not the start of its entrance) to the first frame of its exit. One reading job at a time: a card over a terminal the viewer is also reading counts the words of both.
- Rests on the reading speeds professional subtitlers work to (Netflix 20 characters a second, the BBC 160 to 180 words a minute), plus a moment to find the card. Josh found a seven-word card too fast at 1.5 s.
- Finishing times every card and title from frames (`tools/checking.md`, "Reading time and flashes").

**Graphic clipped, unreadable or stray** (partly measured). From Vision's text lines, once a second, outside the caption band:
- **Text under the platforms' top controls** (measured): any line whose top is above y 200 of 1920.
- **Text too small at phone width** ("look"): a line under 13 px tall at 390 px wide, about Apple's smallest text size. Only while a panel or title is on screen, so text in the room behind him is not flagged on camera shots.

What only eyes find: a card cropped mid-card, a sliver of the next card at an edge, a frozen pointer, the screen showing through a title band, a label (not a caption) in the button column, content mis-sized or mistimed, and content that moves under a held highlight (`tools/checking.md`, "A frame-difference trace"). Look at every graphic's first and last frame at full size and at 390 px wide.

## Opening and ending

**First frame mid-word or with an odd expression** (eyes). The first frame is the thumbnail.

**Abrupt ending** (eyes). The sound or the picture stops dead.

## Not faults: taste

Taste is Josh's. Never change it without him and never count it as a fault:

- which lines are kept, their order, and the length;
- the camera for each line where both are clean, and how tight a punch-in is;
- the opening: a title over the product, or over him;
- a card's wording or design;
- captions word for word at his speaking rate where joining a short one would break the safe line;
- a kept breath with his eyes shut, when cutting it would cut on a blink;
- room tone at the end, or a fade to silence;
- two real recordings that show slightly different numbers or times a few minutes apart;
- a deliberate spelling Josh has been asked about.

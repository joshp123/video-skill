<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: what a fault is, how the gate measures each class and what it cannot see, and how to run it. Updated by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: the sound-join classes moved to pipeline/joins, the gate run by cut.py, a flag decided by the model. Every number is checked against pipeline/b/qc.py. The dated calls behind the numbers are in history.md. -->

# Faults and the gate

## What a fault is

A fault is something wrong in a cut that a professional editor would fix without asking: a cut on a blink, a clipped word, two cameras that do not match, a caption on his mouth, a card too fast to read. Faults never reach Josh (SKILL.md, "Invariants"). Taste is what a professional would ask him about, and is never a fault (below, "Not faults: taste"). When unsure, ask whether a professional would fix it without asking: if yes, it is a fault.

Each class below says what the viewer notices, the number that decides it, what that number rests on, and what measures it:

- **measured:** `pipeline/b/qc.py` measures it on the rendered file and fails the gate on it;
- **look:** the gate marks a place for a model to judge by eye, and does not fail on it;
- **listen:** a place only an ear can settle; nobody here can, so it is named for Josh with the cut;
- **eyes:** no instrument; you look for it at the stage that owns it, again at finishing, and the cold look sees it fresh.

Every number is a limit of what a viewer notices, set from cold judges' calls on real cuts or from a published norm, never a value measured on one recording. Several rest on only one or two judged cuts; each class says what its number rests on, so you know how much to trust it.

**The gate finds; you decide.** A fault row is fixed in the plan by default. You may keep one only with its frame, its evidence image, and the reason the frames show it is not a fault here, written in the `why` of the plan entry it belongs to; the cold look sees what you kept. When the cold look or Josh sees a fault the gate missed, fix the cut now, and note the gap in the instrument for the end of the video. A number that keeps disagreeing with what you see on the frames is reviewed then.

## How the gate works

`qc.py` decodes the rendered file and reads the video's `edit-list.json`, the lav it names and the look's `look.json`. It never judges the list: it measures the pixels and the sound and uses the list to know where the cuts, the sound pieces, the captions and the graphics are meant to be.

- **Picture,** through `qc_vision.swift`: every frame read with AVFoundation and measured with Apple's Vision. For the largest face: its box, eye openness (eye height over eye width from the landmarks), nose and lip boxes, and the median skin colour of the nose and inner cheeks. For the caption band: its text lines and the lit pill's box, read again only when the band's white and orange pixels change. Once a second, every text line outside the band.
- **Sound,** decoded to mono at 48 kHz. Each sound piece of the list is found in the cut by matching its samples to the lav, so the gate knows each piece's real offset and level. A level trace every 5 ms finds word onsets in the cut's own sound.
- **Heard words,** when given (`--heard-words`, Resolve's transcription of the file's own sound by `word_times.py --media`), are paired in order with the lit caption words.

It writes `report.md`, `report.json` and an `evidence/` folder of images (frame strips, crops, level traces, spectrograms) into the video's `build/qc/<timeline>/`, one row per finding with its class, frames, time, number and evidence. It exits 1 while any row is a fault. A row whose evidence shows the instrument misread the frame (a hand taken for a blink, a book spine read as a caption) is kept with that frame as its reason and noted as an instrument error for the end of the video.

**What the gate cannot see:** a face touch; framing, face size and background across a camera change; a bare jump cut; his eyes anywhere but at cuts; the content of a graphic and whether its pill covers its word; encoding breakup; the story at a join; how a join sounds beyond what the join check measures; motion. Each stage's file says which of these are its to look at, and finishing looks at all of them on the whole film.

## Running the gate

`cut.py` runs the gate on every whole render (every check but joins, which the join check covers) and lists its fault rows; its look rows are in `report.md`. To run it yourself, on a whole render or on the span you are changing, from the pipeline devenv with absolute paths:

```sh
cd pipeline && devenv shell -- python3 b/qc.py FILE --edit-list EDIT_LIST --out DIR [--range FIRST LAST] [--only CHECK ...] [--heard-words HEARD.json]
```

`--only` takes `eyes`, `flashes`, `sync`, `loudness`, `captions`, `highlights`, `caption-edges`, `colour` and `text`. `--range` takes timeline frames, both ends included, for a file rendered over that span:

```sh
/usr/bin/python3 -B pipeline/b/render.py EDIT_LIST --timeline "NAME finish" --out SPAN.mp4 --preset phone --range FIRST LAST --loudness PRESET
```

Render every span the gate measures with the loudness preset, so its level is the delivery's: the checks measure levels, and a render at another level passes or fails a different sound from the one Josh hears. Loudness is never checked on a span. A span's phone render takes its bit rate from the span's length, so it encodes far better than the whole film and hides breakup: judge breakup on the whole file. To check the joins in a span, give `joins check --audio SPAN.mp4` each join's time in the span's own seconds (the edit list's `record_s` for each piece after the first, less FIRST divided by the frame rate). `qc.py` needs ffmpeg, ffprobe and Xcode's `swiftc` on the `PATH`; it compiles `qc_vision.swift` into the report folder when the binary there is missing or older than the source. A cut of about 100 s takes 11 to 47 s.

`--heard-words` is Resolve's transcription of the file's own sound (`word_times.py NAME --media FILE`); without it, which is how `cut.py` runs, the "caption word with no sound" class and the connected-speech highlight rows are not measured, and the report says so.

## Picture

**Eyes shut at a cut** (measured). His eyes are closed or closing within 3 frames either side of a cut on his face, so the cut reads as a cut on a blink.
- Decided by: eye openness below 0.65 of that shot's median.
- A cut on him is the first frame of each `segments` row. The pixels cross-check the list: a pixel cut on his face with no listed cut within 2 frames, or a listed cut the pixels do not show, is a "look" row, and so is the eye check at it. A hand across his face can make one.
- A downward glance at his screen lowers eye openness as a blink does; the evidence strip settles it.
- Rests on: the 3-frame window, because cuts checked on their first frame alone passed blinks a viewer saw. The 0.65 has no separately judged basis recorded: treat a row near it as a place to look.

**Lips out of sync, or a frozen picture while he speaks** (measured). We see his mouth from a different moment from the words we hear.
- Decided by: 4 frames or more where the picture's moment and the sound's moment differ by more than 60 ms, while the sound is at -30 dBFS or louder and his face is on screen. 1 to 3 frames is a "look" row. Rests on: two judged cuts, on which a cold judge did not count runs that short.
- The picture's moment comes from each segment's camera and source frame, and each camera's `picture_offset_s` in the list's `cameras` (picture measured against picture at ingest, `tools/cameras.md`). A camera without one is timed by its own microphone, and the report says so; on a camera whose microphone is the lav's radio feed, that reads its shots tens of milliseconds early. A judge checking by hand takes offsets from `inventory.md` for the same reason.

**Camera colour mismatch** (measured). The two cameras do not look like one camera from two angles.
- Decided by: on his skin (the nose and inner cheeks, the median of the pixels between the 20th and 95th percentile of lightness, per shot, then per camera), a camera's red/green ratio at most 0.015 above the reference camera's, and its blue/green within 0.015 of it. The reference is the camera `cameras` marks `reference`.
- Rests on two judged cuts and no more: a wide camera paler than the front with blue/green level was passed; one warmer by more than these limits was failed on every camera change. So 0.015 is a narrow basis. Warmer is what the eye catches as a different room; a row just past the limit is a strong case for a still pair and the cold judge, not a verdict. One row per camera pair, listing every change between them.

**Flash** (measured). A clip on V2 or above on screen for under 3 frames, from the list.

**Black frame** (measured). A frame whose mean level is under 8 of 255, other than the first and last 3 frames.

**Picture breaks up** (eyes). Blocks or streaks from encoding, mostly in fades and dark gradients. The `phone` preset can break fades into blocks at its bit rate, so judge it on the `post` file at full size, and on a whole-film render.

**Frozen end frame or an odd held expression** (eyes). A held frame under speech is measured above; a held frame with no speech, and an ending that stares at a freeze of his face, are for eyes.

## Sound

**Sound joins** (measured, by `pipeline/joins/joins check`, not the gate). A word cut short, a clipped start, a scrap of a removed word, a click, a jump in room sound, a cut inside connected speech. `cut.py` scores every join in the rendered sound and lists each flagged one; what the check is and what it misses is in `tools/audio.md`. The gate's own October join classes, hand-set levels that fitted his microphone and flagged 17% of clean joins on other voices, were retired on 17 Nov.

**Loudness** (measured, whole file only). -14 LUFS integrated within 1 LU, true peak at most -1 dBTP (ffmpeg `ebur128`). Measured on the delivered file, because the encode can raise a peak.

**A join that sounds like an edit** (listen). Pitch, breath and meaning at a join: the join check does not measure them, and a level trace and a spectrogram do not show them (`tools/audio.md`). Name at most three such moments for Josh with the cut.

## Captions

**Caption word with no sound** (measured, needs `--heard-words`, which `cut.py` does not pass). A lit word he is not heard saying, such as a word left in a caption after the sound piece under it was cut short.
- Decided by: the lit words and the heard words aligned in order; a lit word with no heard partner within 2 s is a fault when at least half its lit frames are under -38 dBFS.
- A lit word with no partner over sound is a "look" row: usually an OCR slip or a spelling ("1" for "a", "$600" for "six hundred").

**Caption on his face** (measured). The caption band sits on his mouth or nose, or too close under his lip. Decided by the look: his lower lip's lowest point, from Vision's landmarks on every frame, at least `subtitles.faceClearance.lowerLipToBandTopPx` above the band's top (`look.json`). One row per run of frames. Rests on: two judged cuts, on which every frame a judge called "captions over his face" had the band within 113 px of his lip and every frame passed had 130 px or more.

**Caption past the safe line** (measured). A caption's pill or letters run into the button column (right of the look's `fusion.safeArea.buttonsLeft`) or past its mirror on the left, below `buttonsTop`. Decided on every frame: the white letters and orange pill across the middle half of each caption line's height, joined while the gap is 40 px or less. `captions.py` warns on the same line before the build.

**Highlight late or early** (measured after a pause; look inside connected speech). The pill lights more than 3 frames before or after he starts the word. In his look the pill walks the eye through his speech, so a viewer sees it miss. Rests on: judged cuts where a highlight 4 frames late was called; nothing tighter has been judged.
- An onset is a rise of 10 dB or more within 80 ms, out of a dip of at least 30 ms, reaching speech, on the cut's own sound. After a pause (100 ms under -33 dBFS) a rise can only be a word's start, so the first word lit after a pause is measured against the rise nearest its lit frame, and more than 3 frames either way is a fault.
- Inside connected speech, a closure inside a word ("brea|king") and the gap between two words look alike on the level, so the gate cannot fail there. Where Resolve's heard word and a rise agree on an onset that the lit frame misses by more than 3 frames, and no rise sits at the lit frame, it writes a "look" row with a spectrogram: a yellow line at the lit frame, red at the rise. Judge each by reading the spectrogram against the words. Most are Resolve's word time running late; a few are real early highlights, typically on the word after a very short one.
- Inside connected speech these look rows need `--heard-words`; without them (as `cut.py` runs), the forced alignment that times the captions is the instrument, and its `doubtful_words` in the assemble report are the places to look on the spectrogram; move a word that is off with the caption's `word_starts_s` in the plan.
- The report lists every lit word with its first frame, as read by OCR.

**Caption page broken mid-phrase** (eyes; the report lists every page). A page ends inside a phrase: an article left at the end, a verb split from its object, the next sentence's first word, a one-word orphan page. Reading decides this, not a count.
- The report lists every page with its frames and the text read off them, and marks one-word pages as "look" rows. Resolve's template can split a caption into pages by its own rule (a word over 25 frames after the last), so compare the page list with the list's captions.
- A break no paging inside the safe line can avoid comes from a phrase wider than one row at the look's type size. It is not a fault: it goes to Josh with the cut as a look decision (smaller type, or accept the break).

**Pill does not cover its word** (eyes). Josh: "your subtitles and pills and highlights on terminal stuff do NOT properly cover words and look WRONG". At full size on the frame it arrives: the whole ink covered, even padding, touching nothing else.

**Caption too short to read** (eyes). A caption is never shorter than its words take to say. One up for under about 0.5 s joins a neighbour when the joined page fits the safe line; when it cannot, it stays, and that is taste.

**Caption too fast to read** (eyes; the pace is taste). Captions follow his speech, so their pace is his; condensing his words to slow it is his call, raised with the cut when a caption flashes by. About three words a second finds the captions worth reading again at phone width.

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

## Not faults

The checks, you and the cold look never count these as faults. Who decides each is a separate question, answered in SKILL.md, "What is his, and what is yours": the lines, their order, the look and the words on screen are his; the camera for each line, a punch-in and the rest of the craft are yours, without asking him.

- which lines are kept, their order, and the length;
- the camera for each line where both are clean, and how tight a punch-in is;
- the opening: a title over the product, or over him;
- a card's wording or design;
- captions word for word at his speaking rate where joining a short one would break the safe line;
- a kept breath with his eyes shut, when cutting it would cut on a blink;
- room tone at the end, or a fade to silence;
- two real recordings that show slightly different numbers or times a few minutes apart;
- a deliberate spelling Josh has been asked about.

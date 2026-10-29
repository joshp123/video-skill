<!-- Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream A, the fault instrument). Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). Highlight timing, the caption safe line, short captions, unavoidable breaks and the wide camera's sound: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). Rewritten by AI on 2026-10-29 by Claude Opus 5.5 against the mission: history moved to history.md, each rule once, changes listed in the commit. -->

# Faults

A fault is something wrong in a cut that a professional editor would fix without asking; it never reaches Josh (SKILL.md, "The loop", step 5).

Each class below says what the fault is, the number that decides it, and what measures it. `pipeline/b/qc.py` measures every class marked **measured** on the rendered file. A class marked **eyes** has no instrument; the finishing role and the cold judge look for it. Each number is a limit of what a viewer notices, set from cold judges' calls on real cuts or from a published norm, never a value measured on one recording (SKILL.md, "The loop"). Where a class rests on a particular call or norm, it says so. When a judge disagrees with the instrument, the number is what gets reviewed.

## Running the gate

The commands are in `roles/finishing.md`, "The fault gate". `qc.py` reads the cut, the video's `edit-list.json` and the lav named in it, and the look's `look.json`; without `--heard-words`, "caption word with no sound" is not measured and the report says so. It takes about a minute for a 100 s cut. Each row has a verdict:

- **fault** fails the gate.
- **look** is a place for a model to judge by eye.
- **listen** is a place only an ear can settle; name it for Josh.

If the frames show a fault row is wrong, log it as an instrument error with the frame, and fix the instrument, not the cut.

Any role runs the gate itself, never a copy of its tests. `--only joins` (or `eyes`, `sync`, `captions`, `highlights`, `caption-edges`, `colour`, `text`, `flashes`, `loudness`) runs just those checks; `--range FIRST LAST` reports only timeline frames FIRST to LAST. With `--range`, the cut may be a render of just that span (`render_timeline.py --range FIRST LAST --preset phone --load-render-preset NAME`, so its level is the delivery's): a sound join checks in seconds on a 200-frame render. Loudness is not checked on a span.

## Picture

**Eyes shut at a cut** (measured). His eyes are closed or closing within 3 frames either side of a cut on his face. The cut reads as a cut on a blink.
- Decided by: eye openness (eye height over eye width, from Apple Vision face landmarks) below 0.65 of the shot's median.
- A cut on him is the first frame of each camera segment in the edit list, and each shot is one segment.
- The pixels cross-check the list. A pixel change where his face jumps more than 5% of the frame, appears or goes, with no listed cut or graphic edge within 2 frames and his face still moved 2 frames later, is a "look" row; a hand across his face can make one. So is a listed cut the pixels do not show. An eye check at such a pixel-only cut is also a "look" row.
- Known false alarm: a downward glance at his screen lowers the number as a blink does. The evidence strip settles it.

**Lips out of sync, or picture frozen while he speaks** (measured). We see his mouth from a different moment from the words we hear, or a held frame while he talks.
- Decided by: 4 frames or more where the picture's moment and the sound's moment differ by more than 60 ms, while the sound is above -30 dBFS and his face is on screen.
- 1 to 3 frames is a "look" row: on the cuts judged so far, a cold judge did not count runs that short.
- The picture's moment comes from the edit list's `segments` (camera and source frame). A held segment has `speed_percent` under 100. The sound's moment comes from each sound piece's offset, measured by matching the cut's samples to the lav. Each camera's clock against the lav is measured from its own microphone.
- A judge who checks by hand takes each camera's picture offset from the session's `inventory.md` (picture measured against picture), never from a camera's own sound when that sound is a wireless mic. The wide camera's audio is the lav's radio feed, which arrives 30 to 60 ms after the picture, so an offset taken from it makes in-sync wide shots read tens of milliseconds ahead.

**Camera colour mismatch** (measured). The two cameras do not look like one camera from two angles. Josh's own note on an unmatched pair: "DJI is more saturated, nikon main cam is more flat".
- Decided by `roles/colour.md`: a camera's skin red/green may sit at most 0.015 above the reference camera's, and its blue/green within 0.015 of the reference camera's. The reference is the front camera. The limits rest on two judged cuts, one passed paler and one failed warmer (`roles/colour.md`, "Matched means his skin matches, measured").
- Skin is measured on his nose and inner cheeks, as the median of the pixels between the 20th and 95th percentile of lightness. Each shot gives a median, and each camera the median of its shots.
- One row per camera pair, listing every change between them.

**Flash** (measured). A clip on screen for under 3 frames, taken from the edit list.

**Black frame** (measured). A frame with a mean level under 8, other than the first and last 3 frames.

**Picture breaks up** (eyes). Blocks or streaks from encoding, often in fades and dark gradients. The `phone` preset breaks fades into blocks at its bit rate, so judge this on the `post` file (`roles/finishing.md`, "Rendering").

**Frozen end frame or an odd held expression** (eyes). Josh, on a cut that ended on a held frame: "make it fade out ... so we don't just stare at a freeze frame of me". A held frame under speech is measured above. A held frame with no speech is for eyes.

## Sound

**Clipped word at a sound join** (measured). A sound piece starts or ends inside his speech, so part of a word plays and is cut off.
- Decided by either of two tests, on the lav through the piece's measured offset and level:
  - **A fragment.** The kept side holds a word's start, or its end, within 250 ms of the edge: a rise of 10 dB or more out of a level under -33 dBFS. The dropped side carries on at -25 dBFS or louder. 250 ms is about one syllable.
  - **Through a word.** The lav is at speech level (-30 dBFS or louder) for the whole 40 ms around the edge.
- An edge where the source runs on unbroken into the next piece is not a join.

**Hard sound join** (measured, sometimes listen). The sound stops or starts more sharply than his voice does at that point.
- Decided by the steepest 20 ms level change within 60 ms of the edge, compared with the lav's change at the same moment.
- It is a fault when all of these are true:
  - the step is 6 dB or more
  - the louder side is at -30 dBFS or louder, or 12 dB or more above the room tone within 100 ms of the edge (a weak word tail cut into room tone after a short fade sits under -30 dBFS and is still heard as a chop; a cold judge heard one the gate had passed)
  - the step is 10 dB or more steeper than the lav's own change
- A step 6 to 10 dB steeper than the lav's is a "listen" row, for Josh's ears.

**Loudness** (measured). The delivered file must be -14 LUFS integrated, within 1 LU, and at most -1 dBTP true peak (ffmpeg `ebur128`).

**A join that sounds like an edit** (listen). A level trace and a spectrogram do not show this (`tools/audio.md`, "Seeing a join"). Name at most three moments for Josh.

## Captions

**Caption word with no sound** (measured, needs `--heard-words`). A lit word that he is not heard saying, such as a word left in the caption after the sound piece under it was cut short.
- Decided by: the lit word pairs with no heard word within 2 s, when the lit words and the heard words are aligned in order.
- It is a fault when at least half its lit frames are below -38 dBFS.
- A lit word with no pair over sound is a "look" row: usually an OCR slip or a spelling, such as "1" for "a" or "$600" for "six hundred".

**Caption on his face** (measured). The caption band sits on his mouth or nose, or too close under his lip.
- Decided by the look: his lower lip's lowest point must be at least `subtitles.faceClearance.lowerLipToBandTopPx` (120 px) above the band's top (`look.json`).
- The lip comes from Apple Vision landmarks on every frame. The band's top is the look's measured top for one or two lines.
- One row for each run of frames.

**Caption page broken mid-phrase** (eyes; the report lists every page). A page ends inside a phrase: an article left at the end, a verb split from its object, the next sentence's first word, or a one-word orphan page. Reading decides this, not a count.
- The report lists every page with its frames and text.
- It marks one-word pages as "look" rows.
- A break that no paging inside the safe line can avoid is not a fault: list it for the director, who names it to Josh with the look (smaller type, or accept the break). Such a break comes from a phrase wider than one row inside the safe line; how many characters fit a row is the look's (`roles/motion.md`, "The look").

**Highlight late or early** (measured after a pause; look inside connected speech). The pill lights more than 3 frames before or after he starts the word.
- An onset is a rise of 10 dB or more within 80 ms out of a dip of at least 30 ms, reaching speech, on the cut's own sound. After a pause (100 ms under -33 dBFS) it can only be a word's start: the first word lit after the pause began is measured against the rise nearest its lit frame (so a kept breath before the word does not count), and more than 3 frames either way is a fault.
- Inside connected speech a closure inside a word ("brea|king") and the gap between two words look alike on the level, so the instrument cannot fail the gate there. Where Resolve's heard word and a rise on the trace agree on an onset the lit frame misses by more than 3 frames, and no rise sits at the lit frame, it writes a "look" row with a spectrogram: yellow line at the lit frame, red at the rise. Judge every such row by reading the spectrogram against the words. Expect most of them to be Resolve's word time running late, and a few to be real early highlights, typically on the word after a one-frame word.
- A forced alignment of the known caption text to the placed sound would settle these onsets, and it is the planned instrument: when it lands, this class is measured in connected speech too, at the same 3 frames, and the "look" row goes. The escape is temporary, not a design.
- The report lists every lit word with its first frame, as found by OCR.

**Caption past the safe line** (measured). A caption's pill or letters run into the button column (right of `fusion.safeArea.buttonsLeft`, x 950) or past its mirror on the left (x 130), below `safeArea.buttonsTop`; `captions.py` warns on the same line before the build.
- Decided on every frame: the white letters and orange pill across the middle half of each caption line's height, joined while the gap is 40 px or less, must stay inside x 130 to 950.

**Caption too short to read** (eyes). A caption is never shorter than the words it carries take to say. One up for under about 0.5 s is joined to a neighbour when a page of the joined phrase fits the safe line, and otherwise stays: then it is taste.

**Pill does not cover its word** (eyes). Josh: the "pills and highlights on terminal stuff do NOT properly cover words and look WRONG". Check at full size.

**Caption too fast to read** (eyes; the pace is taste). Captions follow his speech, so their pace is his: condensing his words to slow it is his call, which the director raises with him from finishing's pace numbers (`roles/finishing.md`, "Captions on the track"). About three words a second finds the captions to look at again at phone width (`tools/checking.md`, "Reading time and flashes").

**Card or title too fast to read** (measured by the number below; `qc.py` does not measure it yet). His verdict on screens that were not up long enough: "honestly this is all too fast to see". Cards and titles are ours, so their reading time is a fault, not taste.
- Decided by: a card or title is fully readable for less than about a third of a second per word plus half a second. Count from the first frame its text is fully readable, not the start of its entrance, to the first frame of its exit. One reading job at a time: a card over a terminal the viewer is also reading counts the words of both.
- Rests on: the reading-speed norm professional subtitlers work to (Netflix 20 characters a second, the BBC 160 to 180 words a minute), plus a moment to find the card (`roles/motion.md`, "Motion and reading time"). Josh's own call sits inside it: a seven-word card up 1.5 s was too fast for him.
- Until `qc.py` measures it, the finishing role times every card and title from frames (`tools/checking.md`, "Reading time and flashes").

## Graphics

**Graphic clipped, unreadable or stray** (partly measured). What is measured, using Apple Vision text found every second outside the caption band:
- **Text under the platforms' top controls** is a fault: any text line whose top is above y 200.
- **Text smaller than 13 px tall at 390 px wide** is a "look" row. That is about 11 pt, Apple's smallest text size. It is measured only while the edit list has a panel or title on screen, so the book spine reading "Rotterdam" on the shelf behind him is not flagged on camera shots; beside a panel it still can be.

What only eyes find:
- a card cropped mid-card
- a sliver of the next card at an edge
- a frozen pointer
- the screen showing through a title band
- a label (not a caption) in the button column right of x 950 below y 900
- content that is mis-sized or mistimed

Look at every graphic's first and last frame at full size and at 390 px wide.

## Opening and ending

**First frame mid-word or with an odd expression** (eyes). The first frame is the thumbnail ("never shows him mid-word with an odd expression", `SKILL.md`).

**Abrupt ending** (eyes). The sound or picture stops dead.

## Not faults: taste

Taste is Josh's. Never fix it without him, and never count it as a fault. From the codex-switch judgement:

- which lines are kept, their order, and the length (B's 1:44 against A's 1:18)
- the camera for each line, punch-ins and how tight they are (B's 20 to 25%)
- the opening: a title over the product, or over a held frame of his face
- a card's wording or design, quotation marks round a quoted line
- captions word for word at his speaking rate, even when some are up for under a second, where joining one to a neighbour would break the safe line ("Caption too short to read")
- a kept breath with his eyes shut, when cutting it would cut on a blink
- room tone at the end, or a fade to silence
- two real recordings that show "12:54" and "12:56" a few minutes apart
- the lav transmitter's light reading as a dot between caption words
- a deliberate spelling Josh has been asked about ("pulls" to "pools")

When unsure, ask whether a professional would fix it without asking. If yes, it is a fault; if they would ask him, it is taste.

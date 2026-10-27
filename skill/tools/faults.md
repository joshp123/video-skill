<!-- Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream A, the fault instrument). Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). Highlight timing, the caption safe line, short captions, unavoidable breaks and the wide camera's sound: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). -->

# Faults

A fault is something wrong in a cut that a professional editor would fix without asking; it never reaches Josh (SKILL.md, "The loop", step 5).

Each class below says what the fault is, the number that decides it, and what measures it. `pipeline/b/qc.py` measures every class marked **measured** on the rendered file. A class marked **eyes** has no instrument; the finishing role and the cold judge look for it.

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
- The pixels cross-check the list. A pixel change where his face jumps more than 5% of the frame, appears or goes, with no listed cut or graphic edge within 2 frames and his face still moved 2 frames later, is a "look" row. A hand across his face can still make one (run 4, frame 2173). So is a listed cut the pixels do not show. An eye check at such a pixel-only cut is also a "look" row.
- Known false alarm: a downward glance at his screen lowers the number as a blink does (run 2, frame 1527). The evidence strip settles it.

**Lips out of sync, or picture frozen while he speaks** (measured). We see his mouth from a different moment from the words we hear, or a held frame while he talks.
- Decided by: 4 frames or more where the picture's moment and the sound's moment differ by more than 60 ms, while the sound is above -30 dBFS and his face is on screen.
- 1 to 3 frames is a "look" row. A cold judge did not count those on either cut.
- The picture's moment comes from the edit list's `segments` (camera and source frame). A held segment has `speed_percent` under 100. The sound's moment comes from each sound piece's offset, measured by matching the cut's samples to the lav. Each camera's clock against the lav is measured from its own microphone.
- A judge who checks by hand takes each camera's picture offset from the session's `inventory.md` (picture measured against picture), not from a camera's own sound when that sound is a wireless mic: the Pocket's audio is the lav's radio feed, which arrives 30 to 60 ms after the picture, and on run 4 a cold judge measured the wide shots 58 ms ahead that way when they were 8 to 18 ms off.

**Camera colour mismatch** (measured). The two cameras do not look like one camera from two angles. Josh's own note on an unmatched pair: "DJI is more saturated, nikon main cam is more flat".
- Decided by `roles/colour.md`: a camera's skin red/green may sit at most 0.015 above the reference camera's, and its blue/green within 0.015 of the reference camera's. The reference is the front camera.
- Skin is measured on his nose and inner cheeks, as the median of the pixels between the 20th and 95th percentile of lightness. Each shot gives a median, and each camera the median of its shots.
- One row per camera pair, listing every change between them.

**Flash** (measured). A clip on screen for under 3 frames, taken from the edit list.

**Black frame** (measured). A frame with a mean level under 8, other than the first and last 3 frames.

**Picture breaks up** (eyes). Blocks or streaks from encoding, often in fades and dark gradients. Run 2's closing fade streaked across his face.

**Frozen end frame or an odd held expression** (eyes). Josh, 17 Oct, on a cut that ended on a held frame: "make it fade out ... so we don't just stare at a freeze frame of me". A held frame under speech is measured above. A held frame with no speech is for eyes.

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
  - the louder side is at -30 dBFS or louder, or 12 dB or more above the room tone within 100 ms of the edge (a weak word tail cut into room tone after a short fade sits under -30 dBFS and is still heard as a chop: run 4, "here" at 50.43 s, found by a cold judge after the gate passed it)
  - the step is 10 dB or more steeper than the lav's own change
- A step 6 to 10 dB steeper than the lav's is a "listen" row, for Josh's ears.

**Loudness** (measured). The delivered file must be -14 LUFS integrated, within 1 LU, and at most -1 dBTP true peak (ffmpeg `ebur128`).

**A join that sounds like an edit** (listen). A level trace and a spectrogram do not show this (`tools/audio.md`, "Seeing a join"). Name at most three moments for Josh.

## Captions

**Caption word with no sound** (measured, needs `--heard-words`). A lit word that he is not heard saying. Run 3 lit "here" over silence because the sound piece ended after "app".
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
- A break that no paging inside the safe line can avoid is not a fault: list it for the director, who names it to Josh with the look (smaller type, or accept the break). Run 4 had five, among them "window positioning." and "Nobody's breaking down", each wider than the line on one row.

**Highlight late or early** (measured after a pause; look inside connected speech). The pill lights more than 3 frames before or after he starts the word.
- An onset is a rise of 10 dB or more within 80 ms out of a dip of at least 30 ms, reaching speech, on the cut's own sound. After a pause (100 ms under -33 dBFS) it can only be a word's start: the first word lit after the pause began is measured against the rise nearest its lit frame (so a kept breath before the word does not count), and more than 3 frames either way is a fault. Run 4: "out" lit 4 frames late on builds 14 and 15.
- Inside connected speech a closure inside a word ("brea|king") and the gap between two words look alike on the level, so the instrument cannot fail the gate there. Where Resolve's heard word and a rise on the trace agree on an onset the lit frame misses by more than 3 frames, and no rise sits at the lit frame, it writes a "look" row with a spectrogram: yellow line at the lit frame, red at the rise. Judge every such row by reading the spectrogram against the words. On run 4's build 14 these rows held the judge's two early highlights ("down" after a one-frame "breaking", "don't" after a one-frame "please") among eleven others, most where Resolve's word time was late.
- The report lists every lit word with its first frame, as found by OCR.

**Caption past the safe line** (measured). A caption's pill or letters run into the button column (right of `fusion.safeArea.buttonsLeft`, x 950) or past its mirror on the left (x 130), below `safeArea.buttonsTop`; `captions.py` warns on the same line before the build.
- Decided on every frame: the white letters and orange pill across the middle half of each caption line's height, joined while the gap is 40 px or less, must stay inside x 130 to 950.
- Run 4's build 14: the pill on "Nobody's breaking" from x 118 to 965.

**Caption too short to read** (eyes). A caption is never shorter than the words it carries take to say. One up for under about 0.5 s is joined to a neighbour when a page of the joined phrase fits the safe line, and otherwise stays: then it is taste. Run 4: lengthening a 0.33 s caption to one row put its letters 19 px into the button column, a fault the gate caught.

**Pill does not cover its word** (eyes). Josh, 16 Oct: the "pills and highlights on terminal stuff do NOT properly cover words and look WRONG". Check at full size.

**Caption or card too fast to read** (eyes). His verdict on screens that were not up long enough: "honestly this is all too fast to see".
- About three words a second finds the ones to look at again at phone width (`tools/checking.md`).
- On where-was-i he found a seven-word card too fast at 1.5 s and did not raise it at 2.5 s.
- Captions follow his speech, so their pace is his. Cards and titles are ours.

## Graphics

**Graphic clipped, unreadable or stray** (partly measured). What is measured, using Apple Vision text found every second outside the caption band:
- **Text under the platforms' top controls** is a fault: any text line whose top is above y 200.
- **Text smaller than 13 px tall at 390 px wide** is a "look" row. That is about 11 pt, Apple's smallest text size. It is measured only while the edit list has a panel or title on screen, so a book spine behind him ("Rotterdam" on runs 2 to 4) is not flagged on camera shots; beside a panel it still can be.

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

<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); one line for the finish timeline by Claude Opus 5.5 (hill-climb stream J2) the same day. Caption row length and held highlights: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). Rewritten by AI on 2026-10-29 by Claude Opus 5.5 against the mission: history moved to history.md, each rule once, changes listed in the commit. -->

# Motion designer

Your outcome: every graphic in the video, in the look Josh picked, above the cameras: the tool on screen, his photos, titles, the closing page. Each shows the real thing, lights the word he is saying as he says it, and stays still and readable at phone size for as long as it must be read. You also keep the look itself: one design across captions, graphics and cards.

Graphics are front-end work: build them yourself, never through a GPT model (`roles/director.md`, "Models").

## Two routes

Josh's direction: as much as possible natively in Resolve, "except terminal graphics which are okay in remotion unless there is a better more native sane option".

- **Titles, highlights, photos, cards and the closing page** are the look's Fusion title templates, one per kind the look draws, with published inputs (words, photos, sizes, regions), built once per look and kept in the look's folder. Each is a `titles` row, `{template, inputs, record, frames}`, which `place.py` puts on V4 as a title item with its inputs set on the item; nothing is nested. A word change is an input on that item, about 0.01 s in place, or a change in the list and a re-place. To look at one graphic alone, place its row on a check timeline and take a frame. You choose every value by looking at the frame; there is no layout engine. Text+ wraps by itself. Where a template cannot do something by its inputs (a pill behind part of a line), change the template once for the look, never the code.
  - **The opening title** is "Signpost Opening": a dark band at the top of the frame, so it reads as a card and not as a caption arriving ahead of his voice.
  - **The closing page's address** has its own size input (`AddressSize`): the full address fits one line, clear of the button column.
- **The terminal, an agent's input box and the key-line card** stay in Remotion (`tools/remotion.md`), because Resolve gives no way to hand a graphic its rows and its highlight frames. Each is a rendered clip on V3, a `panels` row. You write its rows from the demo content and the frame of each event from the editor's spotting (`roles/editor.md`, "Spotting graphics"), which takes every frame from the word's onset on the level trace, never from a transcript's word time.

## What each graphic is made of

Four things, kept apart so each changes alone:

- **Content:** the demo's real output, real pixels, his photos, and words from `words.md`, a `Final:` line Josh settled or the director's `Proposed:` line (SKILL.md, "Constraints").
- **Timing:** when it comes in, what lights on which word, when it leaves: the editor's spotting, on the placed timeline's word times.
- **Layout:** where it sits, whether he stays visible, clear of the caption band.
- **Look:** type, colour, sizes, highlight and motion: `looks/<name>/look.json` and its templates.

A value of one video (a frame number, a row of this tool's output, a size for this card) never goes into a template or a component, and a value of the look is never set on one graphic.

## The highlight is the signature

One highlight for whatever he is saying or naming: the spoken word in the captions, the text he names in a terminal, the words he types into an agent's box. In his look it is a pill, chosen so the eye follows his voice across the screen. That works only if it is exact: it covers the word's whole ink with even padding, arrives on the frame the word starts (more than 3 frames out is a fault, `tools/faults.md`), and stays until the next highlight. His note when it was not: "your subtitles and pills and highlights on terminal stuff do NOT properly cover words and look WRONG". A box computed from font metrics can disagree with what renders: the rendered frame is the evidence.

Over real app pixels a filled pill would hide what it marks, so the look lights a region with an orange outline: the "Signpost Highlight" template (inputs: the region's edges in frame pixels and a padding; values under `highlight` in `look.json`, reasons in the README). Josh has not yet seen it, so the script page's look line shows it on a real frame the first time.

## Motion and reading time

**How a graphic moves belongs to the look; when it moves belongs to the cut.** Entrance and exit durations in frames, easing, overshoot, and what holds still while text is read live in `look.json` and the templates (the Fusion templates and the Remotion components, which read the same look), set once per look and never chosen per graphic by a builder. The moments (when a graphic comes in, which word lights, when a panel scrolls, when it leaves) are the editor's spotting, per video. Josh asked for exactly this split: design and "the (timing of how we pan/highlight/etc each elemnt)" kept orthogonal. Two builders who choose their own motion make two looks. Josh asked for "a HOLISTIC style that matches BOTH the subtitles AND the various title/subtitle/on screen graphics and is COHERENT", and for the look "we should keep as much in possible in code". A kind the look has never drawn gets its motion values added to `look.json` once, with the reason in the README, like any other value (below).

**Text never moves or blurs while it is read.** The entrance finishes, the text holds still until the exit begins, and a highlight arriving or moving changes nothing under it. No graphic changes twice a few frames apart.

**Reading time for cards and titles.** A stranger reads about three words a second (the reading-speed norms professional subtitlers work to: Netflix 20 characters a second, the BBC 160 to 180 words a minute) and needs a moment to find the card first. So a card or title is too fast when it is fully readable for less than about a third of a second per word plus half a second, counted from the first frame its text is fully readable, not from the start of its entrance, to the first frame of its exit. This is a limit of the viewer, not a number from one recording; Josh's own two calls agree with it (a seven-word card "too fast" at 1.5 s, not raised at 2.5 s, where the entrance took part of the 2.5 s). One reading job at a time: a card over a terminal the viewer is also reading counts both. Captions follow his speech, so their pace is his, not this limit.

## The look

**Reuse is normal.** His picked look serves every video, extended to anything new this one shows: a kind it has never drawn is designed inside the look, its values added to `look.json` and its reasons to the README, with one still on a real frame of this video for the script page. Check what changes with each recording:

- the caption band against his face in every layout;
- labels over these photos;
- the terminal's column count;
- captions over light pictures;
- the caption row length: how many of his characters fit one row inside the safe line with the pill (about 19 in his look), against the phrases he says. A phrase wider than two rows becomes a page break no paging can avoid (on one project, five phrases). That is a look decision for Josh (smaller type, or accept the breaks): show it to the director before the cut.

**Options only when no picked look fits:** two or three complete looks, each with real values the builders read, shown as stills made by the real builders on the same real moments (the first frame, the hardest graphic moment, the closing card), one column per look, his moodboard reference above each. Never as a prose description (`examples/2-look-options-weak.md` against `examples/2-look-options-strong.png`).

**A note changes a value inside the look.** "Too small" means the same element bigger, never a new style; when the size is unclear, show two or three on one frame. When the look limits a moment of this video, show the director the moment as it is and with the value you propose: "if stuff is limiting us we should flag that".

## Cards

**The intro card is the thumbnail:** one idea, its key words on the highlight, alone on screen before his voice and the captions take over, for its reading time, and alone for a moment before the captions start (Josh, on one opening: "should have the card for 1.5s or smth before the subs come in?").

**The closing card is one page** with an ask a viewer can do from a video, no second slide. Anything they must type lives in the post, and the card says where. Judge the whole frame, empty space included. His note on a card that was not: "your action card is still hunched up ... look at the empty space".

**A terminal or log card** prints its rows directly under the command, as a terminal does.

## How to tell

Look over the real, graded picture on the finish timeline (`frame.py`, or a one-frame render), as SKILL.md's "The loop" says: the gate first, then eyes only where it cannot measure.

1. **The gate on the span.** Render the graphic's span and run `qc.py SPAN.mp4 --range FIRST LAST --only highlights text flashes captions` (`tools/faults.md`, "Running the gate"). It measures highlight timing after a pause, text under the platforms' top controls, text too small at phone width, the caption safe line, and flashes. Open every fault and look row's evidence. The text check samples one frame a second, so a label near the top band is still checked by eye over the graphic's whole range; nothing else on this list is repeated by eye.
2. **Each pill and outline against its word,** at full size on the frame it arrives: the whole ink covered, the padding even.
3. **Labels in the button column.** No label in a still or capture sits right of x 950 below y 900 (the look's `safeArea`), checked at full size over the graphic's whole range.
4. **Content under a held highlight.** Run the frame-difference trace (`tools/checking.md`) over the whole range of every held highlight and every held card, cropped to the panel or card (`crop=W:H:X:Y` before `signalstats`, so his live footage behind it does not count): the content and the text inside must not move, apart from the highlight's own arrival. A menu crop once scrolled 51 px in one frame and carried the outline from "77%" onto the usage bar.
5. **The reading time** of each card and title, from the first fully readable frame to the first frame of its exit.
6. **The rest of what only eyes find** in `tools/faults.md`, "Graphics": a card cropped mid-card, a sliver of the next card, the screen through a title band, mis-sized content.

Write `scratch/motion/state.md` as you go (SKILL.md, "The roles"). Hand over the graphics placed in the list, a check frame of every graphic you changed, and one line on what changed and any slot still showing a proposal.

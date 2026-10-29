<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5 as a brief to the role: its outcome, the two routes and why, the four layers, the highlight, motion and reading time, how a look is written and copied, cards, and what proves a graphic right. The dated evidence behind it is in history.md. -->

# Motion designer

## Your outcome

Every graphic in the video, in the look Josh picked, above the cameras: the tool on screen, his photos, titles, the closing page. Each shows the real thing, lights what he is saying or naming as he says it, and holds still and readable at phone size for as long as it must be read. You also keep the look itself: one design across captions, graphics and cards, so the video looks as if one designer made it. Josh asked for "a HOLISTIC style that matches BOTH the subtitles AND the various title/subtitle/on screen graphics and is COHERENT".

You work after the editor has spotted the graphics and in parallel with the colourist. The editor owns when each graphic comes and goes and which word it lights; the story role owns what it shows; you own how it looks and moves. Graphics are front-end work: build them yourself, never through a GPT model (`roles/director.md`, "Models").

## What you start from

- **The spotting:** the list's `titles` rows and the entries in `graphics/spec.json`, with their record frames, lengths, layouts and cue frames (`roles/editor.md`, "Graphics").
- **The content:** `graphics/content/` and `content.md`, and the words in `words.md` (a `Final:` line Josh settled, or the director's `Proposed:` line).
- **The look:** `looks/<name>/look.json`, its README (the reason for each value), its Fusion templates in `pipeline/b/templates/<look>/`, and its Resolve caption template.
- **His moodboard:** the Apple Notes note "road trip style guide" and the downloads of its references in `Edits/looks/moodboard/`.
- **The finish timeline,** graded, for judging every graphic over the real picture.

## Two routes, and why

Josh's direction: as much as possible natively in Resolve, "except terminal graphics which are okay in remotion unless there is a better more native sane option".

- **Titles, highlights on app pixels, photos, cards and the closing page** are the look's Fusion title templates, one per kind the look draws, each with published inputs (its words, photos, sizes, regions, and fade timings where it has them). Each is a `titles` row `{template, inputs, record, frames}`, which `place.py` puts on V4 as a title item with its inputs set on the item; nothing is nested. A word change is an input on that item, about 0.01 s in place, or a change in the list and a re-place. Text+ lays out and wraps its own words, so there is no layout engine: you choose every input by looking at the frame. To look at one graphic alone, `graphic.py LIST INDEX --over TIMELINE --out PNG` renders it over a scratch duplicate. Where a template cannot do something by its inputs, change the template once for the look (its graph in `pipeline/b/template_kinds.py`, built by `make_templates.py` from `look.json`), never per graphic.
- **The terminal, an agent's box and the key-line card** are Remotion clips, because they need per-frame data that no Resolve graphic takes (`tools/remotion.md`, "Why these three are not Resolve"). You complete each entry in `graphics/spec.json` (its rows from the content, its look) on the editor's frames, render it, and place the clip as a `panels` row on V3.

## What each graphic is made of

Four things, kept apart so each changes alone:

- **Content:** the tool's real output, real pixels, his photos, and words from `words.md`.
- **Timing:** when it comes in, what lights on which word, when it leaves. The editor's, on the placed sound.
- **Layout:** where it sits, whether he stays visible, clear of the caption band and the platforms' buttons.
- **Look:** type, colour, sizes, highlight and motion, in `look.json` and the templates.

Josh asked for exactly this: on-screen graphic design and "the (timing of how we pan/highlight/etc each elemnt) orthogonal". A value of one video (a frame number, a row of this tool's output, a size for this card) never goes into a template or a component; a value of the look is never set on one graphic.

## The highlight is the signature

One highlight for whatever he is saying or naming: the spoken word in the captions, the text he names in a terminal, the words he types into an agent's box. In his look it is a pill, so the eye follows his voice across the screen. That works only if it is exact: it covers the word's whole ink with even padding, arrives on the frame the word starts (more than 3 frames out is a fault, `tools/faults.md`), and stays until the next. His note when it was not: "your subtitles and pills and highlights on terminal stuff do NOT properly cover words and look WRONG". A box computed from font metrics can disagree with what renders, so the rendered frame is the evidence.

Over real app pixels a filled pill would hide what it marks, so the look lights a region with an outline in the pill's orange (the look's highlight template; its values and reasons in `look.json` and the README). The first time Josh sees a highlight treatment he has not chosen, the script page's look line shows it on a real frame.

## Motion and reading time

**How a graphic moves belongs to the look; when it moves belongs to the cut.** Entrance and exit lengths in frames, easing, overshoot, typing and scrolling speeds, and what holds still while text is read live in `look.json` and the templates, set once per look. Two builders who choose their own motion make two looks. A kind the look has never drawn gets its motion values added to `look.json` once, with the reason in the README.

Professional motion has numbers, not adjectives. When a value is missing, choose it from these and write it into the look:

- small feedback, such as a highlight arriving: a few frames; a move: a fifth to half a second; a main reveal: up to about a second; an exit shorter than its entrance;
- ease out on the way in, ease in on the way out, ease in and out across the screen; linear only for a constant scroll or a progress bar;
- no overshoot on text; position and size may settle, opacity and colour never bounce;
- one thing moves at a time, and everything settles before the text that depends on it appears.

**Text never moves or blurs while it is read.** The entrance finishes, the text holds still until the exit begins, and a highlight arriving changes nothing under it. No graphic changes twice a few frames apart. Every graphic is complete on its first frame: one that fades up from nothing reads over a camera as a flash.

**Reading time** for cards and titles is a fault, not taste, because their words are on screen by the crew's choice: fully readable for at least about a third of a second per word plus half a second, counted from the first readable frame, one reading job at a time (`tools/faults.md`, "Card or title too fast to read"). Josh, on screens that were not: "honestly this is all too fast to see". Captions follow his speech, so their pace is his.

## The look

**Reuse is normal.** His picked look serves every video: "for now re-use but 1) it will evolve 2) we should keep as much in possible in code". Extend it to anything new this video shows: a kind it has never drawn is designed inside the look, its values added to `look.json`, its reasons to the README, with one still on a real frame of this video for the script page. Check what changes with each recording:

- the caption band against his face in every layout (`subtitles.faceClearance`);
- captions and labels over this video's pictures, light ones especially;
- the terminal's column count against the panel;
- how many of his characters fit one caption row inside the safe line, against the phrases he says (`captions.py` warns on rows that do not fit). A phrase wider than two rows breaks mid-phrase at any paging: a look decision for Josh (smaller type, or accept the breaks), shown to the director before the cut.

**A note changes a value inside the look.** "Too small" means the same element bigger, never a new style; when the size is unclear, show two or three on one frame. When the look limits a moment of this video, show the director the moment as it is and with the value you propose: "if stuff is limiting us we should flag that".

**Options only when no picked look fits:** two or three complete looks, each with real values the builders read, shown as stills made by the real builders on the same real moments (the first frame, the hardest graphic, the closing card), one column per look, his moodboard reference above each. Never as prose: "i want to fucking see them? with pictures?" (`examples/2-look-options-weak.md` against `examples/2-look-options-strong.png`).

### Writing a look

A look is a system a builder can apply to a recording it was not designed on. Write it so:

- **Sizes relative to the frame** (a share of its width or height), so they carry across shapes; the pixel value for 1080 by 1920 beside it.
- **Gaps as a share of letter height,** not as a line-height number: fonts carry different built-in spacing, so one line-height gives different gaps in another face.
- **Motion in frames at the timeline's rate,** with easing named.
- **Each colour with its job** (the highlight, the panel, dim text), as the display value and, for Fusion, the linear value the template needs (`tools/resolve.md`, "Colour management").
- **What it depends on,** so a builder knows what to keep when a recording differs: a dark enough band behind white captions, room above his head for a panel, a background that is not white.
- **What it never does.** Name the generic choices to refuse (gradients and glows, everything fading in at once, a logo fading to black, text that moves while read, made-up screens) and add any generic look that creeps into a render.

### Copying a look from references

His idea for taste is a moodboard: references he likes, the AI doing the mechanical part. To turn references into a look:

1. Work from the downloads, two or three videos of the same look where there are, because one video mixes the system with one-offs. Keep each download's info file.
2. Find every kind of text, overlay and layout on a pass at about a frame a second, then step frame by frame around every cut, new text and zoom: a frame a second hides the motion.
3. Crop each kind of text at full size. Match the font on what makes it distinctive (weight and width first, then the telling letters), comparing candidates on one sheet against the crop. Sample each colour inside thick strokes over several frames, never at edges.
4. For each kind of text and graphic, write its font, size relative to the frame, case and punctuation, how many words at once, colour and any shadow or box, line gaps, where it sits relative to his face and the frame, what makes it appear, and how it moves in and out in frames and easing.
5. What happens in every reference is the look; what happens once is a one-off. Take why he liked it, not its incidentals, and none of their words.
6. Try it on his footage straight away: stills of the same kinds of moment beside the reference frames, at full size, and fix the look's values where the copy differs.

## Cards

- **The opening card is the thumbnail:** one idea, its key words on the highlight, alone on screen for its reading time before his voice and the captions take over (Josh, on one opening: "should have the card for 1.5s or smth before the subs come in?"). It reads as a card, not as a caption arriving early: high in the frame, larger, on its band.
- **The closing card** carries an ask a viewer can do from a video. Anything they must type lives in the post, and the card says where, because nobody can copy text out of a video. It holds long enough to read everything on it at phone size, and the video never ends on a frozen frame of his face (`roles/editor.md`, "Clean frames"). Judge the whole frame, empty space included: "your action card is still hunched up ... look at the empty space". How it is built and how it arrives is a look decision for each video, shown to him as an option. One example of a decision he made once: on where-was-i he chose a single page with the ask and the mission together ("also the mission on same page as action. no second slide. KISS"), arriving as his last word ended, over his footage darkening behind it. That was his choice for that video, not a rule for the next.
- **A terminal or key-line card** prints its rows directly under the command, as a terminal does.

## What proves a graphic right

Look over the real, graded picture on the finish timeline, as SKILL.md, "The loop" sets out: the gate first, then eyes only where it cannot measure.

1. **The gate on the graphic's span,** `--only highlights text flashes captions` (`tools/faults.md`, "Running the gate"): highlight timing after a pause, text under the platforms' top bar, text too small at phone width, the caption safe line, flashes. Open every row's evidence. It reads text once a second, so a label near the top bar is checked by eye over the graphic's whole time on screen.
2. **Each pill and outline against its word** at full size on the frame it arrives: the whole ink covered, the padding even, touching nothing else.
3. **Labels clear of the button column** (the look's `fusion.safeArea`), at full size over the graphic's whole time on screen.
4. **Nothing moves under a held highlight or a held card:** a frame-difference trace cropped to the panel or card, over its whole time on screen (`tools/checking.md`, "A frame-difference trace").
5. **Reading time** of each card and title, from the first fully readable frame to the first frame of its exit.
6. **What only eyes find** (`tools/faults.md`, "Graphics"): a card cropped mid-card, a sliver of the next card, the screen through a title band, mis-sized content. Every graphic's first and last frame at full size and at 390 px wide.

Write `scratch/motion/state.md` as you go. Hand over the graphics in the list and the rendered clips, a check frame of every graphic you changed, one line on what changed, and every slot still showing a proposal.

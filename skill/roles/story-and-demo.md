<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5 as a brief to the role: its outcome, finding a video in a ramble, the page Josh decides from, the proof on screen, and the hand-over. The dated evidence behind it is in history.md. -->

# Story and demo

## Your outcome

One page that shows Josh the video his recording contains, line by line in the order a viewer hears it, in his words only, with the real content the viewer sees at each line and a measured length, so he can decide what is in at one sitting. And the content itself: the tool's real output, captured so it reads on a phone, ready for the editor and the motion designer.

The story and the proof are found together, because the page must name real output: before anyone writes a line, someone has used the tool, read its README, run it on real data and found what would surprise a stranger. This role comes first after ingest because everything downstream inherits its choices. A page he cannot read costs a round; a story that does not hold costs every round after it.

The writing line is his: "do NOT let the AI do any of your writing (it is bad at it)", and the AI "can give me ideas but it shouldn't write copy". You find, arrange and propose; you never write words that go out under his name, and you never weaken his (SKILL.md, "What is his, and what is yours").

## What you start from

- **The verbatim transcript,** read start to finish (`tools/transcription.md`). Resolve's transcript is for the first minutes after ingest and hides his stumbles.
- **`record.md`,** read whole: what he has said about this video, this tool, its audience and its ask.
- **The tool itself:** its repository, the release a viewer would install, its README and help, and the binary, run on real data.
- **The screen recording** with its index (`screen-recording.md`), and `inventory.md`.
- **His picked look** (`looks/<name>/`), so you know what the pipeline can draw.

The rawest material is the tool running and his voice on the lav. A summary of either, his or an agent's, is a lead to check, never the source.

## Finding the video in a ramble

Expect false starts, asides to the editor ("you can cut here"), the same point made two or three times, and stretches where he narrates the tool as he uses it. None of the asides belong; any of the narration might.

- **Read the whole take.** The best statement of an idea is rarely the first. A search finds one take; only reading finds the better one ten minutes later. Speakers often say a line again, the opening especially, near the end of a session: look there too.
- **Decide three things first:** the promise a stranger should get in the first seconds, in his words; who the video is for; how it ends, meaning what the viewer does next.
- **Keep the proof.** The lines where he narrates the tool working are what make a stranger believe him. Cutting them to save time makes the video weaker: "now your cuts take my lines that actually narrate the terminal out? this is worse?"
- **Look before you cut an odd line.** His words often lean on the screen. A line that reads as rambling on paper ("flew to LAX where I stayed the night, Bell") can be the proof on screen, where he highlights "Bell" as he says it.
- **Arrange by the viewer's questions:** what is this, why should I care, does it really work, how do I get it. Nothing may refer to something the viewer has not yet heard or seen.
- **Join in his voice.** Prefer one long clean run to a line built from fragments, usually his last complete take. At every join, read the words either side together, as a viewer hears them.
- **Repair a broken join from the raw take first.** When two lines placed side by side do not follow, he has often said the link himself a few seconds further on in the same passage. Only after that search, propose a reorder, words on screen or a re-record.
- **Measure the length from placed lines,** never by adding times by hand: write the lines as audio pieces in a draft edit list, place it, and read the length back. A hand total mixes start and end times, and Josh notices at once.

When he read from a script, the story is his. For each line choose the take: a run that carries two or three lines cleanly over the best attempt at each stitched together, his eyes on the lens for front-camera lines, his spoken words over the script's.

A gap (a point he never made clearly, an ask he never said) is found now, while the cameras may still be set up. It reaches him through the director as the point and his own nearest words, never as a line for him to read.

## The page

His standard: "do you get how the script needs to read to a fucking human? this is the key part". The page is something he could print and judge as the video: rows in viewing order, each with its start time, his words in full exactly as said, and what is on screen in plain words naming the real output. No IDs, beat names, source times or commentary. One markdown page in `versions/script-vN.md`, readable on a phone:

```markdown
# <video>: script, version N

72 s, measured from the placed lines. <What changed since the last page, or "First version.">
Cut now: <the version the editor cuts, in one line>

Decisions for you:
1. <a question only he can answer, answerable in a word, with your recommendation>

**0:00 · "<his opening words, in full>"**
<what is on screen: the real output or picture, in plain words>

**0:13 · "<his next line>"**
`<the real command>`: <what it shows, with the real numbers>

---
**Worth re-recording while the cameras are up:** <the point, and his nearest words; or "nothing">
**Options:** <each addition in full, what it adds, its seconds; off unless he says yes>
**Left out:** <each of his lines not used, in a few words>
**What the screens show of you:** <what of his life and of other people shows, and what you propose to hide>
**Words on screen:** <each slot: his own nearest lines first, then yours marked as yours, with your recommendation>
**Captions that tidy your grammar:** <each edit, or "none">
**The look:** <"as last time", or a still of anything new>
```

Weak: prose with bracketed screen notes, options described in words, and source times, so he has to hold the recording in his head to judge it (`examples/1-script-page-weak.md`; his words: "unreadable slop? i dont have rain man memory of all the lines?"). Strong: timed rows in playing order with his exact words and the real output under each, so reading it once is a viewing of the video (`examples/1-script-page-strong.md`).

- **An option that changes the story is a complete second page,** never a list of moves.
- **Promise only what the pipeline can draw today.**
- **Before he sees it,** read it aloud as a stranger would hear it. Then have a fresh model, given only the page, say what the video is about and where it lost the thread. Fix the writing of the page, never his claims.

## His words and his notes on the page

You arrange his words; you never write them and never weaken them. A claim he made on camera stays in the title, the card and the captions as he made it, whatever today's numbers say: "i set the content you do the mechanical stuff". A cold reader who says one of his numbers looks wrong has given you a note for the "what the screens show" line, not a change to his words.

Captions may tidy his grammar, his own example being "it's a command line tool" shown as "this is a command line tool", but never change his meaning, add a claim or drop one. Each tidy-up goes on the page for him to agree.

A note is about the page he was reading, sized to what he named (`roles/director.md`, "Reading Josh"). "Is there any other good material?" asks for additions, each in full with its cost, and everything else unchanged. A repair always goes back inside the whole script, never to him as snippets: "this is fucking annoying giving me all these snippets in random order?"

Text written for a machine, such as a prompt a viewer pastes into their own agent, is outside the writing line: write it well and specifically, for the weakest agent a viewer might use, and give it to Josh to approve. His edits stand exactly.

## The proof: what the viewer sees of the tool

Treat the tool's real output as footage: re-shot cleanly at the size the frame needs, the most telling run, one thing at a time, the thing he names lit as he names it. Copying the screen recording fails because a full-width laptop screen in a 1080-pixel frame cannot be read on a phone; redrawing fails because it no longer looks like the tool. His words for both: "if you copy directly from my screen recording or fake stuff too hard then gg you will have neither." A demo that went badly on the day can be done again from the real tool.

| The line is about | Show |
| --- | --- |
| What a command-line tool prints | The real tool re-run at the panel's column count (`tools/remotion.md`, "Real output, at the panel's width") |
| An app's window, a menu, a web page | Real pixels, captured fresh with the window sized to the frame's shape, cropped to what he names |
| Something he did as it happened | The screen recording, conformed to the timeline's rate and cropped (`tools/cameras.md`, "The screen recording") |
| Asking an agent to use the tool | The agent's real screen, his request as he says it, the answer from a real fresh run |
| What the tool found in his own data | The key lines of real output, with the real thing it came from beside it (a photo, a file) |

Breadth and depth together: Josh asked to "showcase the full breadth/depth of the tool" and to "focus jsust on the most interesting stuff". Show its range in brief glimpses under the lines that name its abilities, and go deep on the one worked example he narrates.

Make the run match the video:

- **The version a viewer installs.** Check the copy on the Mac against the release: a development checkout can be ahead of it.
- **Output that depends on today** runs as of the recording day. When the tool cannot reproduce that state, tell the director, show the most authentic real output you can, and leave his claim as he made it.
- **A narrower real command** when it shows his point on one screen.
- **A few real lines held still and large** when he talks about one line of a long output.
- **A tool with no help** is read in its source before you run a subcommand, because `--help` on a subcommand can run it.

**Tidying is allowed; inventing never is.** You may narrow the command, choose the run, hide rows (whole rows, never edited), crop, re-wrap at word boundaries with every word unchanged, cut dead time visibly, and use the app's own privacy mode. Never change a number, name, date, count or result, never make the tool look faster than it is, never draw an interface that did not run, and never write an agent's answer. His word for hiding is "fake", and his sentence sets its limit: "you can fake the output a little by hiding family trips". Hide by narrowing the command first, so private rows are never captured. Other people appear only if he says so.

**Real pixels in a vertical frame:**

- White captions dissolve over a light app window, so say which content is light where the caption band falls; the editor then puts it in a panel above him.
- What he names sits above the caption band and left of the platforms' button column (the look's `fusion.safeArea`).
- Check both margins of a small window for private desktop detail over the whole time it is used.

A bug you find in the tool goes to the director as a separate task; the video shows the tool as it is.

## Hand over

To the director, the page. To the editor and the motion designer, `graphics/content/`: each piece of content, and `content.md` saying for each how it was made (command, version, date run as, column count), which line it proves, the exact text or regions available to light, what it shows of his life, and every row hidden and why. Write `scratch/story-and-demo/state.md` as you go (SKILL.md, "The roles, and why in this order").

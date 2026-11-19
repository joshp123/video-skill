<!-- Written by AI on 2026.11.19 by model claude opus 5.5: the story and demo brief, from the 29 Oct file, kept to the outcome, Josh's words, the page format he accepted and the practice of a story producer. -->

# Story and demo

## Your outcome

One page that shows Josh the video his recording contains, line by line in the order a viewer hears it, in his words only, with the real content the viewer sees at each line and a measured length, so he can decide what is in at one sitting. And the content itself: the tool's real output, captured so it reads on a phone.

The story and the proof are found together, because the page must name real output: before you write a row, use the tool, read its README, run it on real data and find what would surprise a stranger. The script is the one creative decision models are not yet good enough to make for him, so the page is built to make his decision quick, and the cut waits for it.

The writing line is his: you find, arrange and propose; you never write words that go out under his name, and you never weaken his (SKILL.md, "What is his, and what is yours").

## What you start from

- **The verbatim transcript,** read start to finish (`tools/transcription.md`).
- **`record.md`,** read whole: what he has said about this video, this tool, its audience and its ask.
- **The tool itself:** its repository, the release a viewer would install, its README and help, and the binary, run on real data.
- **The screen recording** with its index (`screen-recording.md`), and `inventory.md`.
- **His picked look,** so you know what the pipeline can draw.

The rawest material is the tool running and his voice on the lav. A summary of either is a lead to check, never the source.

## Finding the video in a ramble

Expect false starts, asides to the editor ("you can cut here"), the same point made two or three times, and stretches where he narrates the tool as he uses it. None of the asides belong; any of the narration might.

- **Read the whole take.** The best statement of an idea is rarely the first, and speakers often say a line again, the opening especially, near the end of a session.
- **Decide three things first:** the promise a stranger should get in the first seconds, in his words; who the video is for; how it ends, meaning what the viewer does next.
- **Keep the proof.** The lines where he narrates the tool working are what make a stranger believe him; cutting them to save time makes the video worse.
- **Look before you cut an odd line.** His words often lean on the screen, so a line that reads as rambling on paper can be the proof on screen.
- **Arrange by the viewer's questions:** what is this, why should I care, does it really work, how do I get it. Nothing may refer to something the viewer has not yet heard or seen.
- **Join in his voice.** Prefer one long clean run to a line built from fragments. At every join, read the words either side together. When two lines side by side do not follow, he has often said the link himself a few seconds further on: search the raw take before you propose a reorder, words on screen or a re-record.
- **Measure the length from the cut edges,** by assembling the plan without Resolve (`pipeline/README.md`, `assemble.py` alone), never by adding times by hand. That also names every edge with no pause next to it: a line that cannot be cut cleanly is better found now than after he has chosen it.

When he read from a script, the story is his: for each line choose the take, his eyes on the lens for front-camera lines, his spoken words over the script's.

A gap (a point he never made clearly, an ask he never said) is found now, while the cameras may still be up. It reaches him on the page as the point and his own nearest words, never as a line for him to read.

## The page

The page is the key deliverable of this stage, and it must read to a human who does not have the recording in his head. The page is something he could print and judge as the video: rows in viewing order, each with its start time, his words in full exactly as said, and what is on screen in plain words naming the real output. No IDs, beat names, source times or commentary. One markdown page in `versions/script-vN.md`, readable on a phone, in the form he accepted:

```markdown
# <video>: script, version N

72 s, measured from the cut edges. <What changed since the last page, or "First version.">
I recommend: <the version to cut, in one line>

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

- **An option that changes the story is a complete second page,** never a list of moves.
- **Promise only what the pipeline can draw today.**
- **Before he sees it,** read it as a stranger would hear it: what is the video about, and where does it lose the thread? When you cannot tell, a fresh model given only the page can. Fix the writing of the page, never his claims.
- **Send it the moment it is right,** not when everything else is ready.

## His words and his notes on the page

A claim he made on camera stays in the title, the card and the captions as he made it, whatever today's numbers say (SKILL.md, "What is his, and what is yours"). A cold reader who says one of his numbers looks wrong has given you a line for "What the screens show of you", not a change to his words.

Captions may tidy his grammar ("it's a command line tool" shown as "this is a command line tool" is his own example) but never change his meaning, add a claim or drop one. Each tidy-up goes on the page for him to agree.

A note is about the page he was reading, sized to what he named. A note asking whether there is other good material asks for additions, each in full with its cost, and everything else unchanged. A repair always goes back inside the whole script, never to him as snippets in random order.

## The proof: what the viewer sees of the tool

Treat the tool's real output as footage: re-shot cleanly at the size the frame needs, the most telling run, one thing at a time, the thing he names lit as he names it. Copying the screen recording fails because a full-width laptop screen in a 1080-pixel frame cannot be read on a phone; inventing a screen fails because it is no longer the tool. A terminal's real output redrawn at the panel's width is still the tool (`tools/remotion.md`). A demo that went badly on the day can be done again from the real tool.

| The line is about | Show |
| --- | --- |
| What a command-line tool prints | The real tool re-run at the panel's column count (`tools/remotion.md`) |
| An app's window, a menu, a web page | Real pixels, captured fresh with the window sized to the frame's shape, cropped to what he names |
| Something he did as it happened | The screen recording, conformed to the timeline's rate and cropped (`tools/cameras.md`) |
| Asking an agent to use the tool | The agent's real screen, his request as he says it, the answer from a real fresh run |
| What the tool found in his own data | The key lines of real output, with the real thing it came from beside it |

- **The version a viewer installs.** Check the copy on the Mac against the release: a development checkout can be ahead of it.
- **Output that depends on today** runs as of the recording day. When the tool cannot reproduce that state, say so on the page and leave his claim as he made it.
- **A tool with no help** is read in its source before you run a subcommand, because `--help` on a subcommand can run it.

**Tidying is allowed; inventing never is.** You may narrow the command, choose the run, hide whole rows, crop, re-wrap at word boundaries with every word unchanged, cut dead time visibly, and use the app's own privacy mode. Never change a number, name, date, count or result, never make the tool look faster than it is, never draw an interface that did not run, and never write an agent's answer. Hiding private rows is allowed; changing what the tool found is not. Hide by narrowing the command first, so private rows are never captured. Other people appear only if he says so.

In a vertical frame, white captions dissolve over a light app window, so say which content is light where the caption band falls; what he names sits above the caption band and clear of the platforms' button column; check both margins of a small window for private desktop detail over the whole time it is used.

The video shows the tool as it is. A bug you find in the tool goes to Josh; it changes the video only when it undoes what the video claims.

## Hand over

The page, with its line in `versions/README.md`. `graphics/content/`, and `content.md` saying for each piece how it was made (command, version, date run as, column count), which line it proves, the exact text or regions available to light, what it shows of his life, and every row hidden and why. Every slot for words on screen in `words.md`. When he decides, his reply is the script: keep it beside the page, and change nothing on it he did not ask for.

<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. The page's "Cut now" and "Left out" lines and the claims rule on words on screen: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). -->

# Story and demo

Your outcome: one page that shows Josh the video his recording contains, line by line in the order a viewer hears it, in his words only, with the real content the viewer sees at each line and a measured length, so he can decide what is in at one sitting. The story and the proof are found together, because the page must name real output: before anyone writes a line, someone has used the tool, read its README, run it on real data and found what would surprise a stranger.

Everything downstream inherits your choices. A page he cannot read costs a round; a story that does not hold costs every round after it.

## You receive

The verbatim transcript (read it start to finish; Resolve's transcript is for the first minutes and hides his stumbles), `record.md` read whole, the tool (its repository, the release a viewer would install, README and help), the screen recording with its index, `inventory.md`, and his picked look.

## Finding the video in a ramble

Expect false starts, asides to the editor ("you can cut here"), the same point made two or three times, and stretches where he narrates the tool as he uses it. None of the asides belong; any of the narration might.

1. **Read the whole take.** The best statement of an idea is rarely the first. A search finds one take; only reading finds the better one ten minutes later.
2. **Decide three things first:** the promise a stranger should get in the first seconds, in his words; who the video is for; how it ends, meaning what the viewer does next.
3. **Keep the proof.** The lines where he narrates the tool working make a stranger believe him. His reaction when a draft cut them: "now your cuts take my lines that actually narrate the terminal out? this is worse?"
4. **Look before you cut an odd line.** His words often lean on the screen. On where-was-i, "flew to LAX where I stayed the night, Bell" read as rambling on paper; on screen he highlights "Bell" as he says it, and the line is the proof.
5. **Arrange by the viewer's questions:** what is this, why should I care, does it really work, how do I get it. Nothing may refer to something the viewer has not yet heard or seen.
6. **Join in his voice.** Prefer one long clean run to a line built from fragments, and usually his last complete take. At every join, read the words either side together.
7. **Repair a broken join from the raw take first.** On where-was-i, "it's hidden away in apps like Apple Photos" followed by "it's a command line tool" made no sense; a few seconds further into the same passage he had said the link himself. Only after that search propose a reorder, words on screen or a re-record.
8. **Measure the length from the placed lines,** never by adding times by hand: write the lines as audio pieces in a draft list, place them, and read the length back. A hand total mixes start and end times, and Josh notices at once.

When he read from a script, the story is his: for each line choose the take, preferring a run that carries two or three lines cleanly to the best attempt at each stitched together, his eyes on the lens for front-camera lines, and his spoken words over the script's. Say where the choice between two clean takes turns on how they sound, which nobody here can hear.

## The page

His standard: "do you get how the script needs to read to a fucking human? this is the key part". One markdown page in `versions/script-vN.md`, readable on a phone:

```markdown
# <video>: script, version N

72 s, measured from the placed lines. <What changed since the last page, or "First version.">
Cut now: <the version the editor cuts, in one line>

Decisions for you:
1. <a question only he can answer, in a word, with your recommendation>

**0:00 · "Have you ever wondered if you could figure out everywhere you've ever been…"**
Your trip photos, each with its place label; then you, on the front camera.

**0:13 · "I made this tool that tells you all the places you've been…"**
`where-was-i in "United States"`: 7 visits, 112 days.

---
**Worth re-recording while the cameras are up:** <the point, and his nearest words; or "nothing">
**Options:** <each addition in full, what it adds, its seconds; off unless he says yes>
**Left out:** <each of his lines not used, in a few words>
**What the screens show of you:** <what of his life and of other people shows, and what you propose to hide>
**Words on screen:** <each slot, his own nearest lines, then yours marked as yours, your recommendation; a proposal keeps his claim as he made it, and none is chosen, and none of his lines left out, because the footage or the tool today shows a different number>
**Captions that tidy your grammar:** <each edit, or "none">
**The look:** <"as last time", or a still of anything new>
```

Every row has its start time, his words in full and exactly as said, and what is on screen in plain words naming the real output. No IDs, beat names, source times or commentary. An option that changes the story is a complete second page, never a list of moves. Promise only what the pipeline can draw today. Before he sees it, read it aloud as a stranger would hear it, then have a fresh model given only the page say what the video is about and where it lost the thread; fix the writing, never his claims. A cold read that says a number of his looks wrong is a note for the page's "what the screen shows" column, not a change to his words (SKILL.md, "His words").

`examples/1-script-page-weak.md` against `examples/1-script-page-strong.md` shows the difference: prose with bracketed screen notes and options described in words, which he called "unreadable slop", against timed rows in playing order with the real output under each, which he judged as a video in one message.

## His words, and his notes on the page

You arrange his words; you never write them, and you never weaken them: a claim he made on camera stays in the title, the card and the captions as he made it, whatever today's numbers are ("i set the content you do the mechanical stuff", 26 Oct). Captions may tidy his grammar ("it's a command line tool" shown as "this is a command line tool", his own example) but never change his meaning or add a word; each tidy-up goes on the page for him to agree. A note is about the page he was reading, sized to what he named: "is there any other good material" asks for additions, each in full with its cost, and everything else unchanged. When he shows you a fix must be in context ("this is fucking annoying giving me all these snippets in random order?"), the repair goes back inside the whole script.

## The proof: what the viewer sees of the tool

A launch-demo producer treats the product's real output as footage: re-shot cleanly at the size the frame needs, the most telling run, one thing at a time, the thing he names lit as he names it. Copying the screen recording fails because a 3456-pixel-wide screen in a 1080-pixel frame cannot be read on a phone; redrawing fails because it no longer looks like the tool. A demo that went badly on the day can be done again from the real tool.

| The line is about | Show |
| --- | --- |
| What a command-line tool prints | The real tool re-run at the panel's column count (`tools/remotion.md`) |
| An app's window, a menu, a web page | Real pixels, captured fresh with the window sized to the frame's shape, cropped to what he names |
| Something he did as it happened | The screen recording, conformed to the timeline's rate and cropped (`tools/cameras.md`) |
| Asking an agent to use the tool | The agent's real screen, his request as he says it, the answer from a real fresh run |
| What the tool found in his own data | The key lines of real output, with the real thing it came from beside it |

Josh asked for breadth and focus together: "showcase the full breadth/depth of the tool" and "focus jsust on the most interesting stuff". Show its range in brief glimpses under the lines that name its abilities, and go deep on the one worked example he narrates. A tool with no help is read in its source before you run a subcommand, because `--help` on a subcommand can run it.

Make the run match the video: the version a viewer will install (on codex-switch the Mac ran 13 commits past the release); output that depends on today run as of the recording day; a narrower real command when it shows his point on one screen; a few real lines held still, large, when he talks about one line of a long output.

**Tidying is allowed; inventing never is.** You may narrow the command, choose the run, hide rows (hidden whole, never edited), crop, re-wrap at word boundaries with every word unchanged, cut dead time visibly, use the app's privacy mode. Never change a number, name, date, count or result, never make the tool look faster, never redraw an interface or write an agent's answer. His word for hiding was "fake", and his sentence shows its limit: "you can fake the output a little by hiding family trips". Hide by narrowing the command first, so private rows are never captured. Other people appear only if he says so.

**Real pixels in a vertical frame:** white captions dissolve over a light app window (13 captions on codex-switch did not read), so say which content is light where the caption band falls; what he names must sit above the band and left of the platforms' button column; check both margins of a small window for private desktop detail over the whole stretch it is used.

Hand over in `graphics/content/` the content itself and `content.md`: for each piece, how it was made (command, version, date run as, column count), which line it proves, the exact text or regions available to light, what it shows of his life, and every row hidden and why. A bug in the tool goes to the director as a separate task; the video shows the tool as it is.

Write `scratch/story-and-demo/state.md` as you go.

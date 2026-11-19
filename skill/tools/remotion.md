<!-- Rewritten by AI on 2026.11.19 by model claude opus 5.5 from the 29 Oct and 18 Nov files: why the terminal kinds are Remotion, real output at the panel's width, the render spec, and checking a clip. The 17 Nov rebuild did not exercise this route; where pipeline/README.md differs, it wins. -->

# Remotion: the terminal, the agent's box and the key-line card

## Why these three are not Resolve

Graphics are native in Resolve, with terminal graphics the one exception (SKILL.md, "Tools"). A terminal graphic needs per-frame data: rows of real output, a command typed character by character, a scroll by whole rows, a highlight on exact character cells from the frame he names them. No Resolve graphic takes that: an OGraf graphic takes a file, a trim, a hold and play frames (pp. 2376 to 2378), and a script cannot put a Text+ character style on named characters (22 Oct). So these three render in Remotion, each as its own transparent clip on the app track. When Resolve gains a route for per-frame text data, this exception should go.

The project is `pipeline/graphics/` (Remotion 4, React 19, in its own devenv). The 17 Nov rebuild did not exercise it: on its first use, check one clip over the graded picture before building a video's worth. Its components are `Terminal.tsx`, `AskTerminal.tsx` (the agent's box) and `Keyline.tsx`, with `glyphBounds.ts` measuring each highlighted word's rendered ink so a pill fits it. It renders with Remotion's own downloaded headless shell, never the installed Chrome app, whose every launch left a 1.4 GB copy of itself in a temporary folder.

## Real output, at the panel's width

The terminal is redrawn, but it must look real and fit the vertical frame. Real means the tool's own output, run at the column count the panel gives, in one monospace face on a character grid.

```sh
python3 pipeline/graphics/capture-terminal.py --columns N --output EDIT/graphics/content/NAME.txt -- COMMAND ARGS
```

It runs the command in a pseudo-terminal N columns wide and saves every byte, only if the command exits cleanly. A tool that formats for the terminal's width then wraps exactly as it would there. A tool that leaves wrapping to the terminal breaks words wherever the line runs out: capture through `-- sh -c 'COMMAND | fold -s -w N'`, after checking the piped run prints the same words. Set `PAGER=cat`, or a pager waits for ever. A full-screen interface that moves the cursor cannot be captured as rows. Pass the tool's full path.

**The column count sets the type size:** the panel's text width divided by the columns, times 0.6 for JetBrains Mono's advance. Fewer columns, bigger type, more wrapping. Never capture wide and zoom: the tool's own layout is then cut at the panel's edge.

**From capture to rows.** `compileTerminalContent(capture, columns)` in `pipeline/graphics/terminal-content.mjs` strips colour and title escape codes, turns carriage returns, backspaces and tabs into what a terminal shows, and wraps at the column count, counting wide characters as two cells. `findTerminalTarget(rows, text, after)` finds a phrase in those rows and returns its character ranges, so a highlight can only land on text the tool really printed.

## The render spec

One `graphics/spec.json` per video lists each clip: its kind, the look, the timeline frame it starts on and its length, its layout (the graphic's region, and where his picture sits when he shares the frame), its content (rows within the column count) and its cues on timeline frames (type, show, highlight a range of character cells, scroll; for the agent's box, each word typed on the frame he says it). A cue on his word is that word's start on the placed sound, so render the clips again after any edit that moves his words. Before it renders, the renderer checks every frame, row, range and action and prints the text each highlight lights, so you read words, not cells. Each clip renders as ProRes 4444 with alpha, into its own folder (it refuses a file that exists). Three terminal clips took about half a minute (22 Oct). Display-referred Rec.709 clips pass through the timeline unchanged only with the inverse DRT on (`tools/resolve.md`, "Colour management").

## Making each kind read

- **Terminal:** the prompt, the command typed in, then the rows exactly as printed. The view scrolls by whole rows, so no half row or cut-off word sits at an edge. What he names lights on the frame he names it.
- **Agent box:** his request appears word by word as he says it, the spoken word on the pill. A caption under it would show his words twice: there is none while it is up.
- **Key-line card:** the command small at the top, a few real lines large, re-wrapped at word boundaries with every word unchanged.

## Checking a clip

Composite it over mid-grey, which shows shadows and edges that black hides, then look at the same moments on the graded timeline. A pill is right when its padding is even on all four sides and it touches nothing but its own text. When a pill looks wrong, check the font first: a face with no declared file falls back silently, and every pill is then measured on the wrong glyphs.

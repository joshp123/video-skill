<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: why the terminal kinds are Remotion, what the render spec holds, how real output becomes rows, and how to render and check a clip. Every field is checked against pipeline/b/render-graphics.mjs and pipeline/graphics/. -->

# Remotion: the terminal, the agent's box and the key-line card

## Why these three are not Resolve

Josh's direction: graphics native in Resolve, "except terminal graphics which are okay in remotion unless there is a better more native sane option". A terminal graphic needs per-frame data: rows of real output, a command typed character by character, a scroll by whole rows, a highlight on exact character cells from the frame he names them. Resolve gives a graphic no way to take that: an OGraf graphic takes a file, a trim, a hold and play frames (pp. 2376 to 2378), and a script cannot put a Text+ character style on named characters (22 Oct). So these three render in Remotion, each as its own transparent clip, placed as a `panels` row on V3 above the cameras. Everything else (titles, photos, cards, the closing page) is the look's Fusion templates (`roles/motion.md`). When Resolve gains a route for per-frame text data, this exception should go (SKILL.md, "Keep moving into Resolve").

The project is `Edits/pipeline/graphics/` (Remotion 4, React 19, in its own devenv, which provides Node and ffmpeg). Its components are in `src/`: `Terminal.tsx`, `AskTerminal.tsx` (the agent's box), `Keyline.tsx`, with `glyphBounds.ts` measuring each highlighted word's rendered ink so a pill fits it.

## Real output, at the panel's width

Josh: "WE CAN FAKE REAL TERMINALS WE SHOULD OBVIOUSLY JUST MAKE IT LOOK REAL BUT FIT THE VERTICAL FORMAT". Real means the tool's own output, run at the column count the panel gives, set in one monospace face on a character grid.

```sh
python3 pipeline/graphics/capture-terminal.py --columns N --output EDIT/graphics/content/NAME.txt -- COMMAND ARGS
```

It runs the command in a pseudo-terminal N columns wide (`COLUMNS=N`, `LINES=40`, `TERM=xterm-256color`) and saves every byte, only if the command exits cleanly. A tool that formats for the terminal's width then wraps exactly as it would there. A tool that leaves wrapping to the terminal breaks words wherever the line runs out: capture through `-- sh -c 'COMMAND | fold -s -w N'`, after checking the piped run prints the same words. Set `PAGER=cat` or a pager waits for ever. A progress bar becomes many rows, and a full-screen interface that moves the cursor cannot be captured as rows at all. Always pass the tool's full path.

**The column count sets the type size.** The columns fill the panel's text width, so the size is the width divided by the columns, times 0.6 for JetBrains Mono's advance. Fewer columns, bigger type, more wrapping. Never capture wide and zoom: the tool's own layout is then cut at the panel's edge.

**From capture to rows.** `compileTerminalContent(capture, columns)` in `pipeline/graphics/terminal-content.mjs` strips colour and title escape codes, turns carriage returns, backspaces and tabs into what a terminal shows, and wraps at the column count, counting wide characters as two cells; every character is otherwise unchanged. `findTerminalTarget(rows, text, after)` finds a phrase in those rows and returns its character ranges, with `after` to pick the occurrence after another phrase. Use both from `node -e` in the graphics devenv, so a highlight can only land on text the tool really printed. `claude-screen.mjs` (`fitClaudeWelcomeRows`) refits a captured Claude Code start screen to the panel's columns, keeping its text and redrawing only the border.

## The render spec: `graphics/spec.json`

One file per video, beside `graphics/content/`. The editor writes each graphic's timing into it (`roles/editor.md`, "Graphics"); the motion designer completes and renders it. Frames are timeline frames: a graphic is on screen from `record` for `frames`, and every cue frame lies inside that span.

```json
{
  "format": {"width": 1080, "height": 1920, "fps": 25},
  "graphics": [
    {"id": "trip", "kind": "terminal", "look": "2026-10-16-signpost-pill", "record": 412, "frames": 160,
     "layout": {"graphic": [0, 0, 1080, 980], "picture": [0, 980, 1080, 940]},
     "content": {"columns": 36, "prompt": "$ ", "command": "TOOL trip 2025-06-23", "rows": ["...", "..."]},
     "cues": [{"frame": 412, "action": "type"},
              {"frame": 470, "action": "highlight", "range": [{"row": 4, "column": 7, "length": 4}]}],
     "source": "graphics/content/trip-36.txt, cue at 470 on his word 'Bell'"}
  ]
}
```

- **Every graphic:** `id` (the clip's file name), `kind`, `look` (a folder in `Edits/looks/`), `record`, `frames`, and `layout`: `graphic` is its region `[x, y, width, height]` in frame pixels (default the whole frame), and `picture`, when he shares the frame, is where his picture sits; a terminal's background stops at its top. Fields the components do not read, such as `source`, pass through untouched: use them for where each value came from.
- **`terminal`:** `content` `{columns, prompt, command?, rows}`, every row no wider than `columns`. Cues `{frame, endFrame?, action, range?}`: `type` types the command at the look's speed, then prints the rows; `show` scrolls a range's first row to the top; `highlight` lights the range until the next highlight, scrolling it into view; `scroll` brings the range's last row to the bottom, ending at `endFrame`. A range is a list of `{row, column, length}` in character cells.
- **`agent box`:** `content` `{columns, prompt, words, welcomeRows}`: the agent's real start screen as `welcomeRows`, and his request as `words`. Cues `{frame, endFrame, action: "type-word", index}` type `words[index]` on the frame he says it, on the pill, at the largest size that fits.
- **`keyline`:** a few real lines held large. `content` `{command?, prompt?, typeCommand?, header?, commandColumns, keyColumns, cards, highlights}`. Each card `{fromFrame, rows}` replaces the one before at its frame; each highlight `{frame, ranges}` lights ranges `{card, row, column, length}` until the next.

Before it renders anything the renderer checks every frame against the span, every row against the column count, every range against its row, and every action against its kind, and prints the text each highlight lights, so the writer sees words, not cells. Any failure stops the render.

## Rendering

From `Edits/pipeline/graphics`, where VIDEO is the video's folder under `Edits/`:

```sh
devenv shell -- node ../b/render-graphics.mjs ../../VIDEO/graphics/spec.json --out=../../VIDEO/build/graphics-vN
```

Each graphic becomes `<id>.mov`, ProRes 4444 with alpha, 10-bit, Rec.709, with a `manifest.json` of `{id, file, record, frames}`; the clip goes on V3 as a `panels` row at that record frame. It refuses any file that exists, so each version renders into its own folder. Three terminal clips took about half a minute (22 Oct). It runs Remotion's own downloaded headless shell through `chrome-render.sh`, never the installed Chrome app, whose every launch left a 1.4 GB copy of itself in a temporary folder. Display-referred Rec.709 clips pass through the timeline unchanged only with the inverse DRT on (`tools/resolve.md`, "Colour management").

`pipeline/graphics/render-clips.mjs` is the older renderer, which builds its data from the older edit format (`pipeline/edit-format.md`, below its line); new work uses `render-graphics.mjs`.

## Making each kind read

- **Terminal:** the prompt, the command typed in, then the rows exactly as printed. The view scrolls by whole rows, so no half row or cut-off word sits at an edge. What he names lights on the frame he names it.
- **Agent box:** his request appears word by word as he says it, the spoken word on the pill. A caption under it would show his words twice: there is none while it is up.
- **Key-line card:** the command small at the top, a few real lines large, re-wrapped at word boundaries with every word unchanged.
- **Complete on its first frame.** A graphic that opens empty or fades up from nothing reads, over a camera, as a one-frame flash.

## Checking a clip

Composite it over mid-grey, which shows shadows and edges that black hides:

```sh
ffmpeg -hide_banner -loglevel error -y -i CLIP.mov -f lavfi -i 'color=c=0x808080:s=1080x1920:r=25,format=rgb24' \
  -filter_complex '[0:v]select=eq(n\,CLIP_FRAME),setpts=PTS-STARTPTS,format=rgba[fg];[1:v][fg]overlay=format=rgb:shortest=1,format=rgb24[out]' \
  -map '[out]' -frames:v 1 EDIT/build/check/ID-FRAME.png
```

Then look at the same moments on the placed finish timeline. A pill is right when its padding is even on all four sides and it touches nothing but its own text. When a pill looks wrong, check the font first: a face with no declared file falls back silently, and every pill is then measured on the wrong glyphs.

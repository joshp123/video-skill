<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). -->

# Remotion: the terminal, the agent box and the key-line card

These three kinds stay in Remotion by Josh's exception, because Resolve gives no way to hand a graphic its rows and its highlight frames: an OGraf graphic takes only a file, trim, hold and play frames (pp. 2376 to 2378), and a script cannot put a Text+ character style on named characters (22 Oct). Each renders as its own transparent clip, a `panels` row that `place.py` lays on V3 above the cameras. The project is `Media/Edits/pipeline/graphics/` (Remotion 4.0.535, React 19), in its own devenv, which provides Node and ffmpeg.

**What still leans on the old format.** The components draw from render data: each graphic's kind, its content rows, the look, and the film frame of every event (type, show, highlight, scroll). `render-clips.mjs` builds that data today from the old edit data and cut list (`prepare.mjs`). In B the motion designer writes the rows and frames; until the renderer takes them directly, tell the director, and do not write a cut list to feed it.

## Content that looks real

Josh: "WE CAN FAKE REAL TERMINALS WE SHOULD OBVIOUSLY JUST MAKE IT LOOK REAL BUT FIT THE VERTICAL FORMAT". Real means the tool's own output, run at the width the panel gives, set in one monospace face on a character grid.

```sh
python3 pipeline/graphics/capture-terminal.py --columns N --output EDIT/graphics/content/NAME.txt -- COMMAND ARGS
```

It runs the command in a pseudo-terminal N columns wide (`COLUMNS=N`, `LINES=40`) and saves every byte, only if the command exits cleanly. A tool that formats for the terminal's width then wraps exactly as it would there. A tool that leaves wrapping to the terminal breaks words anywhere ("Montser|rat" on where-was-i): capture through `-- sh -c 'COMMAND | fold -s -w N'`, after checking the piped run prints the same words. A pager waits for ever (`PAGER=cat`); a progress bar becomes many rows; a full-screen interface captures as garbage, because cursor movement is stripped. Always pass the tool's path.

**The column count sets the type size:** the columns fill the text width, so size is the width divided by the columns times 0.6 for JetBrains Mono. In a 908-px panel, 36 columns give about 42 px type, 26 about 58 px. Never capture wider and zoom: at 44 columns and 1.4 times, "Los Angeles" showed as "Los An".

## The kinds

- **Terminal:** the prompt, the command typed in at the look's speed, then the rows exactly as printed. The view scrolls by whole rows, so no half row or cut-off word sits at an edge. What he names lights on the frame he names it, found by its exact text in the capture (with the text before it when it occurs twice); a target the capture does not hold stops the render, so a highlight can only land on text the tool really printed.
- **Agent box:** the agent's real start screen refitted to the columns (`claude-screen.mjs` for Claude Code), then his request appearing word by word as he says it, the spoken word on the pill, at the largest size that fits.
- **Key-line card:** the command small at the top, then a few real lines large, re-wrapped at word boundaries with every word unchanged, highlights on named text.

Make every graphic complete on its first frame: one that opens empty or fades up from nothing reads over the camera as a one-frame flash.

## Rendering

```sh
cd "/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline/graphics"
devenv shell -- node render-clips.mjs ../../EDIT --out=build/graphics-vN [--only=ID] [--stills --frame=FILM_FRAME]
```

ProRes 4444 with alpha, Rec.709, one clip per graphic, a `manifest.json` of first frames and lengths. It refuses to overwrite, so each version renders into its own folder. Three terminal clips took 33 s (22 Oct). It uses Remotion's own headless shell through `chrome-render.sh`: never the installed Chrome app, whose every launch left a 1.4 GB copy in a temporary folder until the internal disk filled (Josh: "why the fuck do we need a copy of chrome to redner shit?"). Display-referred Rec.709 clips pass through the timeline unchanged only with the inverse DRT on (`tools/resolve.md`).

## Checking a clip

Composite it over mid-grey, which shows shadows and backgrounds that black hides:

```sh
ffmpeg -hide_banner -loglevel error -y -i CLIP.mov -f lavfi -i 'color=c=0x808080:s=1080x1920:r=25,format=rgb24' \
  -filter_complex '[0:v]select=eq(n\,CLIP_FRAME),setpts=PTS-STARTPTS,format=rgba[fg];[1:v][fg]overlay=format=rgb:shortest=1,format=rgb24[out]' \
  -map '[out]' -frames:v 1 EDIT/build/check/ID-FRAME.png
```

Then the same moments on the placed timeline. A pill is right when its padding is even on all four sides and it touches nothing but its own text. Pills are sized from each word's rendered ink after the fonts load (`glyphBounds.ts`); when a pill looks wrong, check the font first: a face with no declared file falls back silently and every pill is measured on the wrong glyphs.

<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). -->

# Looking at the cut

How to make each view. Every role looks at its own work this way before handing it over. On a render, `qc.py` runs first (`tools/faults.md`); these views open what it found and judge what it cannot measure. Instruments find where to look; only frames, looked at, pass anything.

## Frames from the viewer, with no render

`frame.py` wraps this route:

```python
project.SetCurrentTimeline(timeline); resolve.OpenPage("color")
timeline.SetCurrentTimecode(timecode)        # the timeline's start timecode plus the frame
project.ExportCurrentFrameAsStill(path)      # API 1858
```

On 22 Oct stills 0.7 to 8.5 s after the seek matched the rendered frame within 1.1 levels on a shot carrying CineFocus and Magic Mask, and a Fusion photo grid over a camera within 0.26 levels; 128 stills over six rounds all showed the right clip by the second export. One known failure: on 14 Oct a still 1.5 s after a seek showed the previous clip. So read the playhead back and export twice a second apart; identical files mean the viewer had settled. Whether the viewer shows the caption track as Deliver renders it is untested: for captions, render one frame with the `still` preset (0.7 to 2.2 s).

## Frames from the delivered file

By frame number, from 0, at full size:

```sh
ffmpeg -v error -i versions/cut-v5.mp4 -vf "select=eq(n\,725)" -fps_mode passthrough -frames:v 1 build/check/f725.png
```

- **Full size,** each frame opened on its own: a pill against its word, a letter at a panel edge, a mask at hair and glasses, two cameras across a cut.
- **Phone width:** `-vf scale=390:-1`, and read every word in the time it is up.
- **Consecutive frames through anything that moves:** `-vf "select=between(n\,723\,727)" -fps_mode passthrough run_%d.png`. One still can catch a transition halfway.
- **Side by side:** `ffmpeg -i a.png -i b.png -filter_complex hstack=inputs=2 pair.png`, opened at 1300 to 1800 px wide or cropped at full size; a 2160-px pair shrunk by the viewer looked banded where full-size crops were smooth (22 Oct).
- **A frame-difference trace** over the second around each change: `-vf "select=between(n\,700\,750),signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-" -f null -`. A camera cut read 47 against neighbours of 0.5 to 3 (22 Oct). Open every spike.

**A contact sheet is for finding where to look in a long file, never for judging.** Josh: it is "not how a real professional would do it, its too compressed and you miss the full story". Pills that missed their words passed a contact-sheet check on the first video, and he found them.

## What changed since the last version

Compare with the version he last saw, same preset both sides (a phone render decodes about two levels darker than a master):

```sh
ffmpeg -i versions/cut-v5.mp4 -i versions/cut-v4.mp4 -lavfi "[0:v][1:v]psnr=stats_file=build/check/psnr.log" -f null -
ffmpeg -v error -i versions/cut-v5.mp4 -map 0:a:0 -f f32le - | shasum -a 256
```

Align the two first if frames were added or removed. Everything outside the intended change should be identical within encoding noise; anything else is a fault until explained. This comparison found a frozen end frame on the wrong expression and a panel framed 61 to 140 px off within minutes (17 Oct).

## Sound

Loudness and true peak on the file he gets: `ffmpeg -hide_banner -nostats -i FILE -af ebur128=peak=true -f null - 2>&1 | tail -12` (`I:` and `Peak:`). A spectrogram either side of a join: `-filter_complex "[0:a]showspectrumpic=s=1600x600"`; what it shows and misses is in `tools/audio.md`, "Seeing a join".

## Reading time and flashes

Measure how long each caption and card is fully readable from the frames, not the data; about three words a second finds the ones to look at again at phone width. On where-was-i Josh found a seven-word card too fast at 1.5 s and did not raise it at 2.5 s. `pipeline/graphics/scan-flashes.mjs EXPORT.mp4`, in the graphics devenv, lists single-frame flashes and brightness spikes to open.

## What nobody here can check

No model here watches motion or hears sound, and a run of stills is not watching. Say so, and name at most three moments, with times, for Josh's eyes or ears.

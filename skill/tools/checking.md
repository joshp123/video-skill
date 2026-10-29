<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: how to make each view of a cut, what each shows and what it hides. Who looks at what is in each role's file; the measured classes are in tools/faults.md. -->

# Looking at a cut

The gate measures first (`tools/faults.md`). These views open what it found and judge what it cannot measure. Instruments find where to look; only frames, looked at, pass anything.

**A contact sheet is for finding where to look in a long file, never for judging.** It shrinks each frame to a thumbnail, so it hides exactly what a cut is judged on: an eyelid, a fingertip at a cheek, a pill a few pixels off its word, a one-frame sliver of the next card. Josh: "its too compressed and you miss the full story".

## Frames from the camera files

A segment shows a frame of its camera's own file, so what the camera saw at a cut (eyes, hands, mouth, a head turn, both cameras at one moment) is in the file, with no Resolve and no lock. Seek by time, frame n at n divided by the frame rate, and take every frame a decision needs in one command:

```sh
for n in 14210 14211 14212 31004; do
  ffmpeg -v error -ss "$(echo "$n/25" | bc -l)" -i FRONT.MOV -frames:v 1 build/check/front-$n.png
done
```

`-ss` before `-i` with decoding is frame-accurate on a constant-rate camera file: ffmpeg seeks to the keyframe before and decodes forward. Check it once per file against `-vf "select=eq(n\,N)"` on one known frame, since a file with an unusual start time can be a frame out. The screen recording has a variable frame rate: conform it before taking frames from it (`tools/cameras.md`, "The screen recording").

## Frames from the timeline, with no render

`pipeline/b/frame.py NAME FRAME OUT.png` shows what the timeline shows: framing, layout, the grade on a finish timeline, a graphic over him. It selects the timeline, opens the Color page, sets the playhead, exports the viewer twice a second apart, and keeps the frame only when both are identical, so the viewer had settled (`ExportCurrentFrameAsStill`, API 1858). Stills from the viewer matched the rendered frame within about one level of 255 on a shot with CineFocus and Magic Mask, and on a Fusion graphic over a camera (22 Oct). When a caption is on the frame, it renders that one frame instead, with the captions burnt in, because the viewer route is not proven to show the caption track as Deliver renders it. It gives one frame per call and holds the Resolve lock while it works.

## Frames from the delivered file

By frame number from 0, at full size:

```sh
ffmpeg -v error -i versions/cut-v5.mp4 -vf "select=eq(n\,725)" -fps_mode passthrough -frames:v 1 build/check/f725.png
```

- **Full size,** each frame opened on its own: a pill against its word, a letter at a panel's edge, a mask at his hair and glasses, the two cameras across a cut.
- **Phone width:** `-vf scale=390:-1`, and read every word in the time it is up. 390 px is the width of a phone held upright.
- **Consecutive frames through anything that moves:** `-vf "select=between(n\,723\,727)" -fps_mode passthrough run_%d.png`. One still can catch a transition halfway.
- **Side by side:** `ffmpeg -i a.png -i b.png -filter_complex hstack=inputs=2 pair.png`, opened at 1300 to 1800 px wide or cropped at full size. A 2160 px pair shrunk by the viewer looks banded where full-size crops are smooth.

## A frame-difference trace

Over the second around a change, or over the whole time a card or a held highlight is up:

```sh
ffmpeg -v error -i CUT.mp4 -vf "select=between(n\,700\,750),crop=W:H:X:Y,signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-" -f null -
```

`YDIF` is the mean change in brightness from the frame before. A cut stands out far above its neighbours; a spike where nothing should change is a sliver, a flash or content jumping. Crop to the panel or card first, so his live footage behind it does not count: under a held highlight the content must not move, apart from the highlight's own arrival. Open every spike as consecutive frames.

`pipeline/graphics/scan-flashes.mjs FILE`, in the graphics devenv, lists isolated one-frame changes and brightness spikes across a whole file, to open.

## What changed since the last version

Compare with the version Josh last saw, same preset both sides (a phone render decodes about two levels darker than a master):

```sh
ffmpeg -i versions/cut-v5.mp4 -i versions/cut-v4.mp4 -lavfi "[0:v][1:v]psnr=stats_file=build/check/psnr.log" -f null -
ffmpeg -v error -i versions/cut-v5.mp4 -map 0:a:0 -f f32le - | shasum -a 256
```

Align the two first if frames were added or removed. Everything outside the intended change should be identical within encoding noise; anything else is a fault until explained. This finds in minutes what single looks miss, such as a frozen end frame on a different expression or a panel framed differently, and it is how a second look stays small: after a fix, look only where the difference says something changed.

## Sound

Loudness and true peak on the file he gets: `ffmpeg -hide_banner -nostats -i FILE -af ebur128=peak=true -f null - 2>&1 | tail -12` (`I:` and `Peak:`). A spectrogram either side of a join, and what it shows and misses: `tools/audio.md`, "Seeing a join".

## Reading time and flashes

Time each card and title from frames, never from the list: the first frame its text is fully readable, then the first frame of its exit. It is a fault under the limit in `tools/faults.md`, "Card or title too fast to read". For captions, about three words a second finds the ones to read again at phone width; their pace is his.

## What nobody here can check

No model here watches motion or hears sound, and a run of stills is not watching. Consecutive frames and the difference trace show most motion faults; how something feels in motion, and how a join sounds, go to Josh as at most three named moments with their times.

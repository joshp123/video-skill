<!-- Rewritten by AI on 2026.11.19 by model claude opus 5.5 from the 18 Nov file: Josh's rig, the facts a file can and cannot tell you, sync and how to prove it, face touches and the screen recording. Facts about one recording go in that session's inventory.md, never here. -->

# Cameras, ingest and sync

Ingest is the assistant editor's job: everything later stages stand on, proven rather than assumed. Every file copied and checked; the video's Resolve project made with both cameras; the lav on the front camera's clock; each camera's picture offset established; the verbatim transcript started at once, so the story can be read while the cameras may still be set up; both cameras scanned for face touches; `inventory.md`, `screen-recording.md` and `record.md` written. The pipeline's ingest does the measurable part in one call and lists what is left for you (`pipeline/README.md`). One session can hold several videos: ingest once per session, and check an earlier ingest's claims against the files before reusing them.

## The rig

The specifications are in `~/code/gear/camera-gear/` (start at `inventory.md`); it lags his purchases, so check his mail when it looks incomplete. Which lens, profile and settings a session used are facts about that session: establish them from the files.

| Role | Device | How it records |
| --- | --- | --- |
| Front, the main camera | Nikon Z f | Up to 3840 by 2160, 10-bit H.265 `.MOV`, in N-Log, auto white balance; a large sensor with fast lenses, so his background falls out of focus |
| Wide | DJI Osmo Pocket 4 | Up to 3840 by 2160, 10-bit H.265 `.MP4`, in D-Log, auto white balance; a fixed 20 mm-equivalent f/2 lens on a 1-inch sensor, so everything stays sharp |
| Dialogue | DJI Mic Mini on Josh | Into the Pocket's file, as stereo AAC with identical channels. The transmitter records nothing itself, so a dropped radio link loses that dialogue, and the Pocket's sound is the lav's radio feed, delayed against its own picture |
| Screen | macOS screen recording | Silent, variable frame rate, at the display's native size |

## What a file tells you

`ffprobe` gives codec, size, rate, frame count and audio. It cannot show a log profile: both cameras tag their files BT.709 whatever they recorded, so a profile read from a tag is wrong. ExifTool on the Nikon reads its picture control, lens, aperture and focus distance; it is not on the `PATH` (`"$(ls -d /nix/store/*-Image-ExifTool-*/bin/exiftool | sort -t- -k5 -V | tail -1)"`). The Pocket's per-frame data sits in a DJI track ExifTool cannot read: confirm D-Log by eye (a flat, low-contrast picture). Write each fact into `inventory.md` with how it was established.

**Never sync on the clocks.** The two cameras' timecodes and file creation times disagree with each other and with the sound: on one session the timecodes were about seven hours apart, and creation times put the wide camera 15 s after the front when the sound put it 36.7 s after.

**Cards.** The Nikon mounts as `/Volumes/NIKON Z F  ` (two trailing spaces), clips under `DCIM/`; the Pocket's as `Osmo SD 1TB`, clips under `DCIM/DJI_001/` with `.LRF` proxies. Quote every path. Never erase a card. Copying from a card through ingest has not been tested.

## Sync, and how to prove it

Ingest measures the lav against the front camera's own microphone at five points across the take, so drift shows, and pads the lav onto the front camera's clock with the median offset. On 12 Oct the five ran from 36.7370 to 36.7468 s, about 12 ms over the take, under a frame: no speed correction. Decide on one only when the drift passes half a frame.

The wide camera's picture offset is measured picture against picture (his head's motion seen by both cameras), not from its sound, because its sound is the delayed radio feed: on 12 Oct its windows fell in two clusters 80 ms apart, so treat it as evidence and settle it by eye. Prove what it cannot measure as an assistant editor would:

- the clap's transient in both waveforms within a frame;
- late in the take, his lips closing on a "p", "b" or "m" on each camera as the lav's sound starts, which shows drift;
- each camera's picture against the sound on its own: the Pocket's picture can run about a frame ahead of its own sound.

Write each camera's picture offset in `inventory.md` with how it was found. Apply every offset once: front-camera time = a file's own time + its offset; the lav padded onto the front clock has offset 0, and adding the offset as well moves every word twice.

## Face touches

For the cut's rule on touches see `roles/editor.md`, "Clean frames". This skill's `scripts/face_touch.swift`, on Apple's Vision, flags each frame where a hand has three or more confident points inside his face's box enlarged by 15%; ingest runs it on both cameras' whole files. It has caught every touch a frame-by-frame check found, flagged gestures near the neck as well, and missed a scratch behind the ear that the other camera's scan caught. So read the two scans together, and look at each flagged moment on full-size frames.

## The screen recording

macOS writes a frame only when the screen changes, so the file's nominal rate (120 fps) says little; its frame times are a first index of what changed. Look at each change at full size for private detail (emails, account names, file names).

**Sync it on events both clocks record.** A spoken cue finds the offset to a second or two. His face lit by the screen (the front camera's face brightness against the screen's), or his key clicks on the lav against characters appearing, fixes it to the frame. Confirm at a second event far from the first; if they disagree, the recording paused between them. Write the offset and the index in the session's `screen-recording.md`.

**As footage,** conform the stretch to the timeline's rate before editing, trimming inside the filter, because seeking with `-ss` before `-i` on a variable-rate file can drop the frame that was on screen at the start:

```sh
ffmpeg -i SCREEN.mov -vf "fps=25,trim=start=S:end=E,setpts=PTS-STARTPTS" -c:v prores_ks -profile:v 3 OUT.mov
```

Frame n of the result is the screen at S + n/25, within one frame.

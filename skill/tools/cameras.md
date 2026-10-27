<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). "Within one frame": Claude Opus 5.5 (hill-climb stream L), 2026-10-27. -->

# Cameras, ingest and sync

Facts about one recording (its lens, offsets, framing, room tone) go in that session's folder, never here.

## The rig

Specifications are in `~/code/gear/camera-gear/` (start at `inventory.md`); it lags purchases, so check his mail when it looks incomplete.

| Role | Device | What it recorded on 12 Oct |
| --- | --- | --- |
| Front, the main camera | Nikon Z f | 3840 by 2160, 25 fps, 10-bit H.265 `.MOV`, N-Log, auto white balance |
| Wide | DJI Osmo Pocket 4 | 3840 by 2160, 25 fps, 10-bit H.265 `.MP4`, D-Log, auto white balance; fixed 20 mm-equivalent f/2 lens on a 1-inch sensor, so its background stays sharp |
| Dialogue | DJI Mic Mini on Josh | Recorded into the Pocket's file as stereo AAC with identical channels; the transmitter records nothing itself, so a dropped link loses that dialogue |
| Screen | macOS screen recording | Silent, variable frame rate, at the display's native 3456 by 2234 |

## Read the facts from each file

`ffprobe -v error -show_streams -show_format -of json CLIP` gives codec, size, rate, frames and audio. It cannot show a log profile: both cameras' files carry BT.709 tags whatever they recorded. ExifTool on the Nikon reads its picture control, lens, aperture and focus distance (not on the `PATH`: `"$(ls -d /nix/store/*-Image-ExifTool-*/bin/exiftool | sort -t- -k5 -V | tail -1)"`). The Pocket's per-frame data sits in a DJI track ExifTool cannot read; confirm D-Log by eye (a flat picture) and from the camera's setting. Write each fact and how it was established into `inventory.md`.

**The clocks disagree, so never sync on them.** On 12 Oct the Nikon's timecode read 12:16:32 and the Pocket's 05:16:35, and creation times put the Pocket 15 s after the Nikon when the sound put it 36.7 s after.

## Ingest

- **Cards:** the Nikon mounts as `/Volumes/NIKON Z F  ` (two trailing spaces), clips under `DCIM/`; the Pocket's as `Osmo SD 1TB`, clips under `DCIM/DJI_001/` with `.LRF` proxies; the Pocket's internal storage can mount too. Quote every path. Never erase a card.
- **Copy with Resolve's clone:** `pipeline/ingest/clone.py PROJECT SOURCE DESTINATION` (SHA-256, folder names kept). Where the copies land has varied (22 Oct): look, then run `shasum -a 256 -c sha256sums.txt` beside the copies and against the card.
- **Take the lav first:** make the project (`pipeline/resolve/create_project.py`, which also makes the multicam of the two cameras, synced by their sound, and writes each angle's offset to `inventory.md`), transcribe the lav at once (`tools/transcription.md`), and extract the two files the custom steps read:
  ```sh
  ffmpeg -i POCKET.MP4 -map 0:a:0 -ar 48000 -c:a pcm_s24le EDIT/audio/lav_48k.wav
  ffmpeg -i POCKET.MP4 -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le EDIT/audio/lav_16k.wav
  ```

## Sync

`pipeline/ingest/sync.py PROJECT FRONT_FILE WIDE_FILE` (front first: its clock is the master) runs `AutoAlignClips` by waveform on a scratch timeline and prints `first time = second time + OFFSET`: 36.760 s on 12 Oct against 36.737 s by cross-correlation (22 Oct). The multicam's own sync put the wide 0.57 frame from the cross-correlated offset (26 Oct); compare its angle offset with this one. Both report one offset and no drift, so check as a person would: the clap's transient in both waveforms within a frame, then late in the take his lips closing on a "p", "b" or "m" on each camera as the lav's sound starts. On 12 Oct drift was 13 ms over 22 minutes. The Pocket's picture ran about a frame ahead of its own lav (the wireless link), so check the wide picture on its own and give it its own offset when it is a frame or more off.

**Apply each offset once.** Front-camera time = a file's own time + its offset. Either pad the lav onto the front clock and use 0, or keep it raw and pass the offset; doing both moves every word twice. A session may already hold a padded front-clock lav (12 Oct: `audio/dji_0597_aligned_to_nikon_48k_stereo.wav`): look before making one. Write it once per session, name it in `inventory.md`, and point `edit/edit.json`'s `media.lav` and the list's `sound.lav` at it.

## Face touches

His standard: "cut all the moments where i touch my face etc (as a pro director would do)". `scripts/face_touch.swift` (Apple's Vision) flags each frame where a hand has three or more confident points inside his face's box enlarged by 15%; its header has the commands. Extract frames at five a second from the whole file onto the SSD under `Media/Edits/.cache/`, run detached, about five minutes a camera for a 23-minute take. On 12 Oct it caught all 7 touches a frame-by-frame check found, plus 5 gestures at the neck (22 Oct). It missed a scratch behind the ear on the front camera that the wide flagged, so read both scans together: a touch on either is a touch on both. Scan both cameras whole: on where-was-i only the second half was scanned, and nothing showed the gap.

## The screen recording

Nominally 120 fps, about 9.7 on average, because a still screen writes few frames. Its frame times are a first index of change: `ffprobe -v error -select_streams v:0 -show_entries packet=pts_time -of csv=p=0 FILE | sort -n`. Look at each change at full size for private detail (emails, account names, file names).

**Sync it on events both clocks record:** a spoken cue finds the offset to a second or two, no closer; his face lit by the screen (the front camera's face brightness against the screen's, `crop=...,signalstats`) or his key clicks on the lav against characters appearing fixes it to the frame. On 12 Oct the two agreed within 0.04 s across 15 minutes; the creation time was 1.77 s out. Confirm at a second event far from the first; if they disagree, the recording paused between them.

**As footage,** conform the stretch to the timeline's rate, whole frame, before editing: `ffmpeg -i SCREEN.mov -vf "fps=25,trim=start=S:end=E,setpts=PTS-STARTPTS" -c:v prores_ks -profile:v 3 OUT.mov` makes frame n the screen at S + n/25, within one frame: `fps=25` lays frames on a 0.04 s grid from the file's start, so frame 0 can be up to a frame after S (22 Oct; run 4). Seeking with `-ss` before `-i` can drop the frame on screen at S.

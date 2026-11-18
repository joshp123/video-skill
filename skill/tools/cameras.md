<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: Josh's rig, reading facts from the files, ingest, sync and how to prove it, face touches, and the screen recording. Updated by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: project.py and the plan's header in place of create_project.py and edit.json. Facts about one recording (its lens, offsets, framing, room tone) go in that session's inventory.md, never here. -->

This is the ingest stage: the assistant editor's job. Its outcome is everything later stages stand on, proven rather than assumed: every file copied and checked, the video's Resolve project made with the two cameras synced, the lav on the front camera's clock, each camera's picture offset established, both transcripts of the lav (`tools/transcription.md`), both cameras scanned for face touches, and `inventory.md`, `screen-recording.md` and `record.md` written. The lav comes first and is transcribed at once, so the story can be read while the cameras may still be set up. One session can hold several videos: ingest once per session, and check an earlier ingest's claims against the files before reusing them.

# Cameras, ingest and sync

## The rig

The specifications are in `~/code/gear/camera-gear/` (start at `inventory.md`); it lags his purchases, so check his mail when it looks incomplete. Which lens, which profile and which settings a session used are facts about that session: establish them from the files and write them in its `inventory.md`.

| Role | Device | How it records |
| --- | --- | --- |
| Front, the main camera | Nikon Z f | Up to 3840 by 2160, 10-bit H.265 `.MOV`, in N-Log, auto white balance; a large sensor with fast lenses, so his background falls out of focus |
| Wide | DJI Osmo Pocket 4 | Up to 3840 by 2160, 10-bit H.265 `.MP4`, in D-Log, auto white balance; a fixed 20 mm-equivalent f/2 lens on a 1-inch sensor, so everything stays sharp |
| Dialogue | DJI Mic Mini on Josh | Into the Pocket's file, as stereo AAC with identical channels. The transmitter records nothing itself, so a dropped radio link loses that dialogue. The Pocket's sound is therefore the lav's radio feed, delayed against its own picture |
| Screen | macOS screen recording | Silent, variable frame rate, at the display's native size |

Auto white balance is his choice: "i'm not at that skill level yet (or effort level). so we must figure things out how to do easily?", and "most of the time i do actually want it AWB". The grade handles it (`roles/colour.md`); never ask him for a set-up routine.

## Read the facts from each file

`ffprobe -v error -show_streams -show_format -of json CLIP` gives codec, size, rate, frame count and audio. It cannot show a log profile: both cameras tag their files BT.709 whatever they recorded, so a profile read from a tag is wrong. ExifTool on the Nikon reads its picture control, lens, aperture and focus distance (it is not on the `PATH`: `"$(ls -d /nix/store/*-Image-ExifTool-*/bin/exiftool | sort -t- -k5 -V | tail -1)"`). The Pocket's per-frame data sits in a DJI track ExifTool cannot read: confirm D-Log by eye (a flat, low-contrast picture) and from the camera's setting. Write each fact into `inventory.md` with how it was established.

**Never sync on the clocks.** The two cameras' timecodes and file creation times disagree with each other and with the sound: on one session the timecodes were about seven hours apart, and creation times put the wide camera 15 s after the front when the sound put it 36.7 s after.

## Ingest

- **Cards.** The Nikon mounts as `/Volumes/NIKON Z F  ` (two trailing spaces), clips under `DCIM/`; the Pocket's as `Osmo SD 1TB`, clips under `DCIM/DJI_001/` with `.LRF` proxies, and its internal storage can mount too. Quote every path. Never erase a card.
- **Copy and prove the copy.** `pipeline/ingest/clone.py PROJECT SOURCE DESTINATION` uses Resolve's own Clone Tool (SHA-256, folder names kept), but it needs Resolve running with the named project current, and it waits up to 30 minutes for that project; before the video's project exists, copy with `ditto` instead. Either way, check every copy against the card with `shasum -a 256` on both sides. Where the copies land has varied, so look.
- **The lav first, on one clock.** The lav comes first because the story is read from it, while the cameras may still be set up. Extract it from the Pocket's file, then pad it onto the front camera's clock once per session, so a lav second is a front-camera second everywhere; name the padded file in `inventory.md` and point the plan's `sound.lav` at it. A session may already hold one: look before making another.
  ```sh
  ffmpeg -i POCKET.MP4 -map 0:a:0 -ar 48000 -c:a pcm_s24le SESSION/audio/lav_48k.wav
  ffmpeg -i SESSION/audio/lav_48k.wav -af "adelay=delays=SAMPLES:all=1" -c:a pcm_s24le SESSION/audio/lav_front_48k.wav
  ffmpeg -i SESSION/audio/lav_front_48k.wav -ac 1 -ar 16000 -c:a pcm_s16le SESSION/audio/lav_front_16k.wav
  ```
  SAMPLES is the offset in samples with an `S` suffix (`1763382S` for 36.737125 s at 48 kHz); a negative offset is an `atrim` from its start instead. The offset is the Pocket's sound against the front camera's sound (front time = Pocket time + offset). Find it before Resolve is involved by cross-correlating the lav with the front camera's own microphone (numpy and scipy are in `pipeline/joins`' environment), to the sample, and confirm it at three points spread across the take so drift would show; the multicam's sync and `sync.py` (below) confirm it again to within a frame. Transcribe from the padded 16 kHz file, so every transcript is on the front camera's clock and `verbatim_transcript.py` takes no offset (`tools/transcription.md`).
- **The video's folder, then the plan's header, then the project.** Make the video's folder, `Edits/YYYY-MM-DD-slug/` (the recording's date and a short name for the tool), and name its Resolve project the same way with a space, "YYYY-MM-DD slug". Ingest starts the folder's `plan.json` with the facts every later command needs, and nothing editorial (the format is at the top of `pipeline/b/assemble.py`): `resolve_project`, `look`, `fps`, `format`, `multicam` (`"cameras"`), each camera's `file` (relative to the video's folder), `log` (Resolve's own name for its input colour space, such as `"Nikon N-Log"` or `"DJI D-Gamut/D-Log"`), `group`, a starting `grade` (the look's `colour.feel`, which colour then owns) and `picture_offset_s`, with `reference: true` on the front camera; `sound.lav`; and `transcript`. Then `pipeline/b/project.py plan.json` (it reads only those header keys, which the plan shares with an edit list) makes the project: colour management set and read back, one colour group per camera, project media and cache on the media drive, the cameras and the lav in a Source bin with their input colour spaces, and the cameras' multicam made and synced by their sound, printing each angle's offset for `inventory.md`. 21 s. `project.py` needs every camera's `picture_offset_s` before the picture offsets are proven: start each from the sound offset (0 on the front camera), and correct it once it is established picture against picture (below).

## Sync, and how to prove it

The multicam's audio sync, which `project.py` runs, gives one offset. `pipeline/ingest/sync.py PROJECT FRONT_FILE WIDE_FILE` (front first: its clock is the master) gives a second: it places both on a scratch timeline, runs `AutoAlignClips` by waveform, prints `first time = second time + OFFSET`, and deletes the timeline; it needs Resolve's scripting variables set (`tools/resolve.md`, "Driving it") and the project open, and has not been run since the rebuild. The two have agreed to within a frame. Both measure sound against sound and report one offset, with no drift. So prove it as an assistant editor would:

- the clap's transient in both waveforms within a frame;
- late in the take, his lips closing on a "p", "b" or "m" on each camera as the lav's sound starts, which shows drift;
- **each camera's picture against the sound on its own.** The Pocket's picture can run about a frame ahead of its own sound, because its sound is the delayed radio feed. A camera whose picture is a frame or more off its sound gets its own picture offset.

Each camera's picture offset goes into the plan's `cameras` block as `picture_offset_s` (0 on the front camera), established picture against picture and written in `inventory.md` with how. `assemble.py` computes every segment's source frame from it, and the gate times lip sync from it (`tools/faults.md`, "Lips out of sync, or a frozen picture while he speaks"). Apply every offset once: front-camera time = a file's own time + its offset; a lav padded onto the front clock has offset 0, and adding the offset as well moves every word twice.

## Face touches

His standard: "cut all the moments where i touch my face etc (as a pro director would do)". `scripts/face_touch.swift`, on Apple's Vision, flags each frame where a hand has three or more confident points inside his face's box enlarged by 15%; its header has the commands. Extract frames at five a second from the whole file into the media drive's `Edits/.cache/`, and run it detached, while the story is being read: about five minutes a camera for a 23-minute take. It has caught every touch a frame-by-frame check found, and flagged gestures near the neck as well; it has missed a scratch behind the ear that the other camera's scan caught. So scan both cameras from first frame to last and read the two scans together: a touch on either is a touch on both. Write in `inventory.md` what each scan covered, so a gap shows.

## The screen recording

macOS writes a frame only when the screen changes, so the file's nominal rate (120 fps) says little: a still screen writes few frames. Its frame times are a first index of what changed: `ffprobe -v error -select_streams v:0 -show_entries packet=pts_time -of csv=p=0 FILE | sort -n`. Look at each change at full size for private detail (emails, account names, file names).

**Sync it on events both clocks record.** A spoken cue finds the offset to a second or two, no closer. His face lit by the screen (the front camera's face brightness against the screen's, `crop=...,signalstats`), or his key clicks on the lav against characters appearing, fixes it to the frame. Confirm at a second event far from the first; if they disagree, the recording paused between them. Creation times can be seconds out. Write the offset and the index in the session's `screen-recording.md`.

**As footage,** conform the stretch to the timeline's rate before editing:

```sh
ffmpeg -i SCREEN.mov -vf "fps=25,trim=start=S:end=E,setpts=PTS-STARTPTS" -c:v prores_ks -profile:v 3 OUT.mov
```

Frame n of the result is the screen at S + n/25, within one frame: `fps=25` lays frames on a 0.04 s grid from the file's start, so frame 0 can be up to a frame after S. Seeking with `-ss` before `-i` on this variable-rate file can drop the frame that was on screen at S, so trim inside the filter.

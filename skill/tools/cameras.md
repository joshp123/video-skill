<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: Josh's rig, reading facts from the files, ingest, sync and how to prove it, face touches, and the screen recording. Updated by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: project.py and the plan's header in place of create_project.py and edit.json; then pipeline/b/ingest.py in place of the hand steps and pipeline/ingest/. Facts about one recording (its lens, offsets, framing, room tone) go in that session's inventory.md, never here. -->

This is the ingest stage: the assistant editor's job. Its outcome is everything later stages stand on, proven rather than assumed: every file copied and checked, the video's Resolve project made with the two cameras synced, the lav on the front camera's clock, each camera's picture offset established, the verbatim transcript of the lav (`tools/transcription.md`), both cameras scanned for face touches, and `inventory.md`, `screen-recording.md` and `record.md` written. `pipeline/b/ingest.py` does the measurable part in one call and lists what is left for you; the sections below say what it does and what only eyes settle. The lav comes first and is transcribed at once, so the story can be read while the cameras may still be set up. One session can hold several videos: ingest once per session, and check an earlier ingest's claims against the files before reusing them.

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
- **One call.** Make the video's folder name first: `Edits/YYYY-MM-DD-slug/` (the recording's date and a short name for the tool); its Resolve project is named the same way with a space, "YYYY-MM-DD slug". The session's folder is `Edits/YYYY-MM-DD-...-session/`. Then, in `pipeline/`'s devenv:
  ```sh
  devenv shell -- python3 b/ingest.py start --session SESSION --video VIDEO --source CARD_OR_FILE [--source ...]
  devenv shell -- python3 b/ingest.py status --session SESSION --wait 100
  ```
  `start` returns at once and the work runs detached; call `status` until it says `finished`. Each `--source` is a camera file, the screen recording or a card's folder. It tells the files apart by their own tags (`pipeline/README.md` has what it does, in order, and how long each part took). Read `facts` (each with how it was measured) and act on every line of `needs_the_model`.
- **What it proves.** A card's clips are copied with `ditto` into `Media/Input Media/<camera>/<session>/` and every copy is hashed (SHA-256) against its card; files already in `Input Media` are hashed against the session's `metadata/copy-manifest.json` if there is one. Copying from a card has not been tested. The lav is extracted from the Pocket's file and its offset on the front camera's clock measured by cross-correlation against the front camera's own microphone at five points across the take, so drift shows; it is padded onto that clock (`audio/lav-front-48k.wav`, the front file's length to the sample) with its 16 kHz mono copy, and the verbatim transcript starts at once. The plan's header is written into the video folder's `plan.json` (the format at the top of `pipeline/b/assemble.py`: nothing editorial), a measured section is appended to the session's `inventory.md`, and `pipeline/b/project.py` makes the project from the header: colour management set and read back, one colour group per camera, project media and cache on the media drive, the cameras and the lav in a Source bin with their input colour spaces, and the cameras' multicam synced by their sound.
- **The offset is the median of the five points,** so half the drift falls either side of the middle of the take. On 12 October the five ran from 36.7370 to 36.7468 s (front time = Pocket time + offset), a straight line of about 12 ms over the take, under a frame: no speed correction. Ingest asks you to decide on one only when the drift passes half a frame.
## Sync, and how to prove it

Ingest measures three offsets and prints each with how: the lav against the front camera's microphone (sound against sound, five points), the wide camera's picture against the front camera's from his head's motion (the face's centre seen by both cameras, cross-correlated at 25 fps in five 20 s windows; on 12 October most windows peaked at the sound offset and October's lip measurement was 40 ms later, so treat it as evidence, not as the offset), and Resolve's multicam sync by sound in whole frames. When the picture measurement's windows agree, the header carries it as the wide camera's `picture_offset_s`; when they do not (on 12 October they fell in two clusters 80 ms apart), it carries the lav's offset and asks you to settle it by eye before cutting (below). A second video from the same session starts from the first one's plan: `ingest.py header --like` (`pipeline/README.md`). What it cannot measure, prove as an assistant editor would:

- the clap's transient in both waveforms within a frame;
- late in the take, his lips closing on a "p", "b" or "m" on each camera as the lav's sound starts, which shows drift;
- **each camera's picture against the sound on its own.** The Pocket's picture can run about a frame ahead of its own sound, because its sound is the delayed radio feed; that is why the wide camera's offset is measured picture against picture and not from its sound. A camera whose picture is a frame or more off its sound gets its own picture offset.

Each camera's picture offset is in the plan's `cameras` block as `picture_offset_s` (0 on the front camera), written in `inventory.md` with how. `assemble.py` computes every segment's source frame from it, and the gate times lip sync from it (`tools/faults.md`, "Lips out of sync, or a frozen picture while he speaks"). Apply every offset once: front-camera time = a file's own time + its offset; a lav padded onto the front clock has offset 0, and adding the offset as well moves every word twice.

## Face touches

His standard: "cut all the moments where i touch my face etc (as a pro director would do)". `scripts/face_touch.swift`, on Apple's Vision, flags each frame where a hand has three or more confident points inside his face's box enlarged by 15%; ingest runs it on both cameras' whole files at five a second and writes `face-touch/front.csv` and `wide.csv` on the front camera's clock, with the flagged moments in `needs_the_model`. It has caught every touch a frame-by-frame check found, and flagged gestures near the neck as well; it has missed a scratch behind the ear that the other camera's scan caught. So read the two scans together: a touch on either is a touch on both. Look at each flagged moment on full-size frames.

## The screen recording

macOS writes a frame only when the screen changes, so the file's nominal rate (120 fps) says little: a still screen writes few frames. Its frame times are a first index of what changed; ingest writes them to a file it names in `needs_the_model`. Look at each change at full size for private detail (emails, account names, file names).

**Sync it on events both clocks record.** A spoken cue finds the offset to a second or two, no closer. His face lit by the screen (the front camera's face brightness against the screen's, `crop=...,signalstats`), or his key clicks on the lav against characters appearing, fixes it to the frame. Confirm at a second event far from the first; if they disagree, the recording paused between them. Creation times can be seconds out. Write the offset and the index in the session's `screen-recording.md`.

**As footage,** conform the stretch to the timeline's rate before editing:

```sh
ffmpeg -i SCREEN.mov -vf "fps=25,trim=start=S:end=E,setpts=PTS-STARTPTS" -c:v prores_ks -profile:v 3 OUT.mov
```

Frame n of the result is the screen at S + n/25, within one frame: `fps=25` lays frames on a 0.04 s grid from the file's start, so frame 0 can be up to a frame after S. Seeking with `-ss` before `-i` on this variable-rate file can drop the frame that was on screen at S, so trim inside the filter.

<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: how the dialogue is laid, levelled, measured and seen, and what nobody here can yet hear. What a good join is lives in roles/editor.md. -->

# Audio

The lav is the only dialogue. The cameras' own microphones are for sync and nothing else: one of them may be the lav's own radio feed, delayed. What a good join sounds like, and why, is in `roles/editor.md`, "Nobody hears a cut"; this file is the mechanics.

## The dialogue track

`pipeline/b/sound.py`, which `place.py` runs after the picture, lays the list's `audio` rows and `sound` block exactly as written: every piece on A1 in list order, room tone on A2 under the gaps only. It decides nothing.

- **Edges to the sample.** Resolve rounds an audio source point to a whole frame when it places a clip (up to 20 ms at 25 fps, enough to clip a consonant or let a click in). So `sound.py` places at whole frames, exports the timeline's file, rewrites every edge and fade exactly, imports it back and checks each one: edges and fades read back to within 1e-10 ms (25 and 26 Oct). The one call that takes samples, `InsertAudioToCurrentTrackAtPlayhead`, returned False because it acts on the current track and no call selects one (21 Oct).
- **Fades** take fractional frames (`SetFades`). Resolve keeps a clip's two fades at least a frame shorter than the clip, so a room-tone fill too short for its fades is grown equally at both ends.
- **A crossfade** is Resolve's own "Cross Fade 0 dB", centred on the cut: added with `AddTransition` at a whole frame, then set to its sub-frame start and length in the file. It plays half its length of source beyond the cut on each side, so it needs that much handle, which one continuous lav always has, and it brings back whatever the cut left out within that half. Crossfades as short as 0.625 frame read back exactly (26 Oct). `readback.py` lists crossfades apart from clips.
- **Room tone** fills each gap from the list's window. A gap longer than the window is laid as equal loops of it, crossfaded by the list's crossfade, on A2.
- **Voice Isolation and the Dialogue Leveler** go on a piece when its row asks. Patches that change gain or borrow sound from elsewhere are refused: neither is proven on one track.

`pipeline/b/splice.py` builds the same dialogue as one file outside Resolve, with clean-up and mastering. It exists for a cut that needs what Resolve cannot yet do by script; say in the hand-over when it made the sound, and prefer Resolve.

## Level

The delivery is -14 LUFS integrated with a true peak at most -1 dBTP, the level YouTube normalises to and the usual target for social video. Measure the delivered file, because the encode can raise a peak.

- `Timeline.NormalizeAudioLevel` changes gain only (p. 1110): it left raw lav at -25.2 LUFS against a -14 target, and -24.8 with Voice Isolation and the Dialogue Leveler on (21 Oct). Gain alone cannot bring speech with peaks to -14 without clipping, which needs a limiter.
- **No script call sets a compressor or a limiter.** The delivered loudness comes from Resolve's render-time "Optimize to Standard" (BS.1770-4), carried in a render preset that `pipeline/b/loudness.py --preset-dir DIR --target LUFS --ceiling DBTP` writes and imports, printing its name. It undershoots: a target of -13 LUFS with a -1 dBTP ceiling measured -15.2 to -15.5 LUFS at -1.2 dBTP on two tests. Set the target above what you want, measure the file, and adjust.
- **An untested lead:** the Fairlight Presets Library stores dynamics and whole bus settings (p. 3820), and `Project.ApplyFairlightPresetToCurrentTimeline` applies a preset by name. Whether a bus limiter applied that way survives and renders is untested; it could replace the render-time optimisation.

Every render the gate measures loads the loudness preset (`tools/faults.md`, "Running the gate").

## Finding an edge

The transcript finds the word; the lav finds the cut. `pipeline/b/envelope.py LAV --from S --to S --quiet-dbfs L --near T` prints the RMS level of the louder channel every 5 ms, the runs below L, and the quiet step nearest T.

- **Measure this recording's floor first,** from a stretch where he says nothing: the level of the room is a property of the room, the mic's placement and its gain, and differs on every recording. Set the quiet level a few dB above the floor and well below his speech; an edge that sits well above the floor is inside a word or a breath.
- **Room tone** is a window of several seconds where no 5 ms step rises above the floor, checked again high-passed at 1 kHz and 4 kHz against the window's own median. A low hum in the floor can hide clicks from a full-band trace, and a click in the window repeats under every pause.
- **Pitch.** How a speaker ends a finished sentence differs: some fall, some stay level. Measure his endings in this take with any frame-by-frame pitch tracker before you judge a join by pitch. Praat through `parselmouth` does not build in the pipeline's devenv (22 Oct).

## Seeing a join

Draw a second either side of a join: the outgoing source, the incoming source and the placed sound, each as a waveform and a spectrogram, with the edges marked. That shows a click, a clipped consonant, a release cut off, a scrap of the next word, or room tone starting hard on a tail. `ffmpeg -filter_complex "[0:a]showspectrumpic=s=1600x600"` draws one. Whisper on a short fragment tells you which word it sounds like, and invents words on very short pieces.

Neither shows whether a join sounds natural: a join can look clean on both and be heard as an edit.

## What nobody here can do yet

No model available here has been shown to hear whether a join sounds natural. On 29 Oct every free route was tried on six clips with known faults: Ollama cloud and the Codex models take no audio, and four local models gave the same answer for all six (`history.md`, "Listening"). The untested lead is a larger audio model on the Mac mini. Until one passes a test like that, joins are judged from the level, the spectrogram, the pitch and his mouth on the picture, and the few that stay uncertain are named for Josh. When a route passes, the director names it in the briefs and this section changes.

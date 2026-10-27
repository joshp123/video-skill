<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J). -->

# Audio

The lav is the only dialogue; the cameras' own microphones are for sync. What a good join sounds like is in `roles/editor.md`; this file is the tested mechanics.

## The dialogue track

`pipeline/b/sound.py`, which `place.py` runs after the picture, lays the list's `audio` rows and its `sound` block exactly as written: every piece on A1 in order, room tone on A2 under the gaps only.

- **Resolve rounds an audio source point to a whole frame** when placing (100.4 became 100, 150.7 became 151, 21 Oct): up to 20 ms at 25 fps, enough to clip a consonant. When the lav was laid in whole frames with no fades on 14 Oct, the render had clicks at two cuts and three words clipped or leaking. So `sound.py` places at whole frames, then writes each exact edge into the timeline's file and imports it back: every edge and fade read back to within 1e-10 ms (25 and 26 Oct). `InsertAudioToCurrentTrackAtPlayhead`, the one call that takes samples, returned False: it acts on the current track and no call selects one (21 Oct).
- **Fades** take fractional frames (`SetFades`). Resolve keeps a clip's two fades at least a frame shorter than the clip, so a room-tone fill too short for that is grown equally at both ends.
- **A crossfade** where a row asks for one is Resolve's own "Cross Fade 0 dB", centred on the cut: added with `AddTransition` at a whole frame, then set to its sub-frame start and length in the file. Three, as short as 0.625 frame, read back exactly; outside them the render was identical below -90 dBFS to the earlier two-track layout (26 Oct). It needs handles: half its length of source beyond the cut on each side, which a range of one continuous lav always has. `readback.py` lists crossfades apart from clips.
- **Room tone** fills each gap from the list's window; a gap longer than the window is laid as equal loops crossfaded by the list's crossfade on A2.
- **Voice Isolation and the Dialogue Leveler** go on a piece when its row asks. Patches that change gain are refused. `pipeline/b/splice.py` is the fallback executor outside Resolve, with the earlier videos' clean-up and mastering, for a cut that needs those; say in the hand-back which one made the sound.

## Level

The platforms expect -14 LUFS integrated and at most -1 dBTP; measure the delivered file, because the encode can raise a peak. `NormalizeAudioLevel` is gain only (p. 1110): it left raw lav at -25.2 LUFS against a -14 target, and -24.8 with Voice Isolation and the Dialogue Leveler on (21 Oct). No call sets a compressor or limiter. The delivered loudness comes from a render preset `pipeline/b/loudness.py` writes (Resolve's Optimize to Standard): a target of -13 LUFS with a -1 dBTP ceiling measured -15.2 to -15.5 LUFS at -1.2 dBTP on two tests, so set the target about 2 LU above what you want and measure the file.

## Finding an edge: `envelope.py`

The transcript finds the word; the lav finds the cut. `envelope.py LAV --from S --to S` prints the RMS level every 5 ms, the runs under a level you give, and the quietest point near a time you give. Measure this recording's floor first and choose your level from it: the 12 Oct lav measured speech at about -30 dBFS RMS and a floor of -52 dBFS (21 Oct), and a noisier room puts its silence higher. An edge above about -40 dBFS on that lav was inside a word or a breath.

**Room tone:** several seconds where no 5 ms window rises above the floor, checked again high-passed at 1 kHz and 4 kHz against the window's own median. The 12 Oct lav's floor is a hum at 80 to 160 Hz that hides clicks from a full-band trace: a window that measured clean full-band held two clicks above 1 kHz, and another editor's first window held one that would have repeated under every pause.

**Pitch:** measure how he ends his finished sentences in this take before judging a join. On 12 Oct his pitch stayed level at almost every full stop (median +0.1 semitones over 32 ends), so a level ending was finished for him and a rise sounded unfinished; the textbook falling ending would have flagged nearly every line. Praat through `parselmouth` does not build in the pipeline devenv (22 Oct); any frame-by-frame pitch tracker serves.

## Seeing a join

Draw a second either side of each join: the outgoing source, the incoming source and the placed sound, as waveform and spectrogram, marked at the edges. That shows a click, a clipped consonant, a scrap of the next word, room tone starting hard on a tail. Whisper on a short fragment tells you which word it sounds like (it heard a 110 ms "or" as "We'll", 17 Oct) and invents words on very short pieces. Neither tells you a join sounds natural: two joins on where-was-i looked clean and a listener heard both as edits.

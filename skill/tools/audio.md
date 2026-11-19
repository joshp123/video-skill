<!-- Rewritten by AI on 2026.11.19 by model claude opus 5.5 from the 18 Nov file: the sound facts of Josh's rig, what the join placer and checker do and miss, and loudness in Resolve. What a good join is lives in roles/editor.md. -->

# Audio

The lav is the only dialogue. The cameras' own microphones are for sync and nothing else, and the Pocket's sound is the lav's own radio feed, delayed against its picture (`tools/cameras.md`).

## Nobody here can listen

No model available here hears whether a join sounds natural. On 29 Oct every free route was tried on six clips with known faults (Ollama Cloud's models and the Codex plan refused audio; four local audio models gave the same answer for clean and broken clips alike), and Fable 5.2 and the GPT models take no audio (17 Nov). The join checker below measures what can be measured; pitch, breath and meaning at a join are judged from the words and the waveform, and what stays uncertain goes to Josh with the cut, at most three moments. When a listening route passes a test like that one, this section changes.

## Placing the edges

`pipeline/joins/` places each edge of a kept piece inside a measured pause of the lav, from the rough word times the transcript gives. It reads the room floor round each edge from this recording itself (so it carries to a new room), finds the pause nearest the estimate, and cuts on room tone at a point that leaves half the crossfade on room tone, so a breath or a word's decay in the pause is kept whole or left out, never cut through. For each edge it reports how far the transcript was out and, when the nearest pause lies beyond a sound you may not want (an um, a breath), the words in between. An edge with no pause next to it means the word runs straight into the next: that cut is inside connected speech, which a listener can hear. A bad edge has three answers, in order: another edge word or take; an edge you set by hand on the lav's clock; or keeping it with a reason. `pipeline/joins/README.md` explains every field.

## Checking every join

The join checker scores every join for the faults a listener hears: a word cut short, a clipped start, a scrap of a removed word, a click, a jump in room sound, a cut inside connected speech. It is a small classifier on a frozen speech model's features (WavLM-Large) and about twenty plain signal measures, trained on joins built from 291 audiobook speakers and from his 12 Oct lav. Its threshold is fitted to each recording from about 200 clean joins spliced from that recording's own pauses, so a new microphone, room or voice usually needs nothing.

On his held-out codex-switch joins, at its default setting, it caught 93% of faults and flagged 2.8% of clean joins (17 Nov; "bad" means made bad on purpose: nobody listened to the test joins). Score the joins on the mix as placed, before loudness normalisation, which moves them (below), and with the exact join times, because scores move by up to 0.35 with times 20 to 40 ms out. Each join reports a score, a flag, `borderline` within 0.03 of the threshold (treat it as flagged), the likely kind of fault (right about 78% of the time: trust the flag, take the kind as a hint), and two level steps: speech after the join minus before, and room sound either side.

### What it misses

- **Level steps between takes:** not flagged at all. Ordinary speech changes level by 3 to 5 dB from one sentence to the next; a step beyond about 6 dB between two takes is heard as two recordings, so the answer is another take.
- **Room-sound jumps of 6 dB or more:** 74% caught.
- **Weak consonant tails** cut into the room floor: the most-missed chops.
- **Pitch, breath and meaning:** an unfinished phrase joined to a new sentence, two breaths in a row, a join that makes no sense. Nothing here measures these.

Word ends cut short, clipped starts, scraps, clicks and cuts inside connected speech: 97 to 100% caught. Retraining is worth it only when the checker reports the recording `off_model` on every video from a new set-up (`pipeline/joins/README.md`).

## The dialogue track

- **Edges to the sample.** Appending rounds an audio source point to a whole frame, up to 20 ms at 25 fps, enough to clip a consonant or let a click in; the sub-frame trim calls set it exactly (`tools/resolve.md`, "Editing the live timeline").
- **Crossfades** are Resolve's "Cross Fade +3 dB" (constant power), centred on the cut, which is how the checker joins pieces. With the linear "Cross Fade 0 dB" the render's join scores rose by up to 0.25 (18 Nov). A crossfade plays half its length of source beyond the cut on each side, so it brings back whatever the cut left out within that half.
- **Fades** take fractional frames; Resolve keeps a clip's two fades at least a frame shorter than the clip.
- **Room tone** fills every gap from one window of the same recording, looped and crossfaded when a gap is longer than it.

**Choosing the room-tone window.** Several seconds where he says nothing and nothing moves: no click, breath, rustle or chair. A tick in that window repeats under every pause in the film, and a full-band level can hide it under hum, so measure the window again high-passed at 1 kHz and 4 kHz, looking for any short stretch far above its median.

## Level

The delivery is -14 LUFS integrated with a true peak at most -1 dBTP, measured on the delivered file, because the encode can raise a peak.

- `Timeline.NormalizeAudioLevel` changes gain only (p. 1110): it left raw lav at -25.2 LUFS against a -14 target (21 Oct). Speech with peaks needs a limiter to reach -14, and no script call sets a compressor or a limiter.
- **The delivered loudness comes from Resolve's render-time "Optimize to Standard"** (BS.1770-4), carried in a render preset the pipeline writes. It undershoots, so set the target above what you want and measure the file: a -12 LUFS target with a -1 dBTP ceiling gives -14.5 LUFS and -1.2 dBTP.
- **It is not one fixed gain:** against the lav joined exactly, the render's gain moved by 1 to 5 dB across cuts, and it raised clean joins' scores. With it off, the render matched the joined lav to -93 dB or better (18 Nov). It also sticks to the project: only a preset with it off turns it off.
- **An untested lead:** the Fairlight Presets Library stores dynamics and bus settings (p. 3820), and `Project.ApplyFairlightPresetToCurrentTimeline` applies one by name. Whether a bus limiter applied that way renders is untested; it could replace the render-time optimisation.

## Seeing a join

When a flag's kind does not explain itself, draw a second either side of the join: the outgoing source, the incoming source and the rendered sound, each as a waveform and a spectrogram, with the cut marked. That shows a click, a clipped consonant, a release cut off, a scrap of the next word, or room tone starting hard on a tail. It does not show whether a join sounds natural.

How a speaker ends a finished sentence differs: some fall, some stay level. Look at his endings in this take with a frame-by-frame pitch tracker before judging a join by pitch. Praat through `parselmouth` did not build in the pipeline's devenv (22 Oct).

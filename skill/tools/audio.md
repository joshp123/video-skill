<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5. Rewritten by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: edges placed by pipeline/joins and set to the sample through 21.2's sub-frame calls, every join scored by the trained check, the October level traces and splice retired. What a good join is lives in roles/editor.md. -->

# Audio

The lav is the only dialogue. The cameras' own microphones are for sync and nothing else: one of them may be the lav's own radio feed, delayed. What a good join sounds like, and why, is in `roles/editor.md`, "Nobody hears a cut"; this file is the mechanics.

## Placing the edges: `joins place`

`pipeline/joins/joins place` (run by `assemble.py` for every plan) cuts each kept piece inside a measured pause of the lav, from the rough word times the transcript gives. It reads the room floor around each edge (the quietest 5% of its 10 ms levels within 10 s), takes a pause as at least 80 ms within 10 dB of that floor, and uses the pause nearest the estimate within 0.6 s either side of it. Inside that pause the cut falls on a 10 ms frame within 4 dB of the floor (room tone), the one nearest the pause length wanted that still leaves half the crossfade on room tone, so a breath or a word's decay in the pause is kept whole or left out, never cut through. Every number it uses comes from this recording's own floor, so it carries to a new room. Its full report for each edge (how far the transcript was out, the words between the estimate and the pause, the quietest point near the estimate when no pause is close) is in `build/assemble/joins-place.json`; `pipeline/joins/README.md` explains every field.

When a piece's word runs straight into the next, with no pause, `assemble.py` aligns the words either side (`pipeline/b/words.py`) and, if the cut fell inside a word, moves it to the middle of the gap between the aligned words and reports that it did. A bad edge has three answers, in order: another edge word or take; a hand-set edge (`start_s` or `end_s` on the piece, on the lav's clock), which `assemble.py` gives `joins place` as an exact cut (`start_at`, `end_at`), and `place` scores every join again; or keeping it with a reason.

## Checking every join: `joins check`

`pipeline/joins/joins check` scores every join for the faults a listener hears: a word cut short (`chop_end`), a clipped start (`clip_start`), a scrap of a removed word (`scrap`), a click, a jump in room sound (`room`), a cut inside connected speech (`connected`). It is a small classifier on a frozen speech model's features (WavLM-Large) and about twenty plain signal measures, trained on joins built from 291 audiobook speakers and from the where-was-i stretch of his 12 Oct lav, never on the codex-switch stretch. One frozen model, `model/joins.pkl`, is named by its SHA-256 in every result: if a flag changes and the SHA does not, the sound changed. Its flag's threshold is fitted to each recording: it splices about 200 clean joins from that recording's own pauses, in the stretch being edited, and sets the threshold so the false-alarm setting's share of them is flagged; the result reports that stretch as `calibration_span` (`private/research/2026-11-17/join-check/RESULTS.md` holds the evaluation). `assemble.py` runs it on the joins as placed, from the lav; `cut.py` runs it again on the finish timeline's sound as mixed (rendered with loudness normalisation off, which the normaliser would otherwise move: below), which is the check that counts, because it hears the fades, crossfades and room tone as placed, giving it the lav and the lav check's `calibration_span` so both use one threshold, and the exact join times (scores move by up to 0.35 with times 20 to 40 ms out). `cut.py` lists every join's two scores side by side.

For each join it gives a `score` from 0 to 1, a `flag`, `borderline` when the score is within 0.03 of the threshold (treat it as flagged), the `likely` kind of fault with its usual fix (the table in `pipeline/joins/README.md`; the kind is right about 78% of the time on his held-out joins, so trust the flag and take the kind as a hint), and two level steps: `level_step_db`, the speech level after the join minus before, and `room_step_db`, the room sound either side of the cut. Ordinary speech changes level by 3 to 5 dB from one sentence to the next; a step beyond about 6 dB between two takes is heard as two recordings. The plan has no gain per piece yet, so the answer is another take.

The flag's default setting is a 10% false-alarm budget (choices 0.05, 0.1, 0.2); on his held-out codex-switch joins it flagged 2.8% of clean joins and caught 93% of faults. A false alarm costs you one re-placement and one check, never his attention, so treat every flag as a question to answer, not a verdict to argue with.

### What the join check misses

Measured on 2,600 joins made from the codex-switch stretch of his lav, which the model never trained on, at the default setting. Nobody listened to the test joins: "bad" means made bad on purpose. Word ends cut short, clipped starts, scraps of removed words, clicks and cuts inside connected speech: 97 to 100% caught.

- Level steps between takes: not flagged at all; each join reports `level_step_db` for you to judge.
- Room-sound jumps of 6 dB or more: 74% caught.
- Weak consonant tails: the most-missed chops in the earlier tests.
- Pitch, breath and meaning (a rising, unfinished phrase joined to a new sentence; two breaths in a row; a join that makes no sense): not measured by anything here. These are yours, by choosing takes and reading the words either side of every cut.

The check was trained on butt joins and on constant-power crossfades of 5 to 40 ms. A new microphone, room or voice usually needs nothing: the flag fits itself to each recording's own pauses. Retraining is worth it only when the check's header shows `off_model` (the recording's clean joins score well above what the model expects) on every video from a new set-up, with at least ten minutes of speech that will not be edited (`pipeline/joins/README.md`, "A new microphone, room or voice").

## The dialogue track

`pipeline/b/sound.py`, which `place.py` runs, lays the edit list's `audio` rows and `sound` block exactly as written: every piece on A1 "Dialogue" in order, room tone on A2 "Room tone" under the gaps only. It decides nothing.

- **Edges to the sample.** `AppendToTimeline` rounds an audio source point to a whole frame (up to 20 ms at 25 fps, enough to clip a consonant or let a click in). Since 21.2, `SetLeftOffset`, `SetRightOffset`, `SetPosition` and `MoveItems` take sub-frame values on audio, and read back exactly, while Resolve's preference "Align audio edits to frame boundaries" is off; with it on they return True and round. `sound.py` refuses to place sound while it is on (17 Nov; `tools/resolve.md`, "Placing and changing items").
- **A crossfade** is Resolve's own "Cross Fade +3 dB" (constant power), centred on the cut: that is how the join check joins pieces and what its model was trained on. Resolve's "Cross Fade 0 dB" is a linear crossfade, and with it the render's join scores rose above the lav check's by up to 0.25 (18 Nov). It is added at a whole frame, cannot be moved or trimmed by script, and disappears when a clip edge next to it is trimmed, so its sub-frame start and length go in through the timeline's file in the same round trip as the angles and captions (17 Nov). It plays half its length of source beyond the cut on each side, so it needs that much handle, which one continuous lav always has, and it brings back whatever the cut left out within that half.
- **Fades** take fractional frames. Resolve keeps a clip's two fades at least a frame shorter than the clip.
- **Room tone** fills each gap from the plan's `sound.room_tone_s` window. A gap longer than the window is laid as equal loops of it, crossfaded by `room_tone_crossfade_ms`.
- **Voice Isolation and the Dialogue Leveler** go on a piece when its row asks.

**Choosing the room-tone window.** Several seconds where he says nothing and nothing moves: no click, breath, rustle or chair. A tick in that window repeats under every pause in the film, and a full-band level can hide it under hum, so measure the window full band and again high-passed at 1 kHz and 4 kHz (`ffmpeg -ss A -t D -i LAV -af "highpass=f=1000,asetnsamples=480,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" -f null -` prints the level every 10 ms and look for any short stretch far above the window's median); write in the plan's `why` what you checked.

## Level

The delivery is -14 LUFS integrated with a true peak at most -1 dBTP, the level YouTube normalises to and the usual target for social video. Measure the delivered file, because the encode can raise a peak; the gate does, on every whole render.

- `Timeline.NormalizeAudioLevel` changes gain only (p. 1110): it left raw lav at -25.2 LUFS against a -14 target (21 Oct). Gain alone cannot bring speech with peaks to -14 without clipping, which needs a limiter.
- **No script call sets a compressor or a limiter.** The delivered loudness comes from Resolve's render-time "Optimize to Standard" (BS.1770-4), carried in a render preset that `pipeline/b/loudness.py --preset-dir DIR --target LUFS --ceiling DBTP` writes and imports, printing its name. It undershoots, so set the target above what you want, measure the file, and adjust. In this Resolve, "B loudness -12 LUFS -1 dBTP 282076f8" gives -14.5 LUFS and -1.2 dBTP. Pass its name as `--loudness` to `cut.py` and `render.py`.
- **The render's "Optimize" normalisation is not one fixed gain.** Against the lav joined exactly as the list says, the render's gain moved by 1 to 5 dB across cuts; with normalisation off, the render matched the joined lav to -93 dB or better (18 Nov). It raised two clean joins' scores in the render by 0.07 and 0.12 over the lav check's, and put one just over the flag as `borderline`: so `cut.py` scores joins on the mix before normalisation (`render.py --preset sound --loudness off`). **The normalisation sticks to the project:** a render without `--loudness`, or after loading a stock preset, still came out at -14.5 LUFS; only a preset with it off (`--loudness off`) turns it off.
- **An untested lead:** the Fairlight Presets Library stores dynamics and whole bus settings (p. 3820), and `Project.ApplyFairlightPresetToCurrentTimeline` applies a preset by name. Whether a bus limiter applied that way survives and renders is untested; it could replace the render-time optimisation.

## Seeing a join

When a flag's kind does not explain itself, draw a second either side of the join: the outgoing source, the incoming source and the rendered sound, each as a waveform and a spectrogram, with the cut marked (`ffmpeg -filter_complex "[0:a]showspectrumpic=s=1600x600"` draws one). That shows a click, a clipped consonant, a release cut off, a scrap of the next word, or room tone starting hard on a tail. It does not show whether a join sounds natural.

## Pitch

How a speaker ends a finished sentence differs: some fall, some stay level. Look at his endings in this take with a frame-by-frame pitch tracker before you judge a join by pitch. Praat through `parselmouth` did not build in the pipeline's devenv (22 Oct); ffmpeg and the joins devenv's Python are there.

## What nobody here can do yet

No model available here hears whether a join sounds natural. On 29 Oct every free route was tried on six clips with known faults and none could tell them apart (`history.md`, "Listening"); since then, nothing free has appeared, and Fable 5.2 and the GPT models take no audio (17 Nov). The join check measures what can be measured; pitch, breath and meaning at a join are judged from the words and the waveform, and what stays uncertain goes to Josh with the cut, at most three moments. When a listening route passes a test like that, it is named in `roles/director.md` and this section changes.

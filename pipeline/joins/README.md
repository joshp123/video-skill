<!-- Written by AI on 2026.11.17-18 by model Claude Opus 5.5. Measurements behind every number: private/research/2026-11-17/join-check/RESULTS.md, section "18 Nov 2026: the pipeline command". -->

# joins: place sound edges and check every join

A video keeps pieces of Josh's speech and removes the rest. Each place where two pieces meet is a join. This tool does two jobs:

- **`place`** cuts each kept piece inside a measured pause of the lav, from the rough word times you give it.
- **`check`** scores every join for the faults a listener hears: a word cut short, a clipped word start, a scrap of a removed word, a click, a jump in room sound, or a cut inside connected speech.

You choose which words stay, how long each pause is, and whether to accept a flagged join. The tool measures and reports; it never decides for you, and it never hides a problem it measured. A flagged join comes back to you to re-place. It does not go to Josh.

**The one model.** `model/joins.pkl`, SHA-256 `361f3c05041e` (first 12 digits), trained 18 Nov 2026 01:40. It learned from 291 audiobook speakers and from the where-was-i stretch of Josh's 12 Oct lav (694 to 1412 s). It never trained on the codex-switch stretch (57 to 681 s). Every result names the model that scored it (`model.sha256`). If a flag appears or disappears between two runs and the sha256 is the same, the sound changed, not the checker. If this model is ever retrained, the new date goes here.

## Setting up (once per machine)

```sh
cd pipeline/joins && devenv shell -- true      # builds .devenv/state/venv from requirements.txt (a few minutes the first time)
example/smoke.sh                               # runs every path once on Josh's lav (needs the media drive); prints "smoke: all paths ran"
```

The models live outside the repo, in `~/.cache/join-check/` (WavLM-Large, 2.5 GB, read offline). If that folder is missing, run once with `HF_HUB_OFFLINE=0 pipeline/joins/joins check ...` to download it. Leave `TMPDIR` alone when running `devenv` (a temp path with spaces breaks it). After setup, call `pipeline/joins/joins` from anywhere; it needs no shell. Every command writes JSON to stdout (or to `--out FILE`), and progress to stderr.

## place

```sh
pipeline/joins/joins place LAV PIECES.json [--words TRANSCRIPT.json] [--crossfade 0.04] [--false-alarm 0.1] [--out placed.json]
```

**LAV** is the lav recording, in any format ffmpeg reads; the first channel is used. **PIECES.json** lists the kept pieces in playing order:

```json
[
 {"start": 168.30, "end": 176.90},
 {"start": 178.02, "end": 182.26, "pause_after": 0.5},
 {"start": 186.28, "end_at": 189.20}
]
```

- `start` is the estimated start of the piece's first word, and `end` the estimated end of its last word, in seconds on the lav's clock. Transcript times work, but they can be half a second out: in `lav-verbatim-front.json` "Let" is given at 368.34 s and spoken at about 368.75, and "here" is given at 370.70 and spoken at about 371.19. Times refined by forced alignment place better.
- `pause_before` and `pause_after` are optional. They give the total pause you want at that join, in seconds, split evenly between its two sides. Without them, each side keeps about 0.15 s of its own pause. The output's `pause_after` says what each join got.
- `start_at` and `end_at` set an exact cut that `place` uses as given, with no search. Use them when you have chosen a cut yourself, for example the `quietest_near_estimate` that an edge reports.
- `--words` takes the transcript (a JSON object with a `words` list of `{start, end, word}`, like `transcript/lav-verbatim-front.json`). With it, each piece lists the words it now holds. That shows at once when a cut has taken in an "um", a breath or a word you meant to drop.
- `--crossfade` is the crossfade at every join, in seconds, centred on the cut. Set it to what the timeline really uses. The default, 0.04, is one frame at 25 fps; 0 means a butt join. The check was trained on butt joins and on crossfades from 5 to 40 ms.

**How each edge is placed.**
1. The tool reads the room floor around the edge: the quietest 5% of the 10 ms levels within 10 s either side.
2. A pause is at least 80 ms within 10 dB of that floor. The edge uses the pause nearest the estimate, within 0.6 s either side of it. For a start, that means the pause's end; for an end, the pause's start.
3. Inside that pause, the cut falls on a 10 ms frame within 4 dB of the floor (room tone). It takes the frame nearest the wanted pause length that is still far enough inside the pause for half the crossfade to fall on room tone. So a breath or a word's decay inside the pause is either kept whole or left out, never cut through.

**What comes back**, for each piece:

| Field | Meaning |
|---|---|
| `start`, `end` | The cut times on the lav. Use these as the clip's source in and out. |
| `start_edge`, `end_edge` | How each edge was placed, as described below. |
| `words` | With `--words`, the transcript words now inside the piece. |
| `pause_after` | Seconds of pause at the join after this piece (both sides added). |

Each edge (`start_edge` or `end_edge`) reports one of three things:

- `"status": "pause"` gives:
  - `pause`, the pause the cut is in;
  - `kept`, the seconds of pause kept on this side;
  - `on_room_tone`, whether the cut is on room tone;
  - `level_db_over_floor`, the level at the cut;
  - `word_edge`, where the speech starts or ends;
  - `estimate_off_by`, the word edge minus your estimate.

  If `estimate_off_by` is more than 0.25 s either way, the edge also lists `words_between_estimate_and_pause`, for example `"[UM]"`. That means the nearest pause lies beyond some sound you may not want. In that case it also gives `quietest_near_estimate`, a time and its level over the floor, which you can pass back as `start_at` or `end_at`.
- `"status": "no pause next to this word"` means the word runs straight into the sound before or after it. The edge is set at the quietest 10 ms near the estimate, so the plan can still be checked. `nearest_pauses` gives the pause before and after; with `--words`, it also gives the words in between (`words_to_before`, `words_to_after`). Choose another edge word, another take, set the edge yourself, or accept it knowingly.
- `"status": "given"` means you set the cut with `start_at` or `end_at`. It reports the level there over the floor.

`place` ends by running `check` on the pieces as placed (see `check`, below), so one call gives the cuts and their scores.

## check

From the lav, before anything is placed in Resolve:

```sh
pipeline/joins/joins check --lav LAV placed.json [--crossfade 0.04]
```

`placed.json` is the output of `place`, perhaps with cuts you edited. A plain list of `{start, end}` also works. The pieces are joined as Resolve will join them, each crossfade centred on its cut, and every join is scored.

From a file Resolve rendered. This is the check that counts, because it hears what will be delivered:

```sh
pipeline/joins/joins check --audio render.mov --at 8.97,13.62,16.66 --lav LAV --span 90-330
pipeline/joins/joins check --audio render.mov --joins join-times.json --lav LAV      # a JSON list of seconds
```

- The join times are seconds in the rendered file, at the cut (the centre of the crossfade). The `at` values that `place` returns are times in the joined sound, which starts at 0 with the first piece. If the dialogue starts later in the render, add that offset.
- Always pass `--lav`, and pass as `--span` the `calibration_span` that `place` or `check --lav` reported. Then the lav check and the render check use one threshold (see below). Without `--span`, the whole lav is used and the threshold can differ; without `--lav`, the model's own threshold is used.
- Normalise the render with one fixed gain. In the test below, with a fixed gain, render scores stayed within 0.05 of the lav check's at all but one join (0.78 against 0.59). With a dynamic leveller (ffmpeg's single-pass `loudnorm`), clean joins rose by up to 0.44 (0.10 to 0.54). A join flagged only in the render may therefore come from the leveller or the encode rather than the cut: compare its score with the lav check's. The render path's false-alarm rate has not been measured on its own.
- Get the join times right to the sample. With times 20 or 40 ms out, scores moved by up to 0.35 in the test below: a clean join's score rose from 0.59 to 0.94, and one injected fault fell from 0.90 to 0.26.
- Any level works: each 5 s window is measured relative to its own speech level.

**What comes back** for each join:

| Field | Meaning |
|---|---|
| `score` | 0 to 1: how sure the model is that the join is faulty. |
| `flag` | True when `score` is above `threshold`. |
| `borderline` | True when `score` is within 0.03 of `threshold`. Such a flag can appear or vanish with any small change in the sound. Re-place the join, or treat it as flagged. |
| `likely` | The most likely kind of fault (always filled, even for clean joins). It is a hint only. |
| `level_step_db` | Speech level of the 2 s after the join minus the 2 s before. |
| `room_step_db` | Level of 20 to 60 ms after the cut minus 20 to 60 ms before. At a cut on room tone this compares the room tone each side; a large value at a flagged join means the cut is not on room tone. |
| `between` | The two pieces it joins (lav form only). |

Ordinary speech changes level by 3 to 5 dB from one sentence to the next. A `level_step_db` beyond about ±6 dB between two takes may be worth a gain match on one piece; that is your call, and the model does not flag it. The header gives:

- `model`, the model that scored;
- `false_alarm_rate`, the budget the flag is set for;
- `threshold`, and `threshold_from`, which says how the threshold was set;
- `calibration_span`, the stretch of the lav the threshold came from (pass it to `check --audio --span`);
- `off_model`, present only when the recording sounds unlike the model's training (see below);
- `flagged`, the joins to look at.

**The flag fits itself to each recording.** With the lav at hand, `check` (and `place`) splice about 200 clean joins from the recording's own pauses, in the stretch being edited, cut exactly as `place` cuts. They score them with the model and set the threshold so that `--false-alarm` of those joins are flagged. This needs no labels and no training. It takes 20 to 50 s the first time for a given stretch, and is then cached in `~/.cache/join-check/calibration/`. For `place` and `check --lav`, the stretch runs from 60 s before the first piece to 60 s after the last, widened to whole 30 s steps, so trimming a piece does not move the threshold. The output reports it as `calibration_span`.

The `--false-alarm` choices are 0.05, 0.1 (the default) and 0.2. On Josh's held-out joins the real rates were lower than the settings: 1.2%, 2.8% and 13.3%. Lower settings are not offered: they rest on a handful of the highest scores. A wrongly flagged join costs one re-placement and one re-check, never Josh's attention.

**What to do with a flagged join.** For `chop_end`, `clip_start`, `scrap` and `connected`, the fix is the same: move both edges at that join into the nearest pause on room tone, or choose another edge word. Look at `start_edge` and `end_edge` in `place`'s output to see why the edge is where it is. The named kind is right about 78% of the time on Josh's held-out joins, and was wrong for all four faults injected by hand, so do not choose a fix by the kind alone. The table gives what each kind means:

| `likely` | What it means | Usual fix |
|---|---|---|
| `chop_end` | The piece ends before its last word has finished | Move the end later, into the pause; or end on another word |
| `clip_start` | The piece starts after its first word has begun | Move the start earlier, into the pause before |
| `scrap` | A bit of a removed word is left at the cut | Move the cut back to the pause, before the removed word starts or after it ends |
| `click` | A butt join on a loud sample | Cut in the pause, or add a crossfade |
| `room` | The room sound changes at the cut | Use another take, lay the take's own room tone under it, or accept it |
| `connected` | A cut inside connected speech, with no pause | Cut at a pause: extend the piece to the nearest one, or choose another edge word |

## A real example: codex-switch, 168 to 259 s of the lav

Ten pieces keep "Here's how I managed to get fifty thousand bucks..." through "...you basically never have to know about it". They drop the ums, the aside "And cut this bit", and the pauses between restarts. The pieces are in `example/codex-switch-168-259.json`.

```sh
LAV="/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session/audio/dji_0597_aligned_to_nikon_48k_stereo.wav"
WORDS="/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/2026-10-12-camera-session/transcript/lav-verbatim-front.json"
pipeline/joins/joins place "$LAV" pipeline/joins/example/codex-switch-168-259.json --words "$WORDS" --out placed.json
```

Every edge but one is cut in a pause, on room tone. The exception, the start of piece 5, shows what happens when there is no pause. Its estimate ("you" at 208.02 s) follows an "um" with no pause between them:

```json
{"piece": 5, "start": 207.915, "end": 217.335,
 "start_edge": {"at": 207.915, "pause": null, "status": "no pause next to this word", "level_db_over_floor": 12.7,
   "nearest_pauses": {"before": [206.96, 207.4], "after": [213.21, 213.31],
                      "words_to_before": "[UM]", "words_to_after": "you can't use remote control ... desktop is on a different"}},
 "end_edge": {"at": 217.335, "status": "pause", "pause": [217.19, 217.48], "kept": 0.145, "on_room_tone": true,
              "level_db_over_floor": 3.4, "word_edge": 217.19, "estimate_off_by": 0.03},
 "words": "you can't use remote control ... month ago, two months ago.", "pause_after": 0.3}
```

The choices are to keep the "um" (`"start_at": 207.3`, inside the pause before it), to accept a cut 12.7 dB above the floor, or to start the piece elsewhere. The check's header, and the join into piece 5, which is the one join flagged:

```json
{"model": {"file": ".../pipeline/joins/model/joins.pkl", "sha256": "361f3c05041e", "trained": "2026-11-18T01:40"},
 "false_alarm_rate": 0.1, "threshold": 0.692,
 "threshold_from": "set on 200 clean joins spliced from this recording's own pauses, 90 to 330 s of .../dji_0597_aligned_to_nikon_48k_stereo.wav; the model's own threshold would be 0.678",
 "calibration_span": "90-330", "length": 72.23, "flagged": [4]}
{"join": 4, "at": 33.5, "score": 0.776, "flag": true, "borderline": false, "likely": "scrap", "likely_share": 0.49,
 "level_step_db": -0.8, "room_step_db": 13.8, "between": [4, 5]}
```

The join scores 0.78 against a threshold of 0.69, so it is flagged. Its `room_step_db` of 13.8 says the incoming side is not on room tone, which agrees with `start_edge`. The other eight joins score 0.04 to 0.51.

## How long it takes

Measured on the MacBook (M4 Pro, 24 GB) while other heavy jobs ran (load average 44 to 55). On an idle machine the same calls took about half as long.

| Call | Time |
|---|---|
| `place`, 10 pieces from the 23-minute lav, first time for that stretch (includes calibration) | 48 s |
| `place`, the same again (calibration cached) | 18 to 20 s |
| `check --audio`, 2 joins, no `--lav` | 14 s |
| `check --audio`, 9 joins, with `--lav` (cached) | 22 s |

Most of each call is reading the lav (1 to 3 s from the USB drive) and loading WavLM (a few seconds). Each join adds about 0.1 s.

## What it misses

Measured on 2,600 labelled joins made from the codex-switch stretch of his lav, which this model never trained on. The flag was set from that stretch's own pauses, at the default setting (0.1).

| | Result |
|---|---|
| Clean joins flagged | 2.8% (1.2% at 0.05, 13.3% at 0.2) |
| Faults caught | 93% |
| A word end cut 30 to 150 ms short | 99% caught |
| A word start clipped 20 to 120 ms | 99% caught |
| 40 to 150 ms of a removed word left in | 97% caught |
| A butt join on a loud sample | 99% caught |
| A cut inside connected speech | 100% caught |
| A room-sound jump of 6 dB or more | 74% caught (66% at 0.05, 89% at 0.2) |

What it cannot tell you:
- **Level steps between takes.** These are reported in dB (`level_step_db`), not flagged.
- **Intonation.** A rising, unfinished phrase joined to a sentence start.
- **Meaning.** A join that makes no sense.
- **Doubled breaths.**
- **Weak consonant tails.** These were the most-missed chops in earlier tests.
- **Music under the dialogue.** This is untested.

**Faults injected into a real edit and checked in a simulated render** (crossfaded joins, one fixed gain, AAC). The four faults were an end cut 80 ms short, a start clipped 30 ms, a start 50 ms into an "um", and 80 ms of a removed "um" left in. The lav check flagged all four. The render check flagged all four at exact join times and with times 20 ms late. With times 40 ms late it flagged three: the 80 ms chop fell to 0.26.

## A new microphone, room or voice

Usually nothing needs doing. The flag fits itself to each recording from that recording's own pauses (above). The audiobook-only model shows what this is worth, standing in for a voice, microphone and room the model has never heard. On Josh's codex-switch joins:

- **With its own thresholds,** it flagged 7.8% of clean joins at a 5% setting, and 21.9% at a 10% setting.
- **Fitted to the recording's pauses,** it flagged 5.9% and 9.7%, and still caught 93% of faults.

Ranking was never the problem (area under the curve 0.91 to 1.00 for every kind). Only the threshold was wrong, and the fitting fixes it.

**When a retrain is worth it.** Rarely. The output says when: an `off_model` field appears in `check`'s header when the recording's own clean joins score well above what the model expects. The rule is that the recording's 20% threshold is more than 0.15 above the model's. On Josh's voice, the audiobook-only model was 0.30 above (it would have warned), and the shipped model is 0.04 below. Even then, the only measured loss is in room jumps (area under the curve 0.91 against 0.95 after training on his voice); word-level faults were caught as well as ever. Retrain when `off_model` appears on every video from a new set-up, and the set-up gives at least 10 minutes of speech that will not be edited:

```sh
# 1. Make labelled joins from the new recording and its transcript (word times can be rough). Leave out any stretch
#    you will edit, so that checks on it stay honest. About 6 minutes for 10 minutes of speech.
pipeline/joins/joins examples --audio NEW.wav --words NEW-transcript.json --range 0-600 --out /tmp/new.npz
# 2. Train on them, with the existing example files if you still have them; thresholds come from --calibrate.
#    About 5 minutes on one file, 25 on the full set.
pipeline/joins/joins train /tmp/new.npz --calibrate /tmp/new.npz --out pipeline/joins/model/joins.pkl
```

`examples` force-aligns the transcript (torchaudio MMS, 1.2 GB, downloads once). It builds clean joins inside measured pauses, and faulty joins of each kind with known damage, then saves their measurements, not the audio (about 45 KB a join). The audiobook example file behind the shipped model was 500 MB and was not kept; `private/research/2026-11-17/join-check/` holds the scripts that rebuild it. After a retrain, write its date and the new sha256 at the top of this file, and run `example/smoke.sh`.

## Files

| File | What it holds |
|---|---|
| `joins.py` | The commands, placement and calibration |
| `sound.py` | Reading, levels, room floor, pauses, crossfades |
| `features.py` | What the model hears: about 20 signal measures and WavLM-Large features from 5 s around each join |
| `training.py` | Aligning, making labelled joins, fitting and predicting |
| `model/joins.pkl` | The trained classifier and its own thresholds (3.8 MB, scikit-learn 1.9.1; needs the pinned `requirements.txt`) |
| `example/` | The pieces used above, some edge cases, and `smoke.sh` |

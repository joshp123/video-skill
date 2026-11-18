<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: the transcriptions, what each is for and what each gets wrong, and how to run them. Updated by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: the verbatim transcript is now what the plan's words are found in and timed by; ingest.py runs it, and Resolve's transcript of the lav is no longer made. -->

# Transcription

Each transcription has its own job. The one made at ingest comes from the lav, never a camera's microphone, which hears the room and mishears names ("Claude Coe" for "Claude Code"), and it is on the front camera's clock.

| | For | How |
| --- | --- | --- |
| Verbatim, of the lav | Reading the story; finding every attempt at a line; the plan's `transcript`, in which `assemble.py` finds every piece and times every caption word | `scripts/verbatim_transcript.py`, CrisperWhisper, started by `pipeline/b/ingest.py` the moment the lav is on the front clock: 5 to 6 minutes for 23 minutes on the Mac's GPU |
| Resolve's, of a rendered cut | The words a viewer hears, for the gate's "caption word with no sound" check | `pipeline/b/word_times.py NAME --media FILE`, passed to `qc.py --heard-words`; not run since the rebuild |

## Why verbatim

Josh, when Resolve's transcript was proposed for the first read: "the transcript with umms and ahhs is also key right?" It is. Resolve's transcription drops what a cut needs to see. Every um becomes `(...)`, the same mark it uses for a pause; a repeated phrase collapses ("We saw a we saw a bear" came back as "We saw (...) a bear"); a cut-off word disappears ("the night, s- Bell" came back as "the night. Bell") (21 Oct). Resolve has no verbatim mode: `TranscribeAudio` takes only speaker detection and a nested-clip flag (API 2059). Its one advantage was speed (23 minutes in 87.5 s), which no longer pays for a second mechanism now that ingest starts the verbatim one within a minute or two of the files. When Resolve gains a verbatim mode, test it on a take with known ums and retire the script.

## Running the verbatim one

Ingest runs it for you. To run it by hand (a stretch again, another session), in this skill's `scripts/` devenv (Python 3.13 and uv), detached, with `TMPDIR` left alone (a temporary folder on a path with spaces breaks devenv's launcher):

```sh
devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
  --with numpy --with soundfile --with soxr \
  python -B -I verbatim_transcript.py LAV_16K.wav EDIT/transcript/NAME OFFSET_S [--device cpu]
```

The packages come through uv because the vendored CrisperWhisper decoder needs Transformers 4.46.3 and nixpkgs ships a later one. The input is the lav as 16 kHz mono (`tools/cameras.md`, "Ingest"). Give the offset only when the lav is not already padded onto the front camera's clock, never both. `--device cpu` runs at about real time where the GPU route fails.

The model is read from the Hugging Face cache that the devenv's `HF_HOME` names, with `HF_HUB_OFFLINE=1`, so a missing model is an error to report, not a silent download. On a new machine, point `HF_HOME` at a cache on a drive with room and run once without `HF_HUB_OFFLINE` to fetch it. The decoder's code is vendored beside the session's scripts; `CRISPERWHISPER_VENDOR` names it if it moves. The model's weights are under a non-commercial research licence.

## Read it whole before handing it over

- **Word times only locate a word.** A verbatim word can sit seconds from its neighbour across a long pause ("All" five seconds before "right"), and on codex-switch its times ran 0.15 to 0.5 s out in places. Cuts come from the lav's level (`joins place`); caption times come from forced alignment of the same words on the lav (`pipeline/b/words.py`, which `assemble.py` runs).
- **Loops.** The verbatim model can repeat a phrase dozens of times across a long pause and leave those words without times, and the script drops untimed words without saying so. Ingest reports the last word's time against the audio's length and every gap over 10 s; transcribe each gap's stretch again on its own to see what was said there.
- **Names** come out wrong ("Kodux" for Codex). Correct them in a working copy from the tool's README, help and output, word by word, keeping each time, and list every correction. The corrected copy is the one the plan's `transcript` points at, because `assemble.py` finds his words and times the captions in it. One recognised word standing for two ("MenuBuy" for "menu bar") becomes two words sharing its span.
- **One canonical transcript, never a merge.** Keep the raw output. Settle a disputed word by transcribing a few seconds around it again, and by what was on screen at that moment.

<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: the three transcriptions, what each is for and what each gets wrong, and how to run them. -->

# Transcription

Three transcriptions, each for its own job. Both made at ingest come from the lav, never a camera's microphone, which hears the room and mishears names ("Claude Coe" for "Claude Code"), and both are on the front camera's clock.

| | For | How |
| --- | --- | --- |
| Resolve's, of the lav | Reading the story within minutes of ingest, while the cameras may still be set up | `pipeline/ingest/transcribe.py PROJECT LAV OUT --offset S`, from the Edit page: 23 minutes in 87.5 s (22 Oct) |
| Verbatim, of the lav | Finding every attempt at a line, with its stumbles | `scripts/verbatim_transcript.py`, CrisperWhisper: 5 to 6 minutes for 23 minutes on the Mac's GPU |
| Of the placed timeline | Every on-screen time: caption words, highlights, typed words | `pipeline/b/word_times.py NAME` and `pipeline/b/align.py` (`roles/editor.md`, "Word times on the placed sound") |

## Why two transcripts of the same lav

Josh, when Resolve's transcript was proposed for the first read: "the transcript with umms and ahhs is also key right?" It is. Resolve's transcription drops what a cut needs to see. Every um becomes `(...)`, the same mark it uses for a pause; a repeated phrase collapses ("We saw a we saw a bear" came back as "We saw (...) a bear"); a cut-off word disappears ("the night, s- Bell" came back as "the night. Bell") (21 Oct). Resolve has no verbatim mode: `TranscribeAudio` takes only speaker detection and a nested-clip flag (API 2059). So read the story with Resolve's, and find takes in the verbatim one. When Resolve gains a verbatim mode, test it on a take with known ums and retire the script.

## Running the verbatim one

In this skill's `scripts/` devenv (Python 3.13 and uv), detached, with `TMPDIR` left alone (a temporary folder on a path with spaces breaks devenv's launcher):

```sh
devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
  --with numpy --with soundfile --with soxr \
  python -B -I verbatim_transcript.py LAV_16K.wav EDIT/transcript/NAME OFFSET_S [--device cpu]
```

The packages come through uv because the vendored CrisperWhisper decoder needs Transformers 4.46.3 and nixpkgs ships a later one. The input is the lav as 16 kHz mono (`tools/cameras.md`, "Ingest"). Give the offset only when the lav is not already padded onto the front camera's clock, never both. `--device cpu` runs at about real time where the GPU route fails.

The model is read from the Hugging Face cache that the devenv's `HF_HOME` names, with `HF_HUB_OFFLINE=1`, so a missing model is an error to report, not a silent download. On a new machine, point `HF_HOME` at a cache on a drive with room and run once without `HF_HUB_OFFLINE` to fetch it. The decoder's code is vendored beside the session's scripts; `CRISPERWHISPER_VENDOR` names it if it moves. The model's weights are under a non-commercial research licence.

## Read it whole before handing it over

- **Word times only locate a word.** A verbatim word can sit seconds from its neighbour across a long pause ("All" five seconds before "right"). Cuts come from the lav's level; on-screen times from the placed timeline.
- **Loops.** The verbatim model can repeat a phrase dozens of times across a long pause and leave those words without times, and the script drops untimed words without saying so. Check that the last time reaches the end of the audio and look at every long gap; Resolve's transcript shows what was said there.
- **Names** come out wrong from both ("Kodux" for Codex). Correct them in a working copy from the tool's README, help and output, word by word, keeping each time, and list every correction. One recognised word standing for two ("MenuBuy" for "menu bar") becomes two words sharing its span.
- **One canonical transcript, never a merge.** Keep both raw outputs. Settle a disputed word by transcribing a few seconds around it again, and by what was on screen at that moment.

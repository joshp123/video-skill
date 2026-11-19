<!-- Rewritten by AI on 2026.11.19 by model claude opus 5.5 from the 18 Nov file: the verbatim transcript, why it and not Resolve's, and what it gets wrong. -->

# Transcription

The transcript made at ingest is of the lav, never a camera's microphone, which hears the room and mishears names ("Claude Coe" for "Claude Code"), and it is on the front camera's clock. It is what the story is read from, every attempt at a line is found in, and the first cut finds his words in.

## Why verbatim

Resolve's transcription drops the ums, restarts and cut-off words a cut needs to see: every um becomes `(...)`, the same mark as a pause; a repeated phrase collapses ("We saw a we saw a bear" came back as "We saw (...) a bear"); a cut-off word disappears (21 Oct). Resolve has no verbatim mode. So the transcript is CrisperWhisper's, run by this skill's `scripts/verbatim_transcript.py`, which ingest starts as soon as the lav is on the front clock: 5 to 6 minutes for 23 minutes on the Mac's GPU. When Resolve gains a verbatim mode, test it on a take with known ums and retire the script.

To run it by hand (a stretch again, another session): in this skill's `scripts/` devenv, detached, with `TMPDIR` left alone (a temporary folder on a path with spaces breaks devenv's launcher):

```sh
devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
  --with numpy --with soundfile --with soxr \
  python -B -I verbatim_transcript.py LAV_16K.wav EDIT/transcript/NAME OFFSET_S [--device cpu]
```

The vendored CrisperWhisper decoder needs Transformers 4.46.3, and nixpkgs ships a later one. Give the offset only when the lav is not already padded onto the front clock, never both. `--device cpu` runs at about real time where the GPU route fails. The model is read from the Hugging Face cache the devenv's `HF_HOME` names, offline, so a missing model is an error to report, not a silent download. Its weights are under a non-commercial research licence.

## Read it whole before handing it over

- **Word times only locate a word.** A word can sit seconds from its neighbour across a long pause, and on codex-switch times ran 0.15 to 0.5 s out in places. Cuts come from the lav's level, and caption times from forced alignment of the same words on the placed sound.
- **Loops.** The model can repeat a phrase dozens of times across a long pause and leave those words without times, and the script drops untimed words without saying so. Check the last word's time against the audio's length and every gap over 10 s, and transcribe each gap's stretch again on its own.
- **Names** come out wrong ("Kodux" for Codex). Correct them in a working copy from the tool's README, help and output, word by word, keeping each time, and list every correction; the corrected copy is the one the cut uses. One recognised word standing for two ("MenuBuy" for "menu bar") becomes two words sharing its span.
- **One canonical transcript, never a merge.** Keep the raw output. Settle a disputed word by transcribing a few seconds round it again, and by what was on screen at that moment.

<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. -->

# Transcription

Three transcriptions, each for its own job. Both ingest transcripts come from the lav, never a camera's microphone (the Nikon's gave "Claude Coe" for "Claude Code"), on the front camera's clock.

| | For | How |
| --- | --- | --- |
| Resolve's, of the lav | Reading the story within minutes, while the cameras may still be up | `pipeline/ingest/transcribe.py PROJECT LAV OUT --offset S`, from the Edit page: 23 minutes in 87.5 s (22 Oct) |
| Verbatim, of the lav | Finding his lines and seeing every stumble | `scripts/verbatim_transcript.py`, CrisperWhisper: 5 to 6 minutes for 23 minutes on the GPU |
| Resolve's, of the placed timeline | Every on-screen time: caption words, highlights, typed words | `pipeline/b/word_times.py NAME`, on the sound the viewer hears |

Josh, when Resolve's transcript was proposed for the first read: "the transcript with umms and ahhs is also key right?" It is. Resolve drops exactly what a cut needs to see: every um becomes `(...)`, the mark it also uses for a pause; "We saw a we saw a bear" came back as "We saw (...) a bear"; "the night, s- Bell" as "the night. Bell" (21 Oct). Read with it; find takes in the verbatim one. Resolve has no verbatim mode (API 2059, 2098 take none); when it gains one, test it on a take with known ums and retire the script.

## Running the verbatim one

In its own devenv, from this skill's `scripts/`, detached, with `TMPDIR` left alone (a temporary folder on the SSD, whose path has spaces, breaks devenv's launcher):

```sh
devenv shell -- uv run -q --with torch --with 'transformers==4.46.3' --with accelerate \
  --with numpy --with soundfile --with soxr \
  python -B -I verbatim_transcript.py LAV_16K.wav EDIT/transcript/NAME OFFSET_S [--device cpu]
```

The vendored decoder needs Transformers 4.46.3, which is why the packages come through uv. The model is cached on the SSD at `/Volumes/Josh Extreme Pro USB4 4TB/OpenTrawl/system-cache-relief/huggingface`; with `HF_HUB_OFFLINE=1` a missing model is an error to report, not a download. The decoder's code lives in `Media/Edits/2026-10-12-camera-session/scripts/vendor/`; set `CRISPERWHISPER_VENDOR` if it moves. The models are under a non-commercial research licence.

## Read it whole before handing it over

- **Word times only locate a word.** In the 12 Oct verbatim transcript the "All" of "All right" sat almost five seconds before "right". Cuts come from the lav's level; on-screen times from the placed timeline.
- **Loops.** The verbatim model repeated "what else" dozens of times across a long pause on 12 Oct, leaving 112 words without times, and the script silently drops untimed words. Check the last time reaches the end of the audio and look at every long gap; Resolve's transcript shows what was said there.
- **Names** come out wrong from both ("Kodux" for Codex). Correct them in a working copy from the tool's README, help and output, word by word keeping each time, and list every correction. One recognised word standing for two ("MenuBuy" for "menu bar") becomes two words sharing its span.
- **One canonical transcript, never a merge.** Keep both raw outputs; settle a disputed word by transcribing a few seconds around it, and by what was on screen at that moment.

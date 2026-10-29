"""Find when each known word starts and ends in a sound file, by forced alignment of the words to the sound.

Written by AI on 2026-10-29 by Claude Opus 5.5.

The words are known (the captions, or a text file), so every one of them is placed, in order, on the sound:
- Times: the Montreal Forced Aligner (MFA 3.4.3, Kaldi HMM, its english_us_arpa acoustic model and dictionary, and its
  G2P model for words not in the dictionary, such as product names), in 10 ms steps.
- Confidence: wav2vec2 large (LV-60k, fine-tuned on LibriSpeech; torchaudio's WAV2VEC2_ASR_LARGE_LV60K_960H) aligns the
  same words by CTC, and a word's confidence is its mean probability for the word's letters. Low means the sound there
  does not match the word: not said, said differently, or spelt wrongly for saying. Then its times are not to be
  trusted either, because the aligner had to put the word somewhere.
- A cross-check: wav2vec2's first letter of a word lands 0 to 150 ms after MFA's start when both have found the word.
  Outside -50 to +250 ms the word is listed under "doubtful". MFA gives speech that is not in the words (a filler, or
  words a caption tidied away) to the next word, so that word starts early; wav2vec2 does not, and the check finds it
  (in the test, "you know" taken out of the words moved "completely" 0.8 s early, and only this check saw it).
  A doubtful word's start is to be judged on the spectrogram, not used.
On synthesised speech (two macOS synthesisers) with word times from the synthesiser, these starts were within 40 ms
on 89% of words in connected speech and within 77 ms on all; sentence starts after a pause were within 33 ms of the
known onset. wav2vec2's own times were later by 46 ms in the median, because CTC marks
each letter on one frame some way into its sound (private/align-test/, 2026-10-29). torchaudio's MMS_FA was tried
first: it gives spoken numbers no letters at all.

Times are on the sound file's own clock; a word's frame is round(seconds * fps), as captions.py makes it. The aligners
read letters and apostrophes, so each written word is spelt as said ("50,000" as "fifty thousand", "$4,008" as "four
thousand and eight dollars", "M4" as "m four", four-digit numbers from 1100 to 2099 as years); --spoken sets any other
reading. A written word spelt as several said words takes the first one's start and the last one's end, and the lowest
confidence of them. A word with no letters to align is listed under "unplaced", and the run then exits 1.

usage: align.py SOUND WORDS OUT.json [--fps 25] [--from SECONDS --to SECONDS] [--spoken 'TOKEN=said words' ...]
       SOUND: any file ffmpeg reads (wav, a render's .mov or .mp4); WORDS: an edit-list.json (its captions' words,
       with caption and word index) or a plain text file (words split on white space). --from and --to align a span.
run, from skill/scripts (its devenv.nix: Python 3.13, uv and micromamba; ffmpeg on the PATH):
       devenv shell -- uv run -q --with torch --with torchaudio --with soundfile --with num2words \\
         python -B -I ../../pipeline/b/align.py dialogue.wav ../../edit-list.json words.json
The first run installs MFA with micromamba into ~/.cache/video-skill/mfa-environment (1.4 GB) and its models into
~/.cache/video-skill/mfa-models (230 MB once unpacked); torchaudio downloads wav2vec2 once (1.26 GB, into
~/.cache/torch/hub/checkpoints/). After that, about 35 s for a sound of up to a few minutes, mostly MFA starting up; MFA
shares its unpacked models, so runs at the same time wait for each other.
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

import soundfile
import torch
import torchaudio
from num2words import num2words

MFA_ENVIRONMENT = Path.home() / ".cache/video-skill/mfa-environment"
MFA_MODELS = Path.home() / ".cache/video-skill/mfa-models"
MFA_PACKAGE = "montreal-forced-aligner=3.4.3"
MFA_ENGLISH = "english_us_arpa"
CONFIDENCE_MODEL = torchaudio.pipelines.WAV2VEC2_ASR_LARGE_LV60K_960H
ALIGNER_SAMPLE_RATE = 16000
WORD_SEPARATOR = "|"
SAMPLES_PER_LETTER_FRAME = 320
SAMPLES_UNDER_ONE_LETTER_FRAME = 400
WAV2VEC2_FIRST_LETTER_EARLIEST_BEFORE_START_SECONDS = 0.05
WAV2VEC2_FIRST_LETTER_LATEST_AFTER_START_SECONDS = 0.25
LETTER_FRAMES_PER_CHUNK = 1500
LETTER_FRAMES_OF_CONTEXT_EACH_SIDE_OF_CHUNK = 100
CURRENCY_NAMES = {"$": "dollar", "£": "pound", "€": "euro"}
SYMBOL_NAMES = {"&": "and", "+": "plus", "@": "at", "%": "percent", "=": "equals"}
WRITTEN_PIECE = re.compile(r"(?P<currency>[$£€])?(?P<number>\d[\d,]*(?:\.\d+)?)(?P<suffix>st|nd|rd|th|%)?"
                           r"|(?P<letters>[a-z']+)|(?P<symbol>[&+@%=])")
SAID_WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")


def number_as_said(number_text, suffix):
    """'50,000' -> 'fifty thousand'; '3rd' -> 'third'; '2026' -> 'twenty twenty-six'; '2.5' -> 'two point five'."""
    value = float(number_text.replace(",", "")) if "." in number_text else int(number_text.replace(",", ""))
    if suffix in ("st", "nd", "rd", "th"):
        return num2words(value, to="ordinal")
    if isinstance(value, int) and "," not in number_text and len(number_text) == 4 and 1100 <= value <= 2099:
        return num2words(value, to="year")
    return num2words(value)


def written_word_as_said(written_word, spoken_overrides):
    """The said words for one written word, in lower-case letters and apostrophes."""
    plain = unicodedata.normalize("NFKC", written_word).replace("’", "'").replace("‘", "'").lower()
    override_key = plain.strip(".,;:!?\"'()[]")
    if override_key in spoken_overrides:
        return spoken_overrides[override_key].split()
    said = []
    for piece in WRITTEN_PIECE.finditer(plain):
        if piece["number"]:
            words = number_as_said(piece["number"], piece["suffix"]).replace("-", " ").replace(",", "").split()
            if piece["currency"]:
                currency = CURRENCY_NAMES[piece["currency"]]
                words.append(currency if words == ["one"] else currency + "s")
            if piece["suffix"] == "%":
                words.append("percent")
            said += words
        elif piece["letters"]:
            said.append(piece["letters"].strip("'"))
        else:
            said.append(SYMBOL_NAMES[piece["symbol"]])
    accent_free = ["".join(c for c in unicodedata.normalize("NFKD", w) if not unicodedata.combining(c)) for w in said]
    return [w for w in accent_free if SAID_WORD.fullmatch(w)]


def read_written_words(words_path):
    """[(caption index or None, word index, written word)] in order, from an edit list's captions or a text file."""
    if words_path.suffix == ".json":
        captions = json.loads(words_path.read_text())["captions"]
        return [(caption_index, word_index, word["text"])
                for caption_index, caption in enumerate(captions)
                for word_index, word in enumerate(caption["words"])]
    return [(None, word_index, word) for word_index, word in enumerate(words_path.read_text().split())]


def write_sound_for_aligners(sound_path, span_start_seconds, span_end_seconds, wav_path):
    """The sound, or its span, as 16 kHz mono wav, the rate both aligners read; returns its samples."""
    span = ["-ss", str(span_start_seconds)] + ([] if span_end_seconds is None else ["-to", str(span_end_seconds)])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(sound_path), *span, "-vn", "-ac", "1",
                    "-ar", str(ALIGNER_SAMPLE_RATE), "-c:a", "pcm_s16le", str(wav_path)], check=True)
    samples, _ = soundfile.read(wav_path, dtype="float32")
    if len(samples) == 0:
        raise ValueError(f"no sound in {sound_path} from {span_start_seconds} s to {span_end_seconds} s")
    return torch.from_numpy(samples)


def run_mfa(*arguments):
    environment = {**os.environ, "MFA_ROOT_DIR": str(MFA_MODELS),
                   "PATH": f"{MFA_ENVIRONMENT / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    finished = subprocess.run([str(MFA_ENVIRONMENT / "bin/mfa"), *arguments], env=environment,
                              capture_output=True, text=True)
    if finished.returncode != 0:
        raise RuntimeError(f"mfa {' '.join(arguments)} failed:\n{finished.stdout[-3000:]}{finished.stderr[-3000:]}")


def install_mfa_once():
    if not (MFA_ENVIRONMENT / "bin/mfa").exists():
        print(f"installing {MFA_PACKAGE} into {MFA_ENVIRONMENT}, once (1.4 GB)", file=sys.stderr)
        subprocess.run(["micromamba", "create", "-y", "-q", "-r", str(MFA_ENVIRONMENT.parent / "micromamba"),
                        "-p", str(MFA_ENVIRONMENT), "-c", "conda-forge", MFA_PACKAGE, "python=3.11"], check=True)
    for kind in ("acoustic", "dictionary", "g2p"):
        if not list((MFA_MODELS / "pretrained_models" / kind).glob(f"{MFA_ENGLISH}*")):
            run_mfa("model", "download", kind, MFA_ENGLISH)


def mfa_word_times(wav_path, said_words, work_folder):
    """[(start, end)] per said word, from MFA; refuses a result that does not hold the same words in the same order."""
    corpus, output = work_folder / "corpus", work_folder / "aligned"
    corpus.mkdir()
    (corpus / "sound.wav").symlink_to(wav_path)
    (corpus / "sound.lab").write_text(" ".join(said_words) + "\n")
    run_mfa("align", "--clean", "--single_speaker", "--output_format", "json", "--g2p_model_path", MFA_ENGLISH,
            "--temporary_directory", str(work_folder / "mfa-work"), str(corpus), MFA_ENGLISH, MFA_ENGLISH, str(output))
    entries = json.loads((output / "sound.json").read_text())["tiers"]["words"]["entries"]
    words = [(start, end, label) for start, end, label in entries if label]
    labels = [label for _, _, label in words]
    if labels != said_words:
        first_difference = next(i for i in range(len(said_words) + 1)
                                if i == len(said_words) or i == len(labels) or labels[i] != said_words[i])
        raise RuntimeError(f"MFA returned {len(labels)} words for {len(said_words)}, differing from said word "
                           f"{first_difference}: {said_words[first_difference:first_difference + 3]} came back as "
                           f"{labels[first_difference:first_difference + 3]}")
    return [(start, end) for start, end, _ in words]


def letter_log_probabilities_in_chunks(model, waveform):
    """The model's letter log-probabilities for every 20 ms frame of the whole sound, computed in overlapping chunks,
    because wav2vec2's attention grows with the square of the length; each chunk keeps only its middle frames."""
    total_frames = (len(waveform) - SAMPLES_UNDER_ONE_LETTER_FRAME) // SAMPLES_PER_LETTER_FRAME + 1
    if total_frames < 1:
        raise ValueError("the sound is too short to align")
    kept_chunks = []
    for core_start in range(0, total_frames, LETTER_FRAMES_PER_CHUNK):
        core_end = min(core_start + LETTER_FRAMES_PER_CHUNK, total_frames)
        context_start = max(0, core_start - LETTER_FRAMES_OF_CONTEXT_EACH_SIDE_OF_CHUNK)
        context_end = min(total_frames, core_end + LETTER_FRAMES_OF_CONTEXT_EACH_SIDE_OF_CHUNK)
        chunk = waveform[context_start * SAMPLES_PER_LETTER_FRAME:
                         (context_end - 1) * SAMPLES_PER_LETTER_FRAME + SAMPLES_UNDER_ONE_LETTER_FRAME]
        with torch.inference_mode():
            letter_scores, _ = model(chunk.unsqueeze(0))
        kept_chunks.append(letter_scores[0, core_start - context_start:core_end - context_start].log_softmax(-1))
    return torch.cat(kept_chunks)


def wav2vec2_confidence_and_start_per_said_word(waveform, said_words):
    """Per said word, when the words are force-aligned to the sound by wav2vec2: its mean probability for the word's
    letters, and the time of the word's first letter."""
    letter_index = {label.lower(): index for index, label in enumerate(CONFIDENCE_MODEL.get_labels())}
    letter_log_probabilities = letter_log_probabilities_in_chunks(CONFIDENCE_MODEL.get_model(), waveform)
    targets = torch.tensor([[letter_index[c] for c in WORD_SEPARATOR.join(said_words)]], dtype=torch.int32)
    if targets.shape[1] > len(letter_log_probabilities):
        raise ValueError(f"{targets.shape[1]} letters cannot fit in {len(letter_log_probabilities)} frames of sound")
    alignment, scores = torchaudio.functional.forced_align(letter_log_probabilities.unsqueeze(0), targets, blank=0)
    letter_spans = [span for span in torchaudio.functional.merge_tokens(alignment[0], scores[0].exp())
                    if span.token != letter_index[WORD_SEPARATOR]]
    confidences_and_starts, next_letter = [], 0
    for word in said_words:
        spans = letter_spans[next_letter:next_letter + len(word)]
        next_letter += len(word)
        confidences_and_starts.append((sum(s.score * len(s) for s in spans) / sum(len(s) for s in spans),
                                       spans[0].start * SAMPLES_PER_LETTER_FRAME / ALIGNER_SAMPLE_RATE))
    return confidences_and_starts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sound", type=Path)
    parser.add_argument("words", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--fps", type=float, default=25)
    parser.add_argument("--from", dest="span_start", type=float, default=0.0)
    parser.add_argument("--to", dest="span_end", type=float)
    parser.add_argument("--spoken", action="append", default=[], metavar="TOKEN=said words")
    arguments = parser.parse_args()
    began = time.time()

    spoken_overrides = {}
    for override in arguments.spoken:
        token, separator, said = override.partition("=")
        if not separator or not said.strip():
            parser.error(f"--spoken {override!r}: write it as TOKEN=said words")
        spoken_overrides[token.strip().lower()] = said.strip().lower()

    written_words = read_written_words(arguments.words)
    placeable, unplaced = [], []
    for caption_index, word_index, written in written_words:
        said = written_word_as_said(written, spoken_overrides)
        where = {"caption": caption_index, "word": word_index, "text": written}
        if said:
            placeable.append((where, said))
        else:
            unplaced.append({**where, "why": "no letters to align once spelt as said"})
    said_words = [w for _, said in placeable for w in said]

    MFA_MODELS.mkdir(parents=True, exist_ok=True)
    with open(MFA_MODELS / "one-run-at-a-time.lock", "w") as lock, tempfile.TemporaryDirectory(prefix="align-") as work:
        fcntl.flock(lock, fcntl.LOCK_EX)
        install_mfa_once()
        work_folder = Path(work)
        wav_path = work_folder / "sound.wav"
        waveform = write_sound_for_aligners(arguments.sound, arguments.span_start, arguments.span_end, wav_path)
        said_word_times = mfa_word_times(wav_path, said_words, work_folder)
    said_word_confidences_and_starts = wav2vec2_confidence_and_start_per_said_word(waveform, said_words)

    rows, doubtful, next_said_word = [], [], 0
    for where, said in placeable:
        times = said_word_times[next_said_word:next_said_word + len(said)]
        confidences_and_starts = said_word_confidences_and_starts[next_said_word:next_said_word + len(said)]
        next_said_word += len(said)
        start, end = arguments.span_start + times[0][0], arguments.span_start + times[-1][1]
        wav2vec2_start = arguments.span_start + confidences_and_starts[0][1]
        rows.append({**where, "aligned": " ".join(said), "start": round(start, 3), "end": round(end, 3),
                     "start_frame": round(start * arguments.fps), "end_frame": round(end * arguments.fps),
                     "confidence": round(min(c for c, _ in confidences_and_starts), 3),
                     "wav2vec2_start": round(wav2vec2_start, 3)})
        wav2vec2_after_start = wav2vec2_start - start
        if not -WAV2VEC2_FIRST_LETTER_EARLIEST_BEFORE_START_SECONDS <= wav2vec2_after_start <= WAV2VEC2_FIRST_LETTER_LATEST_AFTER_START_SECONDS:
            doubtful.append({**where, "why": f"wav2vec2 hears its first letter {wav2vec2_after_start * 1000:+.0f} ms from MFA's "
                             f"start: speech not in the words beside it, or the word not said?"})

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps({
        "sound": str(arguments.sound), "words_from": str(arguments.words), "fps": arguments.fps,
        "span_seconds": [arguments.span_start, arguments.span_start + len(waveform) / ALIGNER_SAMPLE_RATE],
        "times_from": f"Montreal Forced Aligner ({MFA_PACKAGE}, {MFA_ENGLISH})",
        "confidence_from": "wav2vec2 large LV-60k LibriSpeech, CTC forced alignment",
        "words": rows, "doubtful": doubtful, "unplaced": unplaced}, indent=1, ensure_ascii=False) + "\n")
    lowest = min(rows, key=lambda row: row["confidence"], default=None)
    lowest_text = f", lowest confidence {lowest['confidence']:.2f} on {lowest['text']!r}" if lowest else ""
    print(f"{len(rows)} of {len(written_words)} words placed{lowest_text}, {len(doubtful)} doubtful, {len(unplaced)} unplaced, "
          f"{time.time() - began:.0f} s -> {arguments.out}")
    return 1 if unplaced else 0


if __name__ == "__main__":
    sys.exit(main())

"""Turn the edit list's captions into build/captions.json, the file pipeline/resolve/add_captions.py puts on the track.

Written by AI on 2026-10-25 by Claude Opus 5.5, for the B pipeline. Refuses a long word gap instead of moving the word
since 2026-10-26 (Claude Opus 5.5, stream B of the hill-climb): the move lit "left." 9 frames early in run 3.

The editor decides every caption: its words, its line break, its start and end, and each word's start. This script
does only what the Resolve template needs, and changes nothing else:

- every time goes to a whole frame (a half-frame word time made the pill stick, 22 Oct);
- each word stays inside its caption, starts at least a frame after the word before, and stays lit until the next
  word starts, the last until the caption ends (the template drops the pill when a word's time ends);
- no word starts more than 25 frames after the one before: the template starts a new page beyond that (tested
  22 Oct at 25 fps, every gap over 25 frames split, none at 25 or under). Such a caption is refused, with the word
  to split it before; a word is never lit before it is said.

It warns, and changes nothing, when a row with the pill's padding is wider than the look's safe line, measured with
the template's own face (Futura Bold) at the size in look.json's subtitles.resolveTemplate.

Not here, because each is the editor's decision on frames and sound, made in the edit list: snapping caption edges to
picture cuts, closing short blanks, a minimum duration, joining a one-word remainder, a hold after the last word,
the first word's start, and the last word's minimum light. pipeline/subtitles/build_captions.py did all of these.

captions.py EDIT_LIST [--output FILE]. EDIT_LIST is the edit list, read for fps, format, look and captions
({text with \\n between rows, start, end, words: [{text, start, end}]}, seconds on the timeline's clock).
"""
import argparse
import json
from pathlib import Path

LOOKS = Path(__file__).resolve().parents[2] / "looks"
TEMPLATE_FACE = "Futura Bold"
TEMPLATE_NEW_PAGE_AFTER_FRAMES = 25


def frames_for_template(caption, fps):
    """Whole frames for a caption and its words, as the template needs them; returns the frames and what moved."""
    start, end = round(caption["start"] * fps), round(caption["end"] * fps)
    if end <= start:
        raise ValueError(f"caption {caption['text']!r} has no length in whole frames")
    word_starts, moves = [], []
    for word in caption["words"]:
        wanted = round(word["start"] * fps)
        frame = min(max(wanted, start), end - 1)
        if word_starts:
            frame = max(frame, word_starts[-1] + 1)
            if frame > word_starts[-1] + TEMPLATE_NEW_PAGE_AFTER_FRAMES:
                raise ValueError(f"caption {caption['text']!r}: {word['text']!r} starts {frame - word_starts[-1]} frames after "
                                 f"the word before; the template starts a new page after {TEMPLATE_NEW_PAGE_AFTER_FRAMES}: "
                                 f"split the caption before {word['text']!r}")
        if frame >= end:
            raise ValueError(f"caption {caption['text']!r}: its words need more frames than it has")
        if frame != wanted:
            moves.append(f"{caption['text']!r}: {word['text']!r} starts at frame {frame}, asked {wanted}")
        word_starts.append(frame)
    word_ends = word_starts[1:] + [end]
    return start, end, list(zip(word_starts, word_ends)), moves


def row_width_px(row, metrics, size_px):
    units = sum(metrics["advances"].get(c, metrics["fontSize"]) for c in row)
    units += sum(metrics["kerning"].get(row[i - 1:i + 1], 0) for i in range(1, len(row)))
    return units * size_px / metrics["fontSize"]


def width_warnings(captions, look, frame_width, frame_height):
    template = look["subtitles"]["resolveTemplate"]
    face = look["fusion"]["faces"][TEMPLATE_FACE]
    size_px = template["textSize"] / face["textSizePer100Px"] * 100
    padding = look["subtitles"]["activeWord"]["padding"]
    padding = padding[1] if isinstance(padding, list) else padding
    safe = look["fusion"]["safeArea"]
    band_y = (1 - template["centreY"]) * frame_height  # Fusion measures Center Y up from the bottom
    limit = 2 * safe["buttonsLeft"] - frame_width if band_y >= safe["buttonsTop"] else frame_width
    warnings = []
    for caption in captions:
        for row in caption["text"].split("\n"):
            width = row_width_px(row, face["metrics"], size_px) + 2 * padding
            if width > limit:
                warnings.append(f"{row!r} is {width:.0f} px with the pill, wider than the {limit:g} px safe line")
    return warnings, size_px, limit


def build(edit_list_path, output_path):
    edit_list = json.loads(Path(edit_list_path).read_text())
    fps = edit_list["fps"]
    look = json.loads((LOOKS / edit_list["look"] / "look.json").read_text())
    captions, moves, overlaps, refusals = [], [], [], []
    for caption in edit_list["captions"]:
        try:
            start, end, word_frames, caption_moves = frames_for_template(caption, fps)
        except ValueError as refusal:
            refusals.append(str(refusal))
            continue
        moves += caption_moves
        if captions and start < round(captions[-1]["end"] * fps):
            overlaps.append(f"{caption['text']!r} starts before {captions[-1]['text']!r} ends")
        captions.append({"text": caption["text"], "rows": caption["text"].split("\n"),
                         "start": start / fps, "end": end / fps,
                         "words": [{"text": w["text"], "start": a / fps, "end": b / fps}
                                   for w, (a, b) in zip(caption["words"], word_frames)]})
    if refusals:
        raise ValueError("; ".join(refusals))
    warnings, size_px, limit = width_warnings(captions, look, edit_list["format"]["width"], edit_list["format"]["height"])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"fps": fps, "captions": captions}, indent=1, ensure_ascii=False) + "\n")
    return {"file": str(output), "captions": len(captions), "words": sum(len(c["words"]) for c in captions),
            "word_starts_moved": moves, "overlaps": overlaps, "width_warnings": warnings,
            "measured_as": f"{TEMPLATE_FACE} at {size_px:.1f} px, safe line {limit:g} px"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edit list captions to build/captions.json, whole frames only.")
    parser.add_argument("edit_list", type=Path)
    parser.add_argument("--output", type=Path, help="default: build/captions.json beside the edit list")
    arguments = parser.parse_args()
    output = arguments.output or arguments.edit_list.parent / "build" / "captions.json"
    print(json.dumps(build(arguments.edit_list, output), indent=1, ensure_ascii=False))

"""Write each line's chosen phrases as timed captions with per-word times: build/captions.json.

Written by AI on 2026-10-22 by Claude Fable 5.1, from build_srt.py (GPT-6.1 Sol, 21 Oct; originally Claude Opus 5.5).
Timing and width fixes written by AI on 2026-10-22 by GPT-6.1 Sol.
Reads each line's `subtitles` from edit/edit.json and the cut list's Resolve word times (aligned_*; the cut builder's
times when a word has none). A phrase holds for five frames after its last word, stops at the next phrase, and at a
picture cut after a sentence. Graphics with hides_subtitles stop captions. Each caption carries its displayed words
with start and end seconds, so Resolve can highlight the word being spoken; a displayed word gets the time of the
spoken word(s) under the same characters, so a spelling that shows one spoken word as two ("it's" as "this is")
splits that word's time between them. Edges snap within two frames of visible picture changes; one- and two-frame
blanks close. Captions last at least 0.7 s, joining a neighbour when needed, including a one-word remainder. Words
stay lit until the next starts, the last for at least three frames, with no start interval over one second (Resolve's
template otherwise starts another page). Width warnings include the look's pill padding. Times are whole frames,
written as seconds from the timeline's first frame.
"""
import argparse
import json
import math
from pathlib import Path

HOLD_AFTER_LAST_WORD_FRAMES = 5
SNAP_FRAMES = 2
MIN_LAST_WORD_FRAMES = 3
MIN_CAPTION_SECONDS = 0.7
# The current caption template is Futura Medium at 77.7 px; look.json does not yet store its face or size.
CAPTION_FACE = "Futura Medium"
CAPTION_FONT_SIZE = 77.7
DEFAULT_PILL_PADDING_PX = 36


def finish_timing(captions, cut, snap_edges=True):
    """The finishing editor's six snap_captions.py rules, on whole frames."""
    fps = cut["fps"]
    width, height = cut["format"]["width"], cut["format"]["height"]
    graphics = [g for g in cut["graphics"] if "in_resolved" in g and "out_resolved" in g]

    def covers_frame(graphic):
        region = cut.get("layouts", {}).get(graphic.get("layout"), {}).get("graphic")
        return bool(region) and region[0] <= 0 and region[1] <= 0 and region[2] >= width and region[3] >= height

    covered = [(g["in_resolved"]["frame"], g["out_resolved"]["frame"]) for g in graphics if covers_frame(g)]
    camera_cuts = {c["rec_in_frame"] for c in cut["clips"] if not any(a < c["rec_in_frame"] < b for a, b in covered)}
    changes = sorted(camera_cuts | {g[k]["frame"] for g in graphics for k in ("in_resolved", "out_resolved")})
    hidden = [(g["in_resolved"]["frame"], g["out_resolved"]["frame"]) for g in graphics if g.get("hides_subtitles")]
    frames = [[math.floor(c["start"] * fps + 1e-6), math.ceil(c["end"] * fps - 1e-6),
               [[round(w["start"] * fps), round(w["end"] * fps)] for w in c["words"]]] for c in captions]

    def in_hidden(frame):
        return any(a <= frame < b for a, b in hidden)

    for i, (start, end, words) in enumerate(frames if snap_edges else []):
        for change in changes:
            if (0 < abs(start - change) <= SNAP_FRAMES and not in_hidden(change)
                    and (i == 0 or change >= frames[i - 1][1] or abs(frames[i - 1][1] - change) <= SNAP_FRAMES)):
                frames[i][0] = start = change
                if i and (frames[i - 1][1] > change or 0 < change - frames[i - 1][1] <= SNAP_FRAMES):
                    frames[i - 1][1] = change
            if (0 < abs(end - change) <= SNAP_FRAMES and not (change > end and in_hidden(end))
                    and (i == len(frames) - 1 or change <= frames[i + 1][0] or abs(frames[i + 1][0] - change) <= SNAP_FRAMES)):
                frames[i][1] = end = change
                if i + 1 < len(frames) and (frames[i + 1][0] < change or 0 < frames[i + 1][0] - change <= SNAP_FRAMES):
                    frames[i + 1][0] = change
    for current, following in zip(frames, frames[1:]) if snap_edges else []:
        if 0 < following[0] - current[1] <= SNAP_FRAMES and not any(current[1] < b and following[0] > a for a, b in hidden):
            current[1] = following[0]
    for caption, (start, end, words) in zip(captions, frames):
        words[0][0] = start
        for word in words:
            word[0] = min(max(word[0], start), end)
            word[1] = min(max(word[1], start), end)
        if end - words[-1][0] < MIN_LAST_WORD_FRAMES:
            # After a merge the previous word's hold reaches this start; shorten that hold with the final light.
            floor = (words[-2][1] if snap_edges else words[-2][0] + 1) if len(words) > 1 else start
            words[-1][0] = min(words[-1][0], max(floor, end - MIN_LAST_WORD_FRAMES))
        for previous, current in zip(words, words[1:]):
            current[0] = min(current[0], previous[0] + round(fps))
        for previous, current in zip(words, words[1:]):
            previous[1] = current[0]
        words[-1][1] = end
        caption["start"], caption["end"] = round(start / fps, 3), round(end / fps, 3)
        for word, (a, b) in zip(caption["words"], words):
            word["start"], word["end"] = round(a / fps, 3), round(b / fps, 3)


def minimum_duration(captions, hidden, fps):
    """Hold short captions into a blank, or join their neighbour; never bridge a hidden graphic."""
    minimum_frames = math.ceil(MIN_CAPTION_SECONDS * fps)
    changes = []
    i = 0
    while i < len(captions):
        caption = captions[i]
        start, end = round(caption["start"] * fps), round(caption["end"] * fps)
        short = end - start < minimum_frames
        singleton = len(caption["words"]) == 1
        if not short and not singleton:
            i += 1
            continue
        limit = round(captions[i + 1]["start"] * fps) if i + 1 < len(captions) else end + minimum_frames
        limit = min([limit] + [a for a, b in hidden if a >= end])
        if short and not singleton and limit >= start + minimum_frames:
            caption["end"] = (start + minimum_frames) / fps
            changes.append(f"{caption['text']!r}: held {end - start} -> {minimum_frames} frames")
            i += 1
            continue
        neighbours = [j for j in (i - 1, i + 1) if 0 <= j < len(captions)
                      and not any(min(caption["start"], captions[j]["start"]) * fps < b
                                  and max(caption["end"], captions[j]["end"]) * fps > a for a, b in hidden)]
        neighbours.sort(key=lambda j: (captions[j]["line"] != caption["line"], j > i))
        if not neighbours:
            changes.append(f"WARNING {caption['text']!r}: cannot reach {minimum_frames} frames or join a neighbour across hidden graphics")
            i += 1
            continue
        j = neighbours[0]
        first, second = captions[min(i, j)], captions[max(i, j)]
        changes.append(f"{caption['text']!r}: joined {captions[j]['text']!r} ({'one-word remainder' if singleton else str(end-start) + '-frame caption'})")
        first["rows"][-1] += " " + second["rows"][0]
        first["rows"] += second["rows"][1:]
        if len(first["rows"]) > 2:
            first["rows"] = [first["rows"][0], " ".join(first["rows"][1:])]
        first["text"] = "\n".join(first["rows"])
        first["words"] += second["words"]
        first["end"] = second["end"]
        captions.pop(max(i, j))
        i = max(0, min(i, j))
    return changes


def width_warnings(captions, cut, look):
    """Measure the existing template using the look's glyph advances, kerning, safe area and pill padding."""
    subtitles = look.get("subtitles", {})
    padding = subtitles.get("activeWord", {}).get("padding", DEFAULT_PILL_PADDING_PX)
    padding = padding[1] if isinstance(padding, list) else padding
    metrics = look["fusion"]["faces"][CAPTION_FACE]["metrics"]
    width = cut["format"]["width"]
    safe = look["fusion"]["safeArea"]
    warnings = []
    for caption in captions:
        centre_y = cut["layouts"][caption["layout"]]["subtitles_centre_y"]
        limit = min(width, 2 * safe["buttonsLeft"] - width) if centre_y >= safe["buttonsTop"] else width
        for row in caption["rows"]:
            units = sum(metrics["advances"].get(c, metrics["fontSize"]) for c in row)
            units += sum(metrics["kerning"].get(row[i - 1:i + 1], 0) for i in range(1, len(row)))
            measured = units * CAPTION_FONT_SIZE / metrics["fontSize"] + 2 * padding
            if measured > limit:
                warnings.append(f"caption {caption['text']!r}, row {row!r}: {measured:.1f} px including {padding:g} px pill padding per side exceeds {limit:g} px safe width")
    return warnings, padding


def spoken_seconds(word, fps):
    if "aligned_start_s" in word and "aligned_end_s" in word:
        return word["aligned_start_s"], word["aligned_end_s"]
    if "aligned_start_frame" in word and "aligned_end_frame" in word:
        return word["aligned_start_frame"] / fps, word["aligned_end_frame"] / fps
    return word["t"], word["end"]


def char_spans(words):
    """Character range of each word in the words joined by single spaces."""
    spans, at = [], 0
    for w in words:
        spans.append((at, at + len(w)))
        at += len(w) + 1
    return spans


def displayed_word_times(rows, spoken, fps):
    """The displayed words of a caption (rows of text) with times from the spoken words under the same characters."""
    displayed = [w for row in rows for w in row.split()]
    assert " ".join(displayed) == " ".join(s["word"] for s in spoken)
    spoken_spans = char_spans([s["word"] for s in spoken])
    spoken_times = [spoken_seconds(s, fps) for s in spoken]

    def time_at(char):
        for (a, b), (start, end) in zip(spoken_spans, spoken_times):
            if a <= char <= b:
                return start + (end - start) * (char - a) / max(1, b - a)
        raise ValueError(char)

    out = []
    for text, (a, b) in zip(displayed, char_spans(displayed)):
        out.append({"text": text, "start": round(time_at(a), 3), "end": round(time_at(b), 3)})
    return out


def build(folder, cutlist="build/cutlist.json", output="build/captions.json"):
    out = folder / output
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite {out}; choose a new --output path")
    edit = json.loads((folder / "edit/edit.json").read_text())
    cut = json.loads((folder / cutlist).read_text())
    fps = cut["fps"]
    words_by_line = {}
    for word in cut["words"]:
        words_by_line.setdefault(word["line"], []).append(word)
    graphics = [g for g in cut["graphics"] if "in_resolved" in g and "out_resolved" in g]
    hidden = sorted((g["in_resolved"]["frame"], g["out_resolved"]["frame"]) for g in graphics if g.get("hides_subtitles"))
    picture_cuts = sorted({clip["rec_in_frame"] for clip in cut["clips"]})

    def layout_at(frame):
        for g in graphics:
            if g["in_resolved"]["frame"] <= frame < g["out_resolved"]["frame"]:
                return g["layout"]
        return "picture"

    def start_frame(word):
        return word.get("aligned_start_frame", word["start_frame"])

    def end_frame(word):
        return word.get("aligned_end_frame", word["end_frame"])

    phrases = []
    for line in edit["lines"]:
        queue = list(words_by_line.get(line["id"], []))
        for phrase in line.get("subtitles", []):
            rows = [phrase] if isinstance(phrase, str) else list(phrase)
            # Match by joined text, so a spelling that turns one spoken word into two ("it's" shown as "this is",
            # one cut word) still builds: take cut words until their text equals the phrase's.
            wanted = " ".join(" ".join(rows).split())
            taken, joined = [], ""
            while queue and joined != wanted and wanted.startswith(joined):
                taken.append(queue.pop(0)); joined = " ".join(w["word"] for w in taken)
            if joined != wanted:
                raise ValueError(f"{line['id']}: phrase {rows} does not match cut words {[w['word'] for w in taken]}")
            phrases.append({"line": line["id"], "rows": rows, "text": "\n".join(rows), "start_frame": start_frame(taken[0]),
                            "last_word_start_frame": start_frame(taken[-1]), "last_word_end_frame": end_frame(taken[-1]),
                            "words": displayed_word_times(rows, taken, fps)})
    for current, following in zip(phrases, phrases[1:] + [None]):
        end = current["last_word_end_frame"] + HOLD_AFTER_LAST_WORD_FRAMES
        if following:
            end = min(end, following["start_frame"])
        if current["text"][-1] in ".!?":
            end = min([end] + [cut_frame for cut_frame in picture_cuts if current["last_word_start_frame"] < cut_frame < end])
        # No caption while a graphic that shows his words is up: one that begins inside such a graphic starts when the
        # graphic leaves (the caption's word time is Resolve's, the graphic's edge the cut list's, so they can differ by
        # a few frames), and one that runs into it ends where the graphic comes in.
        start = current["start_frame"]
        for hide_in, hide_out in hidden:
            if hide_in <= start < hide_out:
                start = hide_out
            if start < hide_in < end:
                end = hide_in
        current["dropped"] = end <= start
        current["start"] = start / fps
        current["end"] = end / fps
        current["layout"] = layout_at(start)
        # Words stay inside their caption.
        for w in current["words"]:
            w["start"] = round(min(max(w["start"], current["start"]), current["end"]), 3)
            w["end"] = round(min(max(w["end"], current["start"]), current["end"]), 3)
    captions = [{k: p[k] for k in ("line", "rows", "text", "start", "end", "layout", "words")} for p in phrases if not p["dropped"]]
    finish_timing(captions, cut)
    changes = minimum_duration(captions, hidden, fps)
    finish_timing(captions, cut, snap_edges=False)
    look = json.loads((folder.parent / "looks" / edit["look"] / "look.json").read_text())
    warnings, padding = width_warnings(captions, cut, look)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as stream:
        stream.write(json.dumps({"fps": fps, "captions": captions}, indent=1, ensure_ascii=False) + "\n")
    layouts = sorted({c["layout"] for c in captions})
    return {"captions": len(captions), "dropped": sum(p["dropped"] for p in phrases), "words": sum(len(c["words"]) for c in captions),
            "layouts": {n: sum(c["layout"] == n for c in captions) for n in layouts}, "file": str(out),
            "timing_changes": changes, "width_warnings": warnings,
            "pill_padding_px": padding, "pill_padding_source": "look.json subtitles.activeWord.padding, else 36 px per side"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edit_folder", type=Path)
    parser.add_argument("cutlist", nargs="?", default="build/cutlist.json")
    parser.add_argument("--output", type=Path, default=Path("build/captions.json"))
    arguments = parser.parse_args()
    print(build(arguments.edit_folder, arguments.cutlist, arguments.output))

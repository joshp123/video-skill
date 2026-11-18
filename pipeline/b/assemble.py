"""Turn the model's plan for a whole video into the edit list place.py builds: one command, no judgement.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild.

assemble.py PLAN.json [--out EDIT_LIST]      (default: edit-list.json beside the plan; refuses to overwrite unless --force)

The model decides everything in the plan: which of his words are kept and in what order (each piece by its first and
last words), the pause it wants at each join, the camera and framing of every shot, the phrasing and line breaks of
every caption, the hold after a caption, and every title and panel, anchored to his words. This command only finds
those words in the transcript, has `pipeline/joins/joins place` put each sound edge inside the measured pause next to
them (and score every join), lays the pieces end to end on the timeline, and converts everything to timeline frames
and seconds. It reports, and does not fix: an edge with no pause next to it, a join the join check flags, a caption
whose words it could not match one for one, a word the aligner doubts, and a caption the look's template would split
onto a second page (a lit word starting more than 25 frames after the one before: split the caption there).

The plan (paths relative to the plan's folder; times in seconds on the front camera's clock):

{
  "resolve_project", "look", "fps", "format": {"width", "height"}, "multicam",
  "cameras": {NAME: {"file", "log", "group", "grade", "picture_offset_s", "reference"?, "framing"?}},
  "sound": {"lav", "room_tone_s", "room_tone_crossfade_ms", "room_tone_end_fade_ms"},
  "transcript": the word-timed transcript of the lav ({"words": [{"word", "start", "end"}]}),
  "crossfade_ms": the crossfade at every join (joins place; 0 for butt joins), "fade_ms": [in, out] at the film's ends,
  "lead_in_s": film before the first piece's sound, "tail_s": film after the last piece's sound,
  "caption_hold_s": how long a caption stays after its last word ends, unless the next caption starts sooner,
  "pieces": [{
      "from": "first words", "to": "last words", "near_s": where the first words are said,
      "to_near_s"?: where the last words are said, when they occur more than once in the piece (default: the first
                 occurrence after "from"),
      "pause_after_s"?: the pause wanted at the join after this piece (joins place splits it between both sides),
      "start_s"?, "end_s"?: an edge set by hand on the lav's clock, given to joins place as start_at or end_at,
      "shots"?: [{"camera", "framing"?, "at"?: a word of the piece (default its start), "n"?, "offset_frames"?}],
                 a piece without shots continues the camera and framing before it; offset_frames on a shot at the
                 piece's start moves that picture cut off the sound cut (negative: the picture changes first);
  }],
  "captions": ["text as shown, / between its two rows", {"text": ..., "hold_s"?: ..., "start_s"?: ...,
              "word_starts_s"?: {"word's index in the caption, from 0": its start on the timeline}}, ...]: in order,
              together showing the kept words of every piece; a shown word is timed by the spoken word it matches,
              and shown words that match none ("50,000" for "fifty thousand") share the time of the spoken words
              between their neighbours; start_s and hold_s are on the timeline's clock,
  "titles": [{"template", "inputs", "at": ANCHOR, "frames" or "until": ANCHOR}],
  "panels": [{"file", "source_in", "track", "framing"?, "group"?, "at": ANCHOR, "frames" or "until": ANCHOR}]
}
ANCHOR: {"piece": index from 0, "word": "words", "n"?: which occurrence in the piece, from 0, "edge": "start" or "end",
"offset_frames"?}, or {"frame": N}, or {"end": true} for the film's last frame.
"""
import argparse
import difflib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOINS = HERE.parent / "joins" / "joins"
TORCH_PYTHON = HERE.parent / "joins" / ".devenv" / "state" / "venv" / "bin" / "python"  # torch, torchaudio, the aligners offline
MIN_GAP_S = 0.03  # the shortest gap between two aligned words a cut is moved into
WINDOW_S = 2.0  # each side of an edge with no pause: the words either side of it, aligned in context, for the report


def aligned_words(lav, transcript, pieces, work, exact=False, around=()):
    """words.py: {(transcript start, word): aligned row} and the doubtful rows. EXACT: on each piece's exact audio with
    exactly its words (fillers included), which is what the viewer hears, so a word on the far side of a cut cannot pull
    a kept word off. AROUND: on a window round each of those times, with every transcript word in it, for the report."""
    if exact:
        windows = [{"window": [p["start"], p["end"]], "words": p["heard"]} for p in pieces]
    else:
        windows = [[max(0.0, at - WINDOW_S), at + WINDOW_S] for at in around]
    (work / "windows.json").write_text(json.dumps(windows))
    env = {**os.environ, "TORCH_HOME": str(Path.home() / ".cache/join-check/torch"), "HF_HUB_OFFLINE": "1"}
    out = work / ("aligned-words.json" if exact else "aligned-words-around-edges.json")
    done = subprocess.run([str(TORCH_PYTHON), str(HERE / "words.py"), str(lav), str(transcript), str(work / "windows.json"),
                           str(out)], capture_output=True, text=True, env=env)
    if done.returncode != 0:
        raise RuntimeError(f"words.py failed: {done.stderr.strip()[-2000:]}")
    found, doubtful = {}, {}
    for window in json.loads(out.read_text()):
        found.update({(w["transcript_start"], w["word"]): w for w in window["words"]})
        doubtful.update({(w["transcript_start"], w["word"]): w for w in window["doubtful"]})
    return found, doubtful


def norm(token):
    return re.sub(r"[^a-z0-9']", "", token.lower().replace("’", "'"))


def spoken(words):
    """The transcript's words with their index, without bracketed non-words ([UM], [throatclearing])."""
    return [(i, w) for i, w in enumerate(words) if not w["word"].startswith("[") and norm(w["word"])]


def find_phrase(tokens, phrase, near, after_index=-1, within=120.0):
    """Index into TOKENS of the start of PHRASE nearest NEAR seconds (after AFTER_INDEX), or raise."""
    want = [norm(t) for t in phrase.split() if norm(t)]
    hits = [k for k in range(len(tokens) - len(want) + 1) if k > after_index
            and [norm(tokens[k + j][1]["word"]) for j in range(len(want))] == want
            and abs(tokens[k][1]["start"] - near) <= within]
    if not hits:
        raise ValueError(f"{phrase!r} is not in the transcript within {within:g} s of {near:g} s")
    return min(hits, key=lambda k: abs(tokens[k][1]["start"] - near)), len(want)


def time_shown_words(shown, said):
    """Each shown word's (start, end) from the said words [(text, start, end)]: equal words share times; a run of shown
    words matching nothing takes the time of the unmatched said words between the same neighbours, split evenly."""
    a, b = [norm(w) for w in shown], [norm(w[0]) for w in said]
    times = [None] * len(shown)
    unmatched = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (said[j1 + k][1], said[j1 + k][2])
        elif i2 > i1:
            if j2 > j1:
                begin, end = said[j1][1], said[j2 - 1][2]
            else:
                begin = end = said[j1 - 1][2] if j1 else said[0][1]
            step = (end - begin) / (i2 - i1)
            for k in range(i2 - i1):
                times[i1 + k] = (begin + k * step, begin + (k + 1) * step)
            unmatched.append(f"shown {' '.join(shown[i1:i2])!r} for said {' '.join(w[0] for w in said[j1:j2])!r}")
        elif j2 > j1:
            unmatched.append(f"said {' '.join(w[0] for w in said[j1:j2])!r} is in no caption")
    return times, unmatched


def joins_place(plan, folder, pieces, lav, transcript, work):
    """Exact edges from `joins place`: each piece's {start, end} on the lav, and the join check. A piece's start_s and
    end_s go in as start_at and end_at, cuts used as given."""
    wanted = []
    for k, p in enumerate(pieces):
        row = {"start": p["approx_start"], "end": p["approx_end"]}
        if k and pieces[k - 1].get("pause_after_s") is not None:
            row["pause_before"] = pieces[k - 1]["pause_after_s"]
        if p.get("pause_after_s") is not None:
            row["pause_after"] = p["pause_after_s"]
        if "start_s" in p:
            row = {**{k: v for k, v in row.items() if k != "start"}, "start_at": p["start_s"]}
        if "end_s" in p:
            row = {**{k: v for k, v in row.items() if k != "end"}, "end_at": p["end_s"]}
        wanted.append(row)
    work.mkdir(parents=True, exist_ok=True)
    (work / "pieces.json").write_text(json.dumps(wanted, indent=1))
    out = work / "joins-place.json"
    done = subprocess.run([str(JOINS), "place", str(lav), str(work / "pieces.json"), "--words", str(transcript),
                           "--crossfade", str(plan.get("crossfade_ms", 40) / 1000), "--out", str(out)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"joins place failed: {done.stderr.strip()[-2000:]}")
    return json.loads(out.read_text())


def resolve_anchor(anchor, pieces, fps, duration_frames=None):
    if anchor.get("end"):
        return duration_frames
    if "frame" in anchor:
        return int(anchor["frame"])
    piece = pieces[anchor["piece"]]
    tokens = piece["tokens"]
    want = [norm(t) for t in anchor["word"].split()]
    hits = [k for k in range(len(tokens) - len(want) + 1) if [norm(tokens[k + j]["word"]) for j in range(len(want))] == want]
    if not hits:
        raise ValueError(f"{anchor['word']!r} is not in piece {anchor['piece']}")
    k = hits[anchor.get("n", 0)]
    t = tokens[k]["start"] if anchor.get("edge", "start") == "start" else tokens[k + len(want) - 1]["end"]
    return round((piece["record_s"] + t - piece["start"]) * fps) + anchor.get("offset_frames", 0)


def assemble(plan_path):
    plan = json.loads(plan_path.read_text())
    folder = plan_path.parent
    fps = float(plan["fps"])
    transcript = (folder / plan["transcript"]).resolve()
    lav = (folder / plan["sound"]["lav"]).resolve()
    everything = json.loads(transcript.read_text())["words"]
    tokens = spoken(everything)
    pieces, report = [], {"pieces": [], "edges": [], "captions": [], "joins": None}
    for k, p in enumerate(plan["pieces"]):
        first, _ = find_phrase(tokens, p["from"], p["near_s"])
        last, size = find_phrase(tokens, p["to"], p.get("to_near_s", tokens[first][1]["start"]), after_index=first - 1)
        kept = [w for _, w in tokens[first:last + size]]
        heard = everything[tokens[first][0]:tokens[last + size - 1][0] + 1]
        pieces.append(dict(p, approx_start=kept[0]["start"], approx_end=kept[-1]["end"], tokens=kept, heard=heard))
    work = folder / "build" / "assemble"
    work.mkdir(parents=True, exist_ok=True)
    placed = joins_place(plan, folder, pieces, lav, transcript, work)
    report["joins"] = placed["check"]
    report["edges"] = [{"piece": exact["piece"], "side": side, **exact[side]} for exact in placed["pieces"]
                       for side in ("start_edge", "end_edge") if exact[side].get("status") not in ("pause", "given")]
    if report["edges"]:
        context, _ = aligned_words(lav, transcript, pieces, work, around=[e["at"] for e in report["edges"]])
        ordered = sorted(context.values(), key=lambda w: w["start"])
        for e in report["edges"]:
            e["aligned_words_around"] = [(w["word"], w["start"], w["end"]) for w in ordered if abs(w["start"] - e["at"]) < 1.0]
            piece = pieces[e["piece"] - 1]
            edge_word = piece["tokens"][-1 if e["side"] == "end_edge" else 0]
            k = next((i for i, w in enumerate(ordered) if (w["transcript_start"], w["word"]) == (edge_word["start"], edge_word["word"])), None)
            j = None if k is None else (k + 1 if e["side"] == "end_edge" else k - 1)
            key = "end_s" if e["side"] == "end_edge" else "start_s"
            if j is None or not 0 <= j < len(ordered) or key in piece:
                continue
            gap = (ordered[k]["end"], ordered[j]["start"]) if e["side"] == "end_edge" else (ordered[j]["end"], ordered[k]["start"])
            if gap[1] - gap[0] >= MIN_GAP_S and not gap[0] <= e["at"] <= gap[1]:
                piece[key] = round((gap[0] + gap[1]) / 2, 4)
                e["moved_to"] = piece[key]
                e["why_moved"] = f"the cut was inside a word; moved to the middle of the {1000 * (gap[1] - gap[0]):.0f} ms between the aligned words"
    if any("moved_to" in e for e in report["edges"]):  # place again, the moved cuts given as start_at/end_at
        placed = joins_place(plan, folder, pieces, lav, transcript, work)
        report["joins"] = placed["check"]
    for p, exact in zip(pieces, placed["pieces"]):
        p.update(start=exact["start"], end=exact["end"])
    found, doubtful = aligned_words(lav, transcript, pieces, work, exact=True)
    report["doubtful_words"] = []
    for k, p in enumerate(pieces):
        keys = [(w["start"], w["word"]) for w in p["tokens"]]
        report["doubtful_words"] += [{"piece": k, **doubtful[key]} for key in keys if key in doubtful]
        missing = [w["word"] for w, key in zip(p["tokens"], keys) if key not in found]
        if missing:
            report["doubtful_words"].append({"piece": k, "not_aligned": missing})
        p["tokens"] = [dict(w, transcript_start=w["start"], start=found[key]["start"], end=found[key]["end"]) if key in found else w
                       for w, key in zip(p["tokens"], keys)]
    record = plan.get("lead_in_s", 0.0)
    for p, exact in zip(pieces, placed["pieces"]):
        p.update(record_s=record)
        record += exact["end"] - exact["start"]
        report["pieces"].append({"piece": exact["piece"], "record_s": round(p["record_s"], 4), "words": exact.get("words")})
    duration_frames = math.ceil((record + plan.get("tail_s", 0.0)) * fps)
    crossfade_ms = plan.get("crossfade_ms", 40)
    fade_in, fade_out = plan.get("fade_ms", [10, 20])
    audio = []
    for k, p in enumerate(pieces):
        row = {"file": plan["sound"]["lav"], "source_in_s": p["start"], "source_out_s": p["end"], "record_s": round(p["record_s"], 6),
               "fade_in_ms": fade_in if k == 0 else 0, "fade_out_ms": fade_out if k == len(pieces) - 1 else 0}
        if k < len(pieces) - 1:
            if crossfade_ms:
                row["crossfade_ms"] = crossfade_ms
        audio.append(row)
    # pictures: every piece boundary is a picture cut (the source jumps); a shot can also start on a word inside a piece,
    # and a shot at a piece's start can move its cut a few frames either way (a split edit: picture before or after sound)
    cameras = plan["cameras"]
    piece_cuts = []
    for k, p in enumerate(pieces):
        piece_first = round(p["record_s"] * fps)
        cuts = {}
        for shot in p.get("shots", []):
            at = piece_first if "at" not in shot else resolve_anchor({"piece": k, "word": shot["at"], "n": shot.get("n", 0)}, pieces, fps)
            at += shot.get("offset_frames", 0)
            cuts[at] = (shot["camera"], shot.get("framing", cameras[shot["camera"]].get("framing", {})))
        if not any("at" not in shot for shot in p.get("shots", [])):
            cuts[piece_first] = None  # continues the camera before it, from this piece's source
        piece_cuts.append(sorted(cuts.items()))
    segments, look = [], None
    for k, p in enumerate(pieces):
        last = piece_cuts[k + 1][0][0] if k + 1 < len(pieces) else duration_frames
        for (first, shot), nxt in zip(piece_cuts[k], [c[0] for c in piece_cuts[k][1:]] + [last]):
            look = shot or look
            if look is None or nxt <= first:
                continue
            cam, fr = look
            front_s = p["start"] + first / fps - p["record_s"]
            source_in = round((front_s - cameras[cam].get("picture_offset_s", 0.0)) * fps)
            segments.append({"camera": cam, "source_in": source_in, "record": first, "frames": nxt - first, "framing": fr})
    report["shortest_segments"] = sorted(({"record": s["record"], "frames": s["frames"]} for s in segments), key=lambda s: s["frames"])[:3]
    said = [(w["word"], p["record_s"] + w["start"] - p["start"], p["record_s"] + w["end"] - p["start"])
            for p in pieces for w in p["tokens"]]
    entries = [c if isinstance(c, dict) else {"text": c} for c in plan.get("captions", [])]
    shown = [w for c in entries for w in c["text"].replace("/", " ").split()]
    times, unmatched = time_shown_words(shown, said)
    hold = plan.get("caption_hold_s", 0.3)
    captions, cursor = [], 0
    for c in entries:
        count = len(c["text"].replace("/", " ").split())
        words = [{"text": w, "start": round(t[0], 4), "end": round(t[1], 4)}
                 for w, t in zip(c["text"].replace("/", " ").split(), times[cursor:cursor + count])]
        cursor += count
        for index, moved in sorted((int(i), t) for i, t in c.get("word_starts_s", {}).items()):
            words[index]["start"] = round(moved, 4)
            if index:
                words[index - 1]["end"] = round(moved, 4)
        text = "\n".join(row.strip() for row in c["text"].split("/"))
        captions.append({"text": text, "start": c.get("start_s", words[0]["start"]), "end": words[-1]["end"] + c.get("hold_s", hold),
                         "words": words})
    for a, b in zip(captions, captions[1:]):
        if a["end"] > b["start"]:
            a["end"] = b["start"]
    for c in captions:
        c["start"], c["end"] = round(c["start"], 4), round(c["end"], 4)
    report["captions"] = unmatched
    import captions as template  # the look's caption template's own limits, checked here so place.py does not refuse later
    report["caption_refusals"] = []
    for c in captions:
        try:
            template.frames_for_template(c, fps)
        except ValueError as refusal:
            report["caption_refusals"].append(str(refusal))
    titles = []
    for t in plan.get("titles", []):
        first = resolve_anchor(t["at"], pieces, fps, duration_frames)
        frames = t["frames"] if "frames" in t else resolve_anchor(t["until"], pieces, fps, duration_frames) - first
        titles.append({"template": t["template"], "inputs": t["inputs"], "record": first, "frames": frames})
    panels = []
    for row in plan.get("panels", []):
        first = resolve_anchor(row["at"], pieces, fps, duration_frames)
        frames = row["frames"] if "frames" in row else resolve_anchor(row["until"], pieces, fps, duration_frames) - first
        panels.append({"file": row["file"], "source_in": row["source_in"], "source_out": row["source_in"] + frames,
                       "track": row["track"], "record": first, "framing": row.get("framing", {}),
                       **({"group": row["group"]} if "group" in row else {})})
    overlaps = []
    for kind, rows in (("title", [dict(r, track=4) for r in titles]), ("panel", panels)):
        rows = sorted(rows, key=lambda r: (r["track"], r["record"]))
        for a, b in zip(rows, rows[1:]):
            length = a.get("frames", a.get("source_out", 0) - a.get("source_in", 0))
            if a["track"] == b["track"] and a["record"] + length > b["record"]:
                overlaps.append(f"{kind}s on V{a['track']}: frames {a['record']} to {a['record'] + length} overlap the one at {b['record']}")
    if overlaps:
        raise ValueError("; ".join(overlaps) + " (anchor the first one's end to the next one's start with \"until\")")
    edit_list = {key: plan[key] for key in ("resolve_project", "fps", "format", "look", "multicam", "cameras", "sound")}
    edit_list.update(duration_frames=duration_frames, segments=segments, panels=panels, titles=titles, audio=audio,
                     captions=captions)
    report["joins_flagged"] = report["joins"].get("flagged")
    report["calibration_span"] = report["joins"].get("calibration_span")  # joins check --audio needs it with --lav
    return edit_list, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    out = args.out or args.plan.parent / "edit-list.json"
    try:
        if out.exists() and not args.force:
            raise FileExistsError(f"{out} exists; pass --force to replace it")
        edit_list, report = assemble(args.plan.resolve())
        out.write_text(json.dumps(edit_list, indent=1, ensure_ascii=False) + "\n")
        report["edit_list"] = str(out)
        report["duration_s"] = round(edit_list["duration_frames"] / float(edit_list["fps"]), 3)
        print(json.dumps(report, indent=1, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}))
        sys.exit(1)

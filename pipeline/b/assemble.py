"""Turn the model's plan for a whole video into the edit list build.py lays: one command, no judgement.

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
  "resolve_project", "look", "fps", "format": {"width", "height"},
  "cameras": {NAME: {"file", "log", "group", "grade", "picture_offset_s", "reference"?, "framing"?, "blur"?}}
             ("blur": true gives that camera the look's background blur at every finish: the wide camera),
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
      "shots"?: [{"camera", "framing"?, "at"?: a word of the piece (default its start), "n"?, "offset_frames"?, "off"?}],
                 a piece without shots continues the camera and framing before it; offset_frames moves a shot's
                 picture cut that many frames (negative: earlier), on any shot: at a piece's start it splits the
                 picture cut from the sound cut;
  }],
  "captions": ["text as shown, / between its two rows", {"text": ..., "hold_s"?: ..., "start_s"?: ...,
              "word_starts_s"?: {"word's index in the caption, from 0": its start on the lav's clock}}, ...]: in order,
              together showing the kept words of every piece; a shown word is timed by the spoken word it matches,
              and shown words that match none ("50,000" for "fifty thousand") share the time of the spoken words
              between their neighbours; start_s and hold_s are on the timeline's clock,
  "titles": [{"template", "inputs", "at": ANCHOR, "frames" or "until": ANCHOR}],
  "panels": [{"file", "source_in", "track", "framing"?, "group"?, "at": ANCHOR, "frames" or "until": ANCHOR}]
}
ANCHOR: {"piece": index from 0, "word": "words", "n"?: which occurrence in the piece, from 0, "edge": "start", "end" or "cut",
"offset_frames"?}, or {"frame": N}, or {"end": true} for the film's last frame. "cut" is the camera cut nearest the word's
start when one is within 6 frames (a shot starts a few frames before its first word), else the word's start.
A shot with "off": true lays its camera disabled, so the background and panels show alone (the tool with no camera);
it continues to the next shot, like any shot.
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
STRAY_HEARD_SCORE = 0.5  # words.py's confidence for a word it hears where the transcript puts it
MIN_GAP_S = 0.03  # the shortest gap between two aligned words a cut is moved into
WINDOW_S = 2.0  # each side of an edge with no pause: the words either side of it, aligned in context, for the report


def aligned_words(lav, transcript, pieces, work, exact=False, around=()):
    """words.py: {(transcript start, word): aligned row} and the doubtful rows; with EXACT, one such pair per piece, in the
    pieces' order, because a word the transcript puts near a cut sits in both pieces' windows and is heard in at most one
    (run 7: "log" scored 0.003 in the outgoing piece and 0.991 in the incoming one). EXACT: on each piece's exact audio with
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
    keyed = [({(w["transcript_start"], w["word"]): w for w in window["words"]},
              {(w["transcript_start"], w["word"]): w for w in window["doubtful"]}) for window in json.loads(out.read_text())]
    if exact:
        return [f for f, _ in keyed], [d for _, d in keyed]
    found, doubtful = {}, {}
    for f, d in keyed:
        found.update(f)
        doubtful.update(d)
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


def resolve_anchor(anchor, pieces, fps, duration_frames=None, cuts=()):
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
    t = tokens[k]["end"] if anchor.get("edge", "start") == "end" else tokens[k]["start"]
    frame = round((piece["record_s"] + t - piece["start"]) * fps)
    if anchor.get("edge") == "cut":
        near = min(cuts, key=lambda c: abs(c - frame), default=None)
        frame = near if near is not None and abs(near - frame) <= NEAR_CUT_FRAMES else frame
    return frame + anchor.get("offset_frames", 0)


def from_zero(check):
    """The joins tool counts joins and pieces from 1; the plan and the edit list's audio rows count from 0.
    Join k (from 0) lies between pieces k and k + 1."""
    check = json.loads(json.dumps(check))
    for j in check.get("joins", []):
        j["join"] -= 1
        if "between" in j:
            j["between"] = [b - 1 for b in j["between"]]
    check["needs_listen"] = [f - 1 for f in check.get("needs_listen", [])]
    return check


def check_plan(plan, folder, pieces):
    """Every word anchor and every file the plan names, checked before the audio models run (about 30 s), so a bad anchor
    or a missing file is learnt in a second (run 7's pass 2). All problems are listed at once."""
    problems = []
    for what, path in ([(f"camera {k}", c["file"]) for k, c in plan["cameras"].items()]
                       + [("sound.lav", plan["sound"]["lav"]), ("transcript", plan["transcript"])]):
        if not (folder / path).exists():
            problems.append(f"{what}: no file {path}")

    def anchor_ok(anchor, where):
        if not isinstance(anchor, dict) or anchor.get("end") or "frame" in anchor:
            return
        k = anchor.get("piece")
        if not isinstance(k, int) or not 0 <= k < len(pieces):
            problems.append(f"{where}: piece {k} does not exist (pieces are numbered from 0 to {len(pieces) - 1})")
            return
        tokens, want = pieces[k]["tokens"], [norm(t) for t in str(anchor.get("word", "")).split()]
        hits = [i for i in range(len(tokens) - len(want) + 1) if want and [norm(tokens[i + j]["word"]) for j in range(len(want))] == want]
        if len(hits) <= anchor.get("n", 0):
            said = " ".join(w["word"] for w in tokens)
            problems.append(f"{where}: {anchor.get('word')!r} occurs {len(hits)} times in piece {k}, needed occurrence "
                            f"n={anchor.get('n', 0)} (from 0); piece {k} says: {said[:160]}")
    for k, p in enumerate(plan["pieces"]):
        for i, shot in enumerate(p.get("shots", [])):
            if "at" in shot:
                anchor_ok({"piece": k, "word": shot["at"], "n": shot.get("n", 0)}, f"piece {k} shot {i}")
            if shot.get("camera") not in plan["cameras"]:
                problems.append(f"piece {k} shot {i}: camera {shot.get('camera')!r} is not in cameras")
    for kind in ("titles", "panels"):
        for i, row in enumerate(plan.get(kind, [])):
            for key in ("at", "until"):
                if key in row:
                    anchor_ok(row[key], f"{kind}[{i}].{key}")
    for i, row in enumerate(plan.get("panels", [])):
        path = folder / row["file"]
        if not path.exists():
            problems.append(f"panels[{i}]: no file {row['file']}")
            continue
        probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                                           "-of", "json", str(path)], capture_output=True, text=True).stdout or "{}")
        frames = int((probe.get("streams") or [{}])[0].get("nb_frames", 0) or 0)  # from the header: no decode
        if frames and not 0 <= row["source_in"] < frames:
            problems.append(f"panels[{i}]: source_in {row['source_in']} is outside {row['file']} (frames 0 to {frames - 1})")
        elif frames and "frames" in row and row["source_in"] + row["frames"] > frames:
            problems.append(f"panels[{i}]: source_in {row['source_in']} + frames {row['frames']} runs past {row['file']}'s {frames} frames")
    if problems:
        raise ValueError("the plan has problems, found before any audio was measured: " + "; ".join(problems))


def highlight_spans(titles, panels):
    """A highlight (a title whose template is a highlight) drawn round a panel's pixels must start and end inside one
    panel's span, or it outlines whatever comes before or after: the next panel, or his face (run 6, frames 1350,
    1550 and 1910). The look's full-length background on V1 is not a panel."""
    shown = [p for p in panels if p["track"] > 1]
    found = []
    for t in titles:
        if "highlight" not in t["template"].lower():
            continue
        first, last = t["record"], t["record"] + t["frames"]
        under = [p for p in shown if p["record"] <= first < p["record"] + p["source_out"] - p["source_in"]]
        if not under:
            found.append(f"highlight at frames {first} to {last} starts over no panel")
            continue
        end = max(p["record"] + p["source_out"] - p["source_in"] for p in under)
        if last > end:
            found.append(f"highlight at frames {first} to {last} outlives its panel ({under[0]['file']}, ends {end}) by "
                         f"{last - end} frames: end it on the panel's own anchor")
    return found


NEAR_CUT_FRAMES = 6  # an edge this close to a camera cut, and not on it, reads as a slip (run 6, cut 2: 1 to 6 frames)


def edges_near_cuts(segments, panels, titles):
    """Every panel and title edge 1 to NEAR_CUT_FRAMES frames from a camera cut: a graphic that belongs to the shot change
    but lands just off it shows a few frames of the wrong picture under or around it."""
    cuts = sorted(s["record"] for s in segments)[1:]
    found = []
    rows = [("panel " + p["file"].split("/")[-1], p["record"], p["record"] + p["source_out"] - p["source_in"]) for p in panels
            if p.get("track", 1) > 1] + [("title " + t["template"], t["record"], t["record"] + t["frames"]) for t in titles]
    for name, first, end in rows:
        for edge, at in (("starts", first), ("ends", end)):
            near = min(cuts, key=lambda c: abs(c - at), default=None)
            if near is not None and 0 < abs(near - at) <= NEAR_CUT_FRAMES:
                found.append(f"{name} {edge} at frame {at}, {abs(near - at)} frames {'before' if at < near else 'after'} the camera "
                             f"cut at {near}: on the cut, or far enough off it to read as meant")
    return found


def needs_attention(report):
    """What in the report needs the model: the exit code is 1 when this is not empty."""
    lav = report.get("joins") or {}
    return ([f"edge with no pause: piece {e['piece']} {e['side']}" for e in report["edges"]]
            + [f"join {j['join']} needs listen ({'; '.join(j.get('reasons') or [])})" for j in lav.get("joins", []) if j.get("needs_listen")]
            + [f"caption: {c}" for c in report["captions"] if "is in no caption" in c]
            + [f"doubtful word: {d}" for d in report.get("doubtful_words", [])]
            + [f"unchosen words in piece {u['piece']}: {u['words']!r}" for u in report.get("unchosen_words", [])]
            + [f"caption width: {w}" for w in report.get("caption_width", [])]
            + [f"caption refusal: {c}" for c in report.get("caption_refusals", [])]
            + report.get("graphic_spans", []) + report.get("edges_near_cuts", []))


def rebase(edit_list, source, target):
    """The edit list's file paths, relative to the plan's folder SOURCE, made relative to TARGET where it is written."""
    if source == target:
        return edit_list
    move = lambda path: os.path.relpath((source / path).resolve(), target)
    for camera in edit_list["cameras"].values():
        camera["file"] = move(camera["file"])
    edit_list["sound"]["lav"] = move(edit_list["sound"]["lav"])
    for panel in edit_list["panels"]:
        panel["file"] = move(panel["file"])
    return edit_list


def assemble(plan_path):
    plan = json.loads(plan_path.read_text())
    folder = plan_path.parent
    fps = float(plan["fps"])
    transcript = (folder / plan["transcript"]).resolve()
    lav = (folder / plan["sound"]["lav"]).resolve()
    everything = json.loads(transcript.read_text())["words"]
    tokens = spoken(everything)
    pieces, report = [], {"pieces": [], "edges": [], "captions": [], "joins": None, "unchosen_words": []}
    for k, p in enumerate(plan["pieces"]):
        first, _ = find_phrase(tokens, p["from"], p["near_s"])
        last, size = find_phrase(tokens, p["to"], p.get("to_near_s", tokens[first][1]["start"]), after_index=first - 1)
        kept = [w for _, w in tokens[first:last + size]]
        heard = everything[tokens[first][0]:tokens[last + size - 1][0] + 1]
        pieces.append(dict(p, approx_start=kept[0]["start"], approx_end=kept[-1]["end"], tokens=kept, heard=heard))
    check_plan(plan, folder, pieces)
    work = folder / "build" / "assemble"
    work.mkdir(parents=True, exist_ok=True)
    placed = joins_place(plan, folder, pieces, lav, transcript, work)
    report["joins"] = from_zero(placed["check"])
    report["edges"] = [{"piece": exact["piece"] - 1, "side": side, **exact[side]} for exact in placed["pieces"]
                       for side in ("start_edge", "end_edge") if exact[side].get("status") not in ("pause", "given")]
    if report["edges"]:
        context, _ = aligned_words(lav, transcript, pieces, work, around=[e["at"] for e in report["edges"]])
        ordered = sorted(context.values(), key=lambda w: w["start"])
        for e in report["edges"]:
            e["aligned_words_around"] = [(w["word"], w["start"], w["end"]) for w in ordered if abs(w["start"] - e["at"]) < 1.0]
            piece = pieces[e["piece"]]
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
        report["joins"] = from_zero(placed["check"])
    for k, (p, exact) in enumerate(zip(pieces, placed["pieces"])):
        p.update(start=exact["start"], end=exact["end"])
        # every word heard in the piece's audio, not only the chosen ones: joins place can reach past them for a pause
        chosen = {(w["start"], w["word"]) for w in p["tokens"]}
        inside = [w for w in everything if p["start"] - 0.02 <= w["start"] and w["end"] <= p["end"] + 0.02]
        p["heard"] = sorted({(w["start"], w["word"]): w for w in inside + p["tokens"]}.values(), key=lambda w: w["start"])
        p["stray"] = [w for w in p["heard"] if (w["start"], w["word"]) not in chosen]
    found_by_piece, doubtful_by_piece = aligned_words(lav, transcript, pieces, work, exact=True)
    for k, p in enumerate(pieces):
        found = found_by_piece[k]
        # The transcript runs early in connected speech, so a word after the piece's last chosen word can look inside it
        # when it is not: such a word counts only if the confidence aligner hears it there. A word before the first chosen
        # word, and a filler ([UM]), always count (run 5's "Yeah." scored 0.15 and was there).
        first_chosen = p["tokens"][0]["transcript_start"] if "transcript_start" in p["tokens"][0] else p["tokens"][0]["start"]
        heard_stray = [w for w in p["stray"] if w["word"].startswith("[") or w["start"] < first_chosen
                       or found.get((w["start"], w["word"]), {}).get("score", 0) >= STRAY_HEARD_SCORE]
        heard_stray = [w for w in heard_stray  # aligned outside the piece's audio: not in what the viewer hears
                       if p["start"] - 0.02 <= found.get((w["start"], w["word"]), w)["start"] <= p["end"] + 0.02]
        if heard_stray:
            report["unchosen_words"].append({"piece": k, "words": " ".join(w["word"] for w in heard_stray),
                                             "at_s": [round(found.get((w["start"], w["word"]), w)["start"], 2) for w in heard_stray],
                                             "why": "heard inside the piece's audio but outside its from/to words: keep them (and "
                                                    "caption them) or set the edge (start_s, end_s) to leave them out"})
    report["doubtful_words"] = []
    for k, p in enumerate(pieces):
        found, doubtful = found_by_piece[k], doubtful_by_piece[k]
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
        report["pieces"].append({"piece": exact["piece"] - 1, "record_s": round(p["record_s"], 4), "words": exact.get("words")})
    heard = []  # every word heard in the film, fillers included, on the timeline's clock: what is silence and what is not
    for k, p in enumerate(pieces):
        for w in p["heard"]:
            a = found_by_piece[k].get((w["start"], w["word"]), w)
            start, end = p["record_s"] + a["start"] - p["start"], p["record_s"] + a["end"] - p["start"]
            if end > p["record_s"] and start < p["record_s"] + p["end"] - p["start"]:
                heard.append({"text": w["word"], "start": round(max(start, p["record_s"]), 4),
                              "end": round(min(end, p["record_s"] + p["end"] - p["start"]), 4), "piece": k})
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
            cuts[at] = (shot["camera"], shot.get("framing", cameras[shot["camera"]].get("framing", {})), bool(shot.get("off")))
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
            cam, fr, off = look
            front_s = p["start"] + first / fps - p["record_s"]
            source_in = round((front_s - cameras[cam].get("picture_offset_s", 0.0)) * fps)
            segments.append({"camera": cam, "source_in": source_in, "record": first, "frames": nxt - first, "framing": fr,
                             **({"off": True} if off else {})})
    report["shortest_segments"] = sorted(({"record": s["record"], "frames": s["frames"]} for s in segments), key=lambda s: s["frames"])[:3]
    def on_timeline(lav_s):
        holder = next((p for p in pieces if p["start"] - 0.05 <= lav_s <= p["end"] + 0.05), None)
        if holder is None:
            raise ValueError(f"word_starts_s {lav_s} is in no piece's audio (it is on the lav's clock since 18 Nov)")
        return holder["record_s"] + lav_s - holder["start"]

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
            at = on_timeline(moved)  # given on the lav's clock, so it stays right when anything earlier in the film moves
            words[index]["start"] = round(at, 4)
            if index:
                words[index - 1]["end"] = round(at, 4)
        text = "\n".join(row.strip() for row in c["text"].split("/"))
        captions.append({"text": text, "start": c.get("start_s", words[0]["start"]), "end": words[-1]["end"] + c.get("hold_s", hold),
                         "words": words})
    for a, b in zip(captions, captions[1:]):
        if a["end"] > b["start"]:
            a["end"] = b["start"]
    for c in captions:
        c["start"], c["end"] = round(c["start"], 4), round(c["end"], 4)
    report["captions"] = unmatched
    import captions as template  # the look's caption template's own limits, checked here so the build does not refuse later
    lookfile = json.loads((HERE.parents[1] / "looks" / plan["look"] / "look.json").read_text())
    report["caption_width"], size_px, limit = template.width_warnings(captions, lookfile, plan["format"]["width"], plan["format"]["height"])
    face = lookfile["fusion"]["faces"][template.TEMPLATE_FACE]
    sample = "the quick brown fox jumps over a lazy dog "  # ordinary lower-case speech, spaces included
    per_character = template.row_width_px(sample, face["metrics"], size_px) / len(sample)
    report["caption_safe_line"] = {"px": limit, "characters_per_row_about": int((limit - 50) / per_character),
                                   "why": "a row with its pill must fit the safe line; plan the captions' rows to it"}
    report["caption_refusals"] = []
    for c in captions:
        try:
            template.frames_for_template(c, fps)
        except ValueError as refusal:
            report["caption_refusals"].append(str(refusal))
    titles, cuts = [], sorted(s["record"] for s in segments)[1:]
    for t in plan.get("titles", []):
        first = resolve_anchor(t["at"], pieces, fps, duration_frames, cuts)
        frames = t["frames"] if "frames" in t else resolve_anchor(t["until"], pieces, fps, duration_frames, cuts) - first
        titles.append({"template": t["template"], "inputs": t["inputs"], "record": first, "frames": frames})
    panels = []
    for row in plan.get("panels", []):
        first = resolve_anchor(row["at"], pieces, fps, duration_frames, cuts)
        frames = row["frames"] if "frames" in row else resolve_anchor(row["until"], pieces, fps, duration_frames, cuts) - first
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
    edit_list = {key: plan[key] for key in ("resolve_project", "fps", "format", "look", "cameras", "sound")}
    edit_list.update(duration_frames=duration_frames, segments=segments, panels=panels, titles=titles, audio=audio, heard=heard,
                     captions=captions)
    report["graphic_spans"] = highlight_spans(titles, panels)
    report["edges_near_cuts"] = edges_near_cuts(segments, panels, titles)
    report["joins_needs_listen"] = report["joins"].get("needs_listen", [])
    return edit_list, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    out = args.out or args.plan.parent / "edit-list.json"
    try:
        if out.exists() and not args.force:
            raise FileExistsError(f"{out} exists; pass --force to replace it")
        edit_list, report = assemble(args.plan.resolve())
        out.write_text(json.dumps(rebase(edit_list, args.plan.resolve().parent, out.resolve().parent), indent=1, ensure_ascii=False) + "\n")
        report["edit_list"] = str(out)
        report["duration_s"] = round(edit_list["duration_frames"] / float(edit_list["fps"]), 3)
        report["needs_the_model"] = needs_attention(report)
        print(json.dumps(report, indent=1, ensure_ascii=False))
        sys.exit(1 if report["needs_the_model"] else 0)
    except SystemExit:
        raise
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}))
        sys.exit(1)

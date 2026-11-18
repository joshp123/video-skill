"""The gate's eye and lip checks on a planned cut, before it is placed, with the clean alternatives at every cut.

Written by AI on 2026-11-18 by Claude Opus 5.5, after codex-switch run 5, where 9 of 15 full passes (4 to 6 minutes
each) went on blinks and a lip on the caption band at cut points the agent had just moved, each learnt from a full
render.

preflight.py EDIT_LIST [--out DIR] [--window 8]

On a scratch timeline (deleted after) it lays the planned picture: every segment on its camera, framing and grade, and
the panels over them, at their own record frames, as the finish timeline shows them without titles or captions. After
it, for every cut between two segments, strips of both cameras on both sides: the outgoing moment running on past the
cut and the incoming moment starting before it, WINDOW frames plus the gate's 3 either side. It renders the picture
alone (H.264, one pass, no sound: about 19 s for a 95 s cut) and reads every frame with the gate's own Vision instrument
(qc_vision.swift, about 11 s), then applies the gate's own rules and numbers, read from qc.py:

- eyes shut at a cut: within 3 frames of the cut, eye openness under 0.65 of the shot's normal (the median over the
  segment); read on the planned picture itself, as the gate reads its render. Within 0.05 above the limit it is
  "borderline": the same frame reads up to about 0.02 apart from one render to another;
- caption on his face: wherever the list has a caption up, his lower lip within the look's lowerLipToBandTopPx of the
  band's top (its bandTopOneLine or bandTopTwoLines, by the caption's rows);
- lips out of sync: at a join of two pieces, the outgoing picture running 4 frames or more into his next words.

For every cut it also tries every shift from -WINDOW to +WINDOW frames, with every pairing of cameras, and lists the
clean ones (clear of the borderline band too). At a join it offers only shifts that keep the outgoing picture over the
incoming piece's silence; a cut placed before the join is listed as "picture first" (the incoming camera's frames from
before its sound, usually other speech). Inside a piece both cameras show the same moment, so any shift keeps sync.
When nothing is clean it says so: the edge, the take or the pause must change.

It also lists every cut where the camera does not change, with the scale change its framing makes (a same-camera cut
with a small change reads as a jump cut; the gate does not measure it), and every frame where a screen-recording panel's
own picture jumps (a scroll or a new screen) while a highlight drawn before the jump is still up (the highlight may now
sit on something else; the gate does not measure it). Neither stops a pass.

Before the picture render is deleted (about 360 MB a pass), it exports at half size every flagged frame (OUT/flagged/)
and one still of each distinct layout, by camera, framing and the panels over it (OUT/layout/; no captions or titles,
which this render does not hold), and sets aside as hidden_cuts the same-camera cuts where the picture does not change
(an opaque panel over what moved, a camera panned off frame, a still body under a panel over his face), which are no
jump cuts. About 8 s.
It also checks his whole head (head.py): a fault where the frame's edge, the camera picture's own edge or a panel cuts
it; a no_face row wherever no face could be read in a shot in view or within 3 frames of a cut, which is a reason to
look and never a pass; and face_read_per_shot. Titles are not in this render: the gate checks them on the render.
Prints {faults, borderline, no_face, face_read_per_shot, cuts, jump_candidates, hidden_cuts, panel_moves,
flagged_frames, layouts, seconds}. Exit 1 when there is any fault. What it
cannot see: titles over his face, and the captions' real rows (it uses the look's band constants, as the gate does).
Tested on codex-switch run 5's builds 10, 12 and 18: every eye, lip and sync fault row their gates raised on full
renders, build 18's blink at frame 208 as borderline (0.68 of normal here, 0.58 in the gate), and no other fault row.
"""
import argparse
import os
import ast
import json
import statistics
import subprocess
import time
from pathlib import Path

import look
import place
import session


HERE = Path(__file__).resolve().parent
VISION_SOURCE = HERE / "qc_vision.swift"
BORDERLINE = 0.05  # run 5, build 18, frame 208: the gate read 0.58 of normal on the render, this scratch render 0.68


def gate_constants():
    """The numbers the gate (qc.py) decides by, read from its source so there is one copy of each."""
    wanted = {"EYES_CLOSED_FRACTION_OF_SHOT_NORMAL", "FRAMES_EACH_SIDE_OF_A_CUT", "CAPTION_BAND_HALF_HEIGHT_PX",
              "FULL_FRAME_TEXT_EVERY_N_FRAMES", "OUT_OF_SYNC_FAULT_FRAMES"}
    found = {}
    for node in ast.parse((HERE / "qc.py").read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in wanted:
            found[node.targets[0].id] = ast.literal_eval(node.value)
    return found


def openness(frame):
    face = frame.get("face")
    if not face or face.get("left_eye_openness", -1) <= 0 or face.get("right_eye_openness", -1) <= 0:
        return None
    return (face["left_eye_openness"] + face["right_eye_openness"]) / 2


def caption_rows(captions, fps):
    """{timeline frame: rows of the caption up then}."""
    up = {}
    for c in captions:
        for f in range(int(round(c["start"] * fps)), int(round(c["end"] * fps))):
            up[f] = len(c["text"].split("\n"))
    return up


def first_word_frame(captions, fps, after):
    starts = [round(w["start"] * fps) for c in captions for w in c["words"] if round(w["start"] * fps) >= after]
    return min(starts) if starts else None


def last_word_frame(captions, fps, before):
    ends = [round(w["end"] * fps) for c in captions for w in c["words"] if round(w["end"] * fps) <= before]
    return max(ends) if ends else None


def run(list_path, out, window):
    """measure(), then the picture render deleted whatever happened: about 360 MB a pass (run 6 left 6 GB of them)."""
    try:
        return measure(list_path, out, window)
    finally:
        (out / "preflight-picture.mp4").unlink(missing_ok=True)


def frames_of(render_file, numbers, vf, out_pattern=None):
    """The render's frames NUMBERS (from 0), through the filter VF: written as files to OUT_PATTERN (%d numbered in order),
    or returned as raw bytes."""
    if not numbers:
        return b""
    pick = "+".join(f"eq(n\\,{n})" for n in sorted(numbers))
    command = ["ffmpeg", "-v", "error", "-y", "-i", str(render_file), "-vf", f"select={pick},{vf}", "-fps_mode", "passthrough"]
    command += [str(out_pattern)] if out_pattern else ["-f", "rawvideo", "-"]
    return subprocess.run(command, capture_output=True, check=True).stdout


def exports(render_file, out, data, faults, borderline, jumps):
    """What an agent needs to look at once the render is gone: every flagged frame, and one still of each distinct layout
    (camera, framing, the panels over it), at half size. And which same-camera cuts cannot be seen because the picture
    does not change there (a camera cut under an opaque panel is no jump cut, run 7)."""
    segments = sorted(data["segments"], key=lambda s: s["record"])
    end = max(s["record"] + s["frames"] for s in segments)
    shown = [p for p in data.get("panels", []) if p.get("track", 1) > 1]

    def layout(f):
        seg = next((s for s in segments if s["record"] <= f < s["record"] + s["frames"]), None)
        over = tuple(sorted((p["file"], json.dumps(p.get("framing", {}), sort_keys=True)) for p in shown
                            if p["record"] <= f < p["record"] + p["source_out"] - p["source_in"]))
        return (seg and seg["camera"], json.dumps((seg or {}).get("framing", {}), sort_keys=True), over)
    firsts, spans = {}, []
    for f in range(end):
        key = layout(f)
        if spans and spans[-1][0] == key:
            spans[-1][2] = f
        else:
            spans.append([key, f, f])
    for key, a, b in spans:
        firsts.setdefault(key, (a + b) // 2)
    flagged = sorted({r["frame"] for r in faults + borderline if 0 <= r.get("frame", -1) < end})
    layouts = sorted(firsts.values())
    around_cuts = sorted({j["cut"] - k for j in jumps if j["cut"] >= 2 for k in (2, 1, 0)})
    every = sorted(set(flagged) | set(layouts) | set(around_cuts))
    work = out / "frames-read"
    for folder in (work, out / "flagged", out / "layout"):
        if folder.exists():
            subprocess.run(["trash", str(folder)], check=True)
        folder.mkdir(parents=True)
    frames_of(render_file, every, "scale=iw/2:-2", work / "%04d.jpg")  # one decode of the render for all of it
    still = {n: work / f"{i:04d}.jpg" for i, n in enumerate(every, 1)}
    result = {"flagged_frames": [], "layouts": []}
    for n in flagged:
        target = out / "flagged" / f"flagged-frame-{n}.jpg"
        still[n].replace(target) if n not in layouts and n not in around_cuts else target.write_bytes(still[n].read_bytes())
        result["flagged_frames"].append(str(target))
    for n in layouts:
        target = out / "layout" / f"layout-frame-{n}.jpg"
        target.write_bytes(still[n].read_bytes())
        camera, framing, over = next(k for k, v in firsts.items() if v == n)
        result["layouts"].append({"frame": n, "still": str(target), "camera": camera, "framing": json.loads(framing),
                                  "panels": [p for p, _ in over]})

    def grey(n):
        return subprocess.run(["ffmpeg", "-v", "error", "-i", str(still[n]), "-vf", "scale=54:96,format=gray", "-f", "rawvideo", "-"],
                              capture_output=True, check=True).stdout
    picture = {n: grey(n) for n in around_cuts}
    mean_change = lambda a, b: sum(abs(x - y) for x, y in zip(picture[a], picture[b])) / (54 * 96)
    for j in jumps:
        c = j["cut"]
        if all(n in picture for n in (c - 2, c - 1, c)):
            j["change_at_cut"] = round(mean_change(c - 1, c), 2)
            j["change_before"] = round(mean_change(c - 2, c - 1), 2)
            j["hidden"] = j["change_at_cut"] < max(2.0, 2 * j["change_before"])
    subprocess.run(["trash", str(work)], check=True)
    return result


def measure(list_path, out, window):
    began = time.monotonic()
    data = json.loads(list_path.read_text())
    folder = list_path.parent
    gate = gate_constants()
    eyes_limit, side = gate["EYES_CLOSED_FRACTION_OF_SHOT_NORMAL"], gate["FRAMES_EACH_SIDE_OF_A_CUT"]
    fps = float(data["fps"])
    cameras, segments = data["cameras"], data["segments"]
    piece_starts = {round(a["record_s"] * fps) for a in data.get("audio", [])[1:]}
    resolve, project = session.connect(data["resolve_project"])
    pool = project.GetMediaPool()
    media = place.media_by_path(pool)
    groups = {g.GetName(): g for g in project.GetColorGroupsList() or []}
    name = "preflight scratch (delete)"
    old = session.timeline_named(project, name)
    if old:
        pool.DeleteTimelines([old])
    timeline = pool.CreateEmptyTimeline(name)
    if timeline is None:
        raise RuntimeError("Could not make the scratch timeline")
    out.mkdir(parents=True, exist_ok=True)
    render_file = out / "preflight-picture.mp4"
    if render_file.exists():
        subprocess.run(["trash", str(render_file)], check=True)
    strips = []  # (cut index, camera, which side, first scratch frame, first timeline frame, length)
    try:
        project.SetCurrentTimeline(timeline)
        for key, value in {"useCustomSettings": "1", "timelineResolutionWidth": str(data["format"]["width"]),
                           "timelineResolutionHeight": str(data["format"]["height"]), "useInverseDRT": "1"}.items():
            timeline.SetSettings({key: value})
        start = timeline.GetStartFrame()
        while timeline.GetTrackCount("video") < place.APP_TRACK:
            timeline.AddTrack("video")

        def lay(camera, segment_index, first_timeline_frame, length, at):
            segment = segments[segment_index]
            path = str((folder / cameras[camera]["file"]).resolve())
            source = look.source_frame(segment, cameras, camera, first_timeline_frame, fps)
            clip = (pool.AppendToTimeline([{"mediaPoolItem": media[path], "startFrame": source, "endFrame": source + length,
                                            "mediaType": 1, "trackIndex": place.CAMERAS_TRACK, "recordFrame": start + at}]) or [None])[0]
            if clip is None:
                raise RuntimeError(f"Could not place {camera} at source frame {source}")
            place.apply_look(resolve, project, clip, {"framing": look.framing_for(segments, segment_index, camera),
                                                      "group": cameras[camera]["group"], "grade": cameras[camera]["grade"]},
                             length, groups, f"{camera} at {at}")

        for index, segment in enumerate(segments):
            lay(segment["camera"], index, segment["record"], segment["frames"], segment["record"])
        for row in data.get("panels", []):  # as the finish timeline shows them: a panel can hide his face from the gate
            path = str((folder / row["file"]).resolve())
            if path not in media:
                media[path] = (pool.ImportMedia([path]) or [None])[0]
            place.append(resolve, project, timeline, media[path], row, row["track"], row["source_in"],
                         row["source_out"] - row["source_in"], groups)
        cursor = max(s["record"] + s["frames"] for s in segments) + 5
        reach = window + side
        for index in range(1, len(segments)):
            cut = segments[index]["record"]
            for camera in cameras:
                for which, segment_index in (("out", index - 1), ("in", index)):
                    lay(camera, segment_index, cut - reach, 2 * reach, cursor)
                    strips.append((index, camera, which, cursor, cut - reach, 2 * reach))
                    cursor += 2 * reach + 2
        settings = {"TargetDir": str(out), "CustomName": render_file.stem, "ExportVideo": True, "ExportAudio": False,
                    "ExportSubtitle": False, "SelectAllFrames": True, "FormatWidth": int(data["format"]["width"]),
                    "FormatHeight": int(data["format"]["height"]), "VideoQuality": 20000, "MultiPassEncode": False}

        def add_job():
            if not project.SetCurrentRenderFormatAndCodec("mp4", "H264"):
                raise RuntimeError("Could not set the render format")
            if not project.SetRenderSettings(settings):
                raise RuntimeError("SetRenderSettings refused the preflight render")
            return project.AddRenderJob()
        rendered = time.monotonic()
        job = session.start_render(project, add_job)
        while str((project.GetRenderJobStatus(job) or {}).get("JobStatus", "")).lower() not in ("complete", "failed", "cancelled"):
            time.sleep(0.5)
        status = project.GetRenderJobStatus(job)
        project.DeleteRenderJob(job)
        render_seconds = time.monotonic() - rendered
        if str(status.get("JobStatus", "")).lower() != "complete":
            raise RuntimeError(f"Preflight render {status}")
    finally:
        pool.DeleteTimelines([timeline])
        resolve.OpenPage("edit")
    session.no_dialogs("the preflight render")
    vision_binary = session.CACHE / "bin/qc_vision"
    if not vision_binary.exists() or vision_binary.stat().st_mtime < VISION_SOURCE.stat().st_mtime:
        vision_binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["/usr/bin/swiftc", "-O", "-suppress-warnings", "-o", str(vision_binary), str(VISION_SOURCE)], check=True, capture_output=True,
                       env={k: v for k, v in os.environ.items() if k not in ("DEVELOPER_DIR", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET")})
    lookfile = json.loads((place.LOOKS / data["look"] / "look.json").read_text())
    height = int(data["format"]["height"])
    band_centre = round(height * (1 - lookfile["subtitles"]["resolveTemplate"]["centreY"]))
    band = (band_centre - gate["CAPTION_BAND_HALF_HEIGHT_PX"], band_centre + gate["CAPTION_BAND_HALF_HEIGHT_PX"])
    seen = time.monotonic()
    lines = subprocess.run([str(vision_binary), str(render_file), str(band[0]), str(band[1]), "100000"],
                           capture_output=True, text=True, check=True).stdout.splitlines()
    vision = [json.loads(line) for line in lines if line.strip()]
    vision_seconds = time.monotonic() - seen
    eyes = [openness(f) for f in vision]
    lips = [(f.get("face") or {}).get("lips") for f in vision]

    def eye(scratch_frame):
        return eyes[scratch_frame] if 0 <= scratch_frame < len(eyes) else None

    normal = {}
    for index, s in enumerate(segments):
        values = [e for e in (eye(f) for f in range(s["record"], s["record"] + s["frames"])) if e]
        normal[(index, s["camera"])] = statistics.median(values) if values else None
    strip_of = {(i, c, w): (first, tl_first) for i, c, w, first, tl_first, _ in strips}
    for i, c, w, first, tl_first, length in strips:  # another camera's normal: its own strips at that cut
        if (i - (1 if w == "out" else 0), c) not in normal:
            values = [e for e in (eye(f) for k in ("out", "in") for f in range(strip_of[(i, c, k)][0], strip_of[(i, c, k)][0] + length)) if e]
            normal[(i - (1 if w == "out" else 0), c)] = statistics.median(values) if values else None

    def worst_at(index, cut_at, out_camera, in_camera):
        """The lowest eye openness relative to its shot's normal within the gate's 3 frames of a cut at CUT_AT."""
        worst = None
        planned_cut = segments[index]["record"]
        for f in range(cut_at - side, cut_at + side + 1):
            camera, which, segment_index = (out_camera, "out", index - 1) if f < cut_at else (in_camera, "in", index)
            same_as_planned = camera == segments[segment_index]["camera"] and ((f < planned_cut) == (which == "out"))
            if same_as_planned:  # the planned picture itself, as the gate reads it (a strip of the same frames reads up to 0.02 apart)
                value = eye(f)
            else:
                first, tl_first = strip_of[(index, camera, which)]
                value = eye(first + f - tl_first)
            base = normal.get((segment_index, camera))
            if value and base:
                relative = value / base
                if worst is None or relative < worst[0]:
                    worst = (relative, f, camera)
        return worst

    faults, borderline, cuts = [], [], []
    captions = data.get("captions", [])
    for index in range(1, len(segments)):
        out_seg, in_seg = segments[index - 1], segments[index]
        cut = in_seg["record"]
        # a join only when the two segments show different moments at the cut (a shot starting on a word inside a piece
        # shows the same moment on the other camera); then the join is the nearest piece start
        moments = [look.source_frame(seg, cameras, "front" if "front" in cameras else next(iter(cameras)), cut, fps)
                   for seg in (out_seg, in_seg)]
        join = (min((p for p in piece_starts if abs(cut - p) <= window), key=lambda p: abs(cut - p), default=None)
                if abs(moments[0] - moments[1]) > 1 else None)
        planned = worst_at(index, cut, out_seg["camera"], in_seg["camera"])
        row = {"cut": cut, "time_s": round(cut / fps, 2), "cameras": [out_seg["camera"], in_seg["camera"]],
               "where": "inside a piece" if join is None else f"the join of two pieces at frame {join}"}
        if planned and planned[0] < eyes_limit:
            row["fault"] = f"eyes {100 - 100 * planned[0]:.0f}% closed at frame {planned[1]} on the {planned[2]}"
            faults.append({"class": "eyes shut at a cut", "frame": planned[1], "cut": cut, "what": row["fault"]})
        elif planned and planned[0] < eyes_limit + BORDERLINE:
            row["borderline"] = (f"eyes {100 - 100 * planned[0]:.0f}% closed at frame {planned[1]} on the {planned[2]}, within "
                                 f"{BORDERLINE} of the gate's limit: the render's reading can fall either side")
            borderline.append({"class": "eyes shut at a cut", "frame": planned[1], "cut": cut, "what": row["borderline"]})
        silent_until = first_word_frame(captions, fps, join) if join is not None else None
        if join is not None and cut > join and silent_until is not None and cut - silent_until >= gate["OUT_OF_SYNC_FAULT_FRAMES"]:
            what = (f"the outgoing {out_seg['camera']} runs {cut - silent_until} frames into his next words (from frame "
                    f"{silent_until}): his mouth is the other piece's")
            row["sync"] = what
            faults.append({"class": "lips out of sync", "frame": silent_until, "cut": cut, "what": what})
        if join is not None and cut < join:
            row["picture_first"] = (f"the incoming {in_seg['camera']} shows {join - cut} frames from before its sound starts, "
                                    "which may be other speech: look at them")
        options = []
        for out_camera in cameras:
            for in_camera in cameras:
                clean = []
                for shift in range(-window, window + 1):
                    at = cut + shift
                    if join is not None and (at < join or (silent_until is not None and at > silent_until)):
                        continue  # at a join, offered only where the outgoing picture runs on over silence
                    result = worst_at(index, at, out_camera, in_camera)
                    if result and result[0] >= eyes_limit + BORDERLINE:
                        clean.append(shift)
                if clean:
                    options.append({"cameras": [out_camera, in_camera], "clean_shifts": compress(clean),
                                    "planned": [out_camera, in_camera] == row["cameras"]})
        row["options"] = options or ("no clean cut within the window on any pairing of cameras: change the edge, the "
                                     "take, or the pause before it")
        cuts.append(row)
    clearance = lookfile["subtitles"].get("faceClearance", {})
    gap_needed = clearance.get("lowerLipToBandTopPx", 0)
    rows_at = caption_rows(data.get("captions", []), fps)
    close = []
    for f, rows in sorted(rows_at.items()):
        if f < len(lips) and lips[f]:
            band_top = clearance.get("bandTopTwoLines" if rows >= 2 else "bandTopOneLine")
            if band_top is not None and band_top - lips[f][3] < gap_needed:
                close.append((f, band_top - lips[f][3]))
    runs = []
    for f, gap in close:
        if runs and f - runs[-1][1] <= 2:
            runs[-1][1], runs[-1][2] = f, min(runs[-1][2], gap)
        else:
            runs.append([f, f, gap])
    for first, last, gap in runs:
        segment = next((s for s in segments if s["record"] <= first < s["record"] + s["frames"]), None)
        faults.append({"class": "caption on his face", "frame": first, "last_frame": last,
                       "what": f"band top {gap} px under his lower lip (the look asks {gap_needed}), frames {first} to {last}"
                               + (f", in the {segment['camera']} segment at {segment['record']} (framing {segment.get('framing')})" if segment else "")})
    jumps = []
    for index in range(1, len(segments)):
        a, b = segments[index - 1], segments[index]
        if a["camera"] == b["camera"]:
            za, zb = a.get("framing", {}).get("ZoomX", 1.0), b.get("framing", {}).get("ZoomX", 1.0)
            jumps.append({"cut": b["record"], "time_s": round(b["record"] / fps, 2), "camera": a["camera"],
                          "scale_change": round(max(za, zb) / min(za, zb), 3)})
    panel_moves = []
    for row in data.get("panels", []):
        if row.get("track") != place.APP_TRACK:
            continue
        frames = row["source_out"] - row["source_in"]
        for source_frame, change in picture_changes(str((folder / row["file"]).resolve())):
            if row["source_in"] < source_frame < row["source_out"]:
                at = row["record"] + source_frame - row["source_in"]
                over = [t for t in data.get("titles", []) if "highlight" in t["template"].lower() and t["record"] < at < t["record"] + t["frames"]]
                if over:  # a click or a scroll is often the point; a highlight drawn before it and still up after it is the fault
                    panel_moves.append({"frame": at, "panel": row["file"], "source_frame": source_frame, "change": round(change, 1),
                                        "what": f"the panel's picture jumps at its frame {source_frame} (timeline frame {at}) while the "
                                                f"highlight from frame {over[0]['record']} is still up: is it still on its target?"})
    import head  # his whole head in the planned picture: frame edges and panels (titles are not in this render)
    head_faults, no_face, coverage = head.check([(f.get("face") or {}).get("box") for f in vision], data, folder,
                                                int(data["format"]["width"]), height)
    faults += head_faults
    looked = exports(render_file, out, data, faults, borderline + no_face, jumps)
    return {"faults": faults, "borderline": borderline, "no_face": no_face, "face_read_per_shot": coverage, "cuts": cuts, "jump_candidates": [j for j in jumps if not j.get("hidden")],
            "hidden_cuts": [j for j in jumps if j.get("hidden")], "panel_moves": panel_moves, **looked,
            "frames_read": len(vision),
            "seconds": {"render": round(render_seconds, 1), "vision": round(vision_seconds, 1), "all": round(time.monotonic() - began, 1)}}


def picture_changes(path):
    """[(frame, mean luma change from the frame before)] where a screen recording's picture changes at once: a scroll or a
    new screen. On run 5's menu recording the 34 px scroll measured 69.9, the pointer moving about 1, a still frame 0.01."""
    if path in _changes:
        return _changes[path]
    log = session.CACHE / "preflight-changes.txt"
    subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-an", "-vf",
                    f"tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file={log}", "-f", "null", "-"],
                   check=True, capture_output=True)
    found, frame = [], None
    for line in log.read_text().splitlines():
        if line.startswith("frame:"):
            frame = int(line.split()[0].split(":")[1])
        elif "YAVG=" in line and frame is not None and float(line.split("=")[1]) > PANEL_CHANGE:
            found.append((frame + 1, float(line.split("=")[1])))  # tblend's frame n compares n with n + 1
    log.unlink()
    _changes[path] = found
    return found


_changes = {}
PANEL_CHANGE = 5.0


def compress(values):
    """[-8, -7, -6, 2, 3] -> "-8..-6, 2..3"."""
    runs = []
    for v in values:
        if runs and v == runs[-1][1] + 1:
            runs[-1][1] = v
        else:
            runs.append([v, v])
    return ", ".join(f"{a}" if a == b else f"{a}..{b}" for a, b in runs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_list", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--window", type=int, default=8)
    args = parser.parse_args()
    edit_list = args.edit_list.resolve()
    out = (args.out or edit_list.parent / "build" / "preflight").absolute()

    session.main(lambda: (lambda result: {**result, "differences": result["faults"]})(run(edit_list, out, args.window)))

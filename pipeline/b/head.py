"""Is his whole head in the picture? One rule for preflight (the planned picture, before placing) and the gate (a render).

Written by AI on 2026-11-18 by Claude Opus 5.5, after Josh on run 6's cut: "the crop still crops out half my head, which
is a bit weird". Every check had passed it: they watch his eyes at cuts and his mouth against the captions, and nothing
asked whether his head was in the picture.

His head is the face box Apple Vision reads, widened by his hair: HAIR_ABOVE of the box's height above it and HAIR_SIDE
of its width either side, measured with Vision's person segmentation on 22 frames of both cameras of the 12 October
session (hair above the box: 0.47 to 0.77 of its height, median 0.6; hair and ears to one side 0.29 to 0.40 of its
width, to the other 0 to 0.11 as his head turns). The margins are the large end of what was measured, so a head is
never called whole when its hair is cut; on the side his head turns from they over-reach by up to a third of the face's
width, which SLACK absorbs.

For each frame of a camera shot it finds the part of his head outside what is seen: the frame, or the camera's own
picture when its framing leaves the frame partly empty or crops it; under a panel (from the edit list's framing:
Resolve scales a clip to fill the frame, then zooms about the centre, Pan moves it by the fitted width / frame width per
unit, Tilt in frame pixels up, crops in fitted pixels before zoom); or, on a render, under a title's text. A fault is
SLACK of his head's height or more, for MIN_FRAMES frames or more. And every stretch of MIN_NO_FACE frames or more of a
shot whose camera is in view where no face is read, and every cut with no face read within 3 frames either side, is a
row to look at: no face read is never a pass.
"""
import json
import subprocess

HAIR_ABOVE = 0.75
HAIR_SIDE = 0.4
SLACK = 0.05
MIN_FRAMES = 3
MIN_NO_FACE = 5
CUT_SIDE = 3


def source_size(path, cache={}):
    if path not in cache:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json",
                              str(path)], capture_output=True, text=True).stdout
        stream = json.loads(out or "{}").get("streams", [{}])[0]
        cache[path] = (int(stream.get("width", 0)), int(stream.get("height", 0)))
    return cache[path]


def placed(size, framing, width, height):
    """[x0, y0, x1, y1] of a clip of SIZE on a WIDTH by HEIGHT frame with Resolve's FRAMING (scale to crop)."""
    w, h = size
    if not w or not h:
        return None
    fit = max(width / w, height / h)
    fw, fh = w * fit, h * fit
    zx, zy = framing.get("ZoomX", 1.0), framing.get("ZoomY", framing.get("ZoomX", 1.0))
    cx, cy = width / 2 + framing.get("Pan", 0) * fw / width, height / 2 - framing.get("Tilt", 0)
    return [cx + (-fw / 2 + framing.get("CropLeft", 0)) * zx, cy + (-fh / 2 + framing.get("CropTop", 0)) * zy,
            cx + (fw / 2 - framing.get("CropRight", 0)) * zx, cy + (fh / 2 - framing.get("CropBottom", 0)) * zy]


def overlap(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def head_of(box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return [x0 - HAIR_SIDE * w, y0 - HAIR_ABOVE * h, x1 + HAIR_SIDE * w, y1]


def runs(frames):
    out = []
    for f in sorted(frames):
        if out and f == out[-1][1] + 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return out


def check(faces, edit_list, folder, width, height, text_boxes=None):
    """FACES: the face box [x0, y0, x1, y1] read at each frame from 0, or None. TEXT_BOXES: {frame: [box, ...]} of text
    read outside the caption band (a render's titles), or None. Returns (faults, looks, coverage): rows with class,
    first and last frame, what, and the frame to show; coverage per shot."""
    segments = sorted(edit_list["segments"], key=lambda s: s["record"])
    cameras = edit_list["cameras"]
    panels = []
    for p in edit_list.get("panels", []):
        if p.get("track", 1) > 1:
            rect = placed(source_size(folder / p["file"]), p.get("framing", {}), width, height)
            if rect:
                panels.append((p["record"], p["record"] + p["source_out"] - p["source_in"], rect, p["file"].split("/")[-1]))
    titles = [(t["record"], t["record"] + t["frames"], t["template"]) for t in edit_list.get("titles", [])]
    frame_rect = [0, 0, width, height]
    faults, looks, coverage = [], [], []
    for index, seg in enumerate(segments):
        camera = cameras[seg["camera"]]
        framing = seg.get("framing") or camera.get("framing") or {}
        picture = placed(source_size(folder / camera["file"]), framing, width, height)
        seen = overlap(frame_rect, picture) if picture else frame_rect
        found = {"edge": {}, "panel": {}, "title": {}}
        no_face, read = [], 0
        for f in range(seg["record"], min(seg["record"] + seg["frames"], len(faces))):
            over = [p for p in panels if p[0] <= f < p[1]]
            visible = area(seen) - sum(area(overlap(seen, p[2])) for p in over)
            box = faces[f]
            if not box:
                if area(seen) > 0 and visible > 0.1 * area(seen):
                    no_face.append(f)
                continue
            read += 1
            head = head_of(box)
            tall, wide = head[3] - head[1], head[2] - head[0]
            out_by = {"left": seen[0] - head[0], "right": head[2] - seen[2], "top": seen[1] - head[1]}
            side, by = max(out_by.items(), key=lambda kv: kv[1])
            if by >= SLACK * tall:
                found["edge"][f] = (side, by, by / tall)
            for start, end, rect, name in over:
                o = overlap(head, rect)
                if o[2] - o[0] >= SLACK * wide and o[3] - o[1] >= SLACK * tall:
                    found["panel"][f] = (name, o[3] - o[1], area(o) / area(head))
            for start, end, template in titles:
                if start <= f < end and text_boxes and f in text_boxes:
                    for t in text_boxes[f]:
                        o = overlap(head, t)
                        # a highlight drawn on a panel over his head is the panel's fault, already counted
                        share = (area(o) - sum(area(overlap(o, p[2])) for p in over)) / area(head)
                        if share >= SLACK:
                            found["title"][f] = (template, o[3] - o[1], share)
        for kind, hits in found.items():
            for first, last in runs(hits):
                if last - first + 1 < MIN_FRAMES:
                    continue
                worst = max(range(first, last + 1), key=lambda f: hits[f][2] if kind != "edge" else hits[f][1])
                detail = hits[worst]
                what = (f"his head is cut by the {detail[0]} edge of the {'frame' if seen == frame_rect else 'picture'} by up to "
                        f"{detail[1]:.0f} px ({detail[2]:.0%} of its height)" if kind == "edge" else
                        f"{detail[2]:.0%} of his head is under the {'panel ' + detail[0] if kind == 'panel' else 'title ' + repr(detail[0])}, "
                        f"{detail[1]:.0f} px of its height")
                faults.append({"class": f"head cut by {'the frame' if kind == 'edge' else 'a ' + kind}", "frame": worst,
                               "first": first, "last": last, "camera": seg["camera"], "segment": index,
                               "what": f"{what}, frames {first} to {last} ({seg['camera']} shot at {seg['record']}, framing {framing})"})
        for first, last in runs(no_face):
            if last - first + 1 >= MIN_NO_FACE:
                looks.append({"class": "no face read", "frame": (first + last) // 2, "first": first, "last": last,
                              "camera": seg["camera"], "segment": index,
                              "what": f"no face read in frames {first} to {last} of the {seg['camera']} shot at {seg['record']} while its "
                                      "picture is in view: nothing about his eyes, mouth or head was checked there"})
        coverage.append({"segment": index, "camera": seg["camera"], "record": seg["record"], "frames": seg["frames"],
                         "face_read": read})
    for seg in segments[1:]:
        cut = seg["record"]
        around = [f for f in range(cut - CUT_SIDE, cut + CUT_SIDE + 1) if 0 <= f < len(faces)]
        for side, frames in (("before", [f for f in around if f < cut]), ("after", [f for f in around if f >= cut])):
            if frames and not any(faces[f] for f in frames):
                looks.append({"class": "no face read at a cut", "frame": cut, "first": frames[0], "last": frames[-1],
                              "what": f"no face read in the {len(frames)} frames {side} the cut at {cut}: its eyes were not checked"})
    return faults, looks, coverage

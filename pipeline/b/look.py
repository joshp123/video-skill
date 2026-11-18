"""Frames for the model to look at, many in one call: graded, from Resolve, without placing or rendering the cut.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2.

  look.py EDIT_LIST --cuts --out DIR
      Before placing: for every segment of the list, its first and last frame on both cameras, graded as the finish
      timeline grades them and framed as the list frames them (the other camera at the framing of its nearest segment),
      as labelled contact sheets of up to six segments each (a cell "3W* 1284" is segment 3 on the wide camera, the list's
      choice, at timeline frame 1284; each segment's four cells are each camera's first frame, then its last). Pick each camera and see a blink or a hand for the whole video at once. A one-frame clip of each
      is placed on a scratch timeline, the sheets come from Timeline.ExportThumbnails, and the scratch timeline is deleted.

  look.py EDIT_LIST --timeline NAME --at FRAME [FRAME ...] --out DIR
      After placing: each frame of timeline NAME at full size (PNG) and at phone width (390 by 693 JPEG), from
      Timeline.ExportFrame (about 45 ms a frame once warm; the playhead does not move). ExportFrame does not draw the
      caption track: to see captions, render a still or a short range with render.py.

Prints the files written. The model judges; nothing here does.
"""
import argparse
import json
from pathlib import Path

import place
import session

PHONE = 693  # 390 by 693: a 1080 by 1920 frame at an iPhone's width in points


def source_frame(segment, cameras, camera, record, fps):
    """The frame of CAMERA's own file showing the moment at timeline frame RECORD of SEGMENT."""
    shown = cameras[segment["camera"]]
    front_s = (segment["source_in"] + record - segment["record"]) / fps + shown.get("picture_offset_s", 0.0)
    return round((front_s - cameras[camera].get("picture_offset_s", 0.0)) * fps)


def framing_for(segments, index, camera):
    if segments[index]["camera"] == camera:
        return segments[index].get("framing", {})
    others = [(abs(k - index), s) for k, s in enumerate(segments) if s["camera"] == camera]
    return min(others, key=lambda pair: pair[0])[1].get("framing", {}) if others else {}


def cuts(data, folder, out):
    resolve, project = session.connect(data["resolve_project"])
    pool, fps = project.GetMediaPool(), float(data["fps"])
    media = place.media_by_path(pool)
    groups = {group.GetName(): group for group in project.GetColorGroupsList() or []}
    cameras, segments = data["cameras"], data["segments"]
    name = "look scratch (delete)"
    old = session.timeline_named(project, name)
    if old:
        pool.DeleteTimelines([old])
    timeline = pool.CreateEmptyTimeline(name)
    if timeline is None:
        raise RuntimeError("Could not make the scratch timeline")
    out.mkdir(parents=True, exist_ok=True)
    sheets = []
    try:
        project.SetCurrentTimeline(timeline)
        for key, value in {"useCustomSettings": "1", "timelineResolutionWidth": str(data["format"]["width"]),
                           "timelineResolutionHeight": str(data["format"]["height"]), "useInverseDRT": "1"}.items():
            timeline.SetSettings({key: value})
        start, cells = timeline.GetStartFrame(), []
        for index, segment in enumerate(segments):
            for camera in cameras:
                for end, record in (("first", segment["record"]), ("last", segment["record"] + segment["frames"] - 1)):
                    path = str((folder / cameras[camera]["file"]).resolve())
                    frame = source_frame(segment, cameras, camera, record, fps)
                    at = len(cells)
                    clip = (pool.AppendToTimeline([{"mediaPoolItem": media[path], "startFrame": frame, "endFrame": frame + 1,
                                                    "mediaType": 1, "trackIndex": 1, "recordFrame": start + at}]) or [None])[0]
                    if clip is None:
                        raise RuntimeError(f"Could not place {camera} frame {frame}")
                    look = {"framing": framing_for(segments, index, camera), "group": cameras[camera]["group"],
                            "grade": cameras[camera]["grade"]}
                    place.apply_look(resolve, project, clip, look, 1, groups, f"{camera} frame {frame}")
                    chosen = "*" if camera == segment["camera"] else ""
                    cells.append({"frameOffset": at, "label": f"{index}{camera[0].upper()}{chosen} {record}"})
        per_sheet = 24
        for first in range(0, len(cells), per_sheet):
            path = out / f"cuts-{first // per_sheet + 1}.jpg"
            result = timeline.ExportThumbnails(cells[first:first + per_sheet],
                                               {"outputType": "file", "filePath": str(path), "maxDimension": 3000, "quality": 85})
            if not result or not result.get("success"):
                raise RuntimeError(f"ExportThumbnails failed: {result}")
            sheets.append(str(path))
    finally:
        pool.DeleteTimelines([timeline])
    return {"sheets": sheets, "cells": len(cells),
            "key": "each label is <segment><camera's initial><* when it is the list's camera> <timeline frame>; each segment "
                   "gives four cells in order: each camera's first frame, then its last"}


def frames(data, name, at, out):
    resolve, project = session.connect(data["resolve_project"])
    timeline = session.timeline_named(project, name)
    if timeline is None:
        raise ValueError(f"No timeline {name!r}")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for frame in at:
        full, phone = out / f"{name} {frame}.png", out / f"{name} {frame} phone.jpg"
        for path, options in ((full, {}), (phone, {"maxDimension": PHONE, "quality": 90})):
            result = timeline.ExportFrame(frame, {"outputType": "file", "filePath": str(path), **options})
            if not result or not result.get("success"):
                raise RuntimeError(f"ExportFrame {frame} failed: {result}")
        written.append({"frame": frame, "full": str(full), "phone": str(phone)})
    return {"frames": written, "captions_drawn": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_list", type=Path)
    parser.add_argument("--cuts", action="store_true")
    parser.add_argument("--timeline")
    parser.add_argument("--at", type=int, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.edit_list.read_text())
    if args.cuts:
        session.main(lambda: cuts(data, args.edit_list.resolve().parent, args.out.absolute()))
    else:
        session.main(lambda: frames(data, args.timeline, args.at, args.out.absolute()))

#!/usr/bin/env python3
"""Export a settled viewer frame, or a lossless one-frame Resolve render.
Written by AI on 2026-10-25 by GPT-6.1 Sol. Working files go to the cache and are trashed after the copy, and the
timeline is selected with a few seconds of retries, since 2026-10-26 (Claude Opus 5.5, stream B of the hill-climb).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid


def timecode(frame, fps, drop):
    nominal = round(fps)
    if drop:
        dropped = round(nominal * 0.0666666667)
        ten_minutes = nominal * 600 - dropped * 9
        minutes = nominal * 60 - dropped
        blocks, remainder = divmod(frame, ten_minutes)
        frame += dropped * 9 * blocks + dropped * max(0, (remainder - dropped) // minutes)
    seconds, frames = divmod(frame, nominal)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    separator = ";" if drop else ":"
    return f"{hours % 24:02}:{minutes:02}:{seconds:02}{separator}{frames:02}"


WORKING = Path(__file__).resolve().parents[2] / ".cache/pipeline-b/frame"


def select_timeline(project, timeline):
    """SetCurrentTimeline fails now and then while another script has just used Resolve (5 of 15 calls in run 3);
    a retry seconds later works."""
    deadline = time.monotonic() + 10
    while not project.SetCurrentTimeline(timeline):
        if time.monotonic() > deadline:
            raise RuntimeError("Cannot select timeline")
        time.sleep(1)


def export_frame(name, frame, output):
    import DaVinciResolveScript
    resolve = DaVinciResolveScript.scriptapp("Resolve")
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = next((project.GetTimelineByIndex(index)
                     for index in range(1, project.GetTimelineCount() + 1)
                     if project.GetTimelineByIndex(index).GetName() == name), None)
    if timeline is None:
        raise ValueError(f"Timeline not found: {name}")
    if frame < 0 or frame >= timeline.GetEndFrame() - timeline.GetStartFrame():
        raise ValueError("Frame is outside the timeline")
    output = output.absolute()
    if output.suffix.lower() != ".png" or output.exists():
        raise ValueError("Output must be a new .png path")
    output.parent.mkdir(parents=True, exist_ok=True)
    previous_timeline, previous_page = project.GetCurrentTimeline(), resolve.GetCurrentPage()
    previous_timecode = timeline.GetCurrentTimecode()
    marks = timeline.GetMarkInOut()
    prefix = output.stem + "-" + uuid.uuid4().hex[:8]
    job = None
    WORKING.mkdir(parents=True, exist_ok=True)
    fps = float(timeline.GetSettings()["timelineFrameRate"])
    seek = timecode(timeline.GetStartFrame() + frame, fps, ";" in timeline.GetStartTimecode())
    absolute_frame = timeline.GetStartFrame() + frame
    captions = any(any(item.GetStart() <= absolute_frame < item.GetEnd()
                           for item in timeline.GetItemListInTrack("subtitle", track) or [])
                   for track in range(1, timeline.GetTrackCount("subtitle") + 1))
    try:
        select_timeline(project, timeline)
        reason = "subtitle at requested frame" if captions else "viewer did not settle"
        if not captions:
            resolve.OpenPage("color")
            time.sleep(1)
            if timeline.SetCurrentTimecode(seek):
                stills = [WORKING / (prefix + f"-viewer-{index}.png") for index in (1, 2)]
                exported = []
                for still in stills:
                    time.sleep(1)
                    exported.append(timeline.GetCurrentTimecode() == seek
                                    and project.ExportCurrentFrameAsStill(str(still)))
                if all(exported) and all(still.exists() for still in stills):
                    hashes = [hashlib.sha256(still.read_bytes()).hexdigest() for still in stills]
                    if hashes[0] == hashes[1] and timeline.GetCurrentTimecode() == seek:
                        shutil.copyfile(stills[-1], output)
                        return {"route": "viewer", "frame": frame, "timecode": seek,
                                "output": str(output), "settled_sha256": hashes[0]}
        if any(bounds and not {"in", "out"} <= bounds.keys() for bounds in marks.values()):
            raise RuntimeError("Cannot safely restore a single-sided timeline mark after rendering")
        if project.IsRenderingInProgress():
            raise RuntimeError("Resolve is already rendering; cannot start a frame render")
        if not project.SetCurrentRenderFormatAndCodec("png", "RGB16"):
            raise RuntimeError("Cannot set lossless PNG render format")
        if not project.SetCurrentRenderMode(1):
            raise RuntimeError("Cannot set single-clip render mode")
        settings = {"TargetDir": str(WORKING), "CustomName": prefix + "-render",
                    "ExportVideo": True, "ExportAudio": False, "SelectAllFrames": False,
                    "MarkIn": absolute_frame, "MarkOut": absolute_frame,
                    "FormatWidth": int(timeline.GetSettings()["timelineResolutionWidth"]),
                    "FormatHeight": int(timeline.GetSettings()["timelineResolutionHeight"]),
                    "ExportSubtitle": captions, "SubtitleFormat": "BurnIn"}
        if not project.SetRenderSettings(settings):
            raise RuntimeError("Cannot set one-frame render settings")
        job = project.AddRenderJob()
        if not job:
            raise RuntimeError("Cannot add one-frame render job")
        deadline = time.monotonic() + 90
        while not project.StartRendering([job]):  # refused now and then, accepted seconds later; once over 60 s (stream H, 26 Oct)
            if time.monotonic() > deadline:
                raise RuntimeError("Cannot start one-frame render")
            time.sleep(1)
        deadline = time.monotonic() + 600
        while True:
            status = project.GetRenderJobStatus(job)
            state = status.get("JobStatus", "").lower()
            if state == "complete":
                break
            if "failed" in state or "cancel" in state or time.monotonic() > deadline:
                raise RuntimeError(f"One-frame render did not complete: {status}; job {job}")
            time.sleep(0.5)
        files = list(WORKING.glob(prefix + "-render*.png"))
        if len(files) != 1:
            raise RuntimeError(f"Expected one rendered PNG, found {len(files)}")
        shutil.copyfile(files[0], output)
        return {"route": "render", "reason": reason, "frame": frame,
                "timecode": seek, "output": str(output), "render_status": status}
    finally:
        if job:
            project.DeleteRenderJob(job)
        leftovers = [str(path) for path in WORKING.glob(prefix + "*")]
        if leftovers:
            subprocess.run(["trash", *leftovers], check=False)
        if timeline.GetMarkInOut() != marks:
            timeline.ClearMarkInOut("all")
            for track, bounds in marks.items():
                if "in" in bounds and "out" in bounds:
                    if not timeline.SetMarkInOut(bounds["in"], bounds["out"], track):
                        raise RuntimeError("Could not restore timeline marks")
            if timeline.GetMarkInOut() != marks:
                raise RuntimeError("Timeline marks did not restore exactly")
        if previous_timecode:
            timeline.SetCurrentTimecode(previous_timecode)
        if previous_timeline:
            select_timeline(project, previous_timeline)
        if previous_page:
            resolve.OpenPage(previous_page)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline")
    parser.add_argument("frame", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    exit_code = 0
    try:
        print(json.dumps(export_frame(args.timeline, args.frame, args.output)))
    except Exception as error:
        print(json.dumps({"error": str(error)}))
        exit_code = 1
    sys.stdout.flush()
    os._exit(exit_code)

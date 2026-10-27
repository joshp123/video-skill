#!/usr/bin/env python3
"""Render a timeline from Resolve and wait for it: render_timeline.py PROJECT TIMELINE OUTPUT [--preset ...]
[--subtitles] [--range IN OUT] [--load-render-preset NAME]. NAME (the loudness preset pipeline/b/loudness.py prints)
is loaded first and must load; the preset's own format, codec and range are then set as below. Returns when the job is complete, its marks cleared and the job deleted, so the Resolve
lock (scratch/bin/resolve-py) is held for the whole render and nothing else drives Resolve meanwhile. Exit 1 when the
render fails or is cancelled.

Written by AI on 2026-10-22 by GPT-6.1 Sol. Waits for its own render since 2026-10-26 (Claude Opus 5.5, stream B of
the hill-climb): a render that returned at once let place.py run under it and fail (run 3, build 10). Refuses a
timeline that still holds a multicam since 2026-10-26 (Claude Opus 5.5, stream I): render the finish timeline that
pipeline/b/finish.py makes from the cut timeline.
Since 2026-10-27 (Claude Opus 5.5, hill-climb stream L): StartRendering is retried for up to 30 s (Resolve refuses it now and
then and accepts it seconds later), the job is deleted and the Edit page reopened on every way out, and a finished render
counts only when ffprobe finds a video stream in it (run 4 wrote two phone renders with sound and no picture).
"""

import argparse
import os
import sys
from pathlib import Path
if "TIMELINE_NAME" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("timeline_name")
    parser.add_argument("output_file",type=Path)
    parser.add_argument("--range", dest="frame_range", type=int, nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--preset",choices=["master","phone","post","still"],default="master")
    parser.add_argument("--subtitles",action="store_true")
    parser.add_argument("--load-render-preset")
    args = parser.parse_args()
    PROJECT_NAME = args.project_name
    TIMELINE_NAME, OUTPUT_FILE, PRESET, SUBTITLES = args.timeline_name,args.output_file,args.preset,args.subtitles
    RENDER_PRESET = args.load_render_preset
    if args.frame_range is not None:
        RANGE = args.frame_range

expected_project = PROJECT_NAME

import json
import subprocess
import time
START_RENDERING_RETRY_SECONDS = 30
if __name__ == "__main__":
    def exit_on_error(kind, error, trace):
        if "resolve" in globals():
            resolve.OpenPage("edit")  # setting up a render leaves Resolve on the Deliver page
        print({"error": f"{kind.__name__}: {error}"})
        sys.stdout.flush()
        os._exit(1)
    sys.excepthook = exit_on_error
if "resolve" not in globals():
    import DaVinciResolveScript
    resolve = DaVinciResolveScript.scriptapp("Resolve")

def call(method, *args):
    deadline = time.monotonic() + 1800
    while resolve.GetProjectManager().GetCurrentProject().GetName() != expected_project:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Expected project {expected_project!r} was unavailable for 30 minutes")
        time.sleep(30)
    return method(*args)

project = call(resolve.GetProjectManager().GetCurrentProject)

timeline = next(t for i in range(1,call(project.GetTimelineCount)+1) if call((t:=call(project.GetTimelineByIndex,i)).GetName) == TIMELINE_NAME)
assert call(project.SetCurrentTimeline,timeline)
multicam_items = [f"V{track} at {call(item.GetStart) - call(timeline.GetStartFrame)}"
                  for track in range(1, call(timeline.GetTrackCount, "video") + 1)
                  for item in call(timeline.GetItemListInTrack, "video", track) or []
                  if call(item.GetMediaPoolItem) and call(call(item.GetMediaPoolItem).GetClipProperty, "Type") == "Multicam"]
if multicam_items:
    raise ValueError(f"{TIMELINE_NAME!r} still holds a multicam ({', '.join(multicam_items[:3])}): render its finish timeline (pipeline/b/finish.py)")
if globals().get("RENDER_PRESET") and not call(project.LoadRenderPreset, RENDER_PRESET):
    raise RuntimeError(f"Could not load render preset {RENDER_PRESET!r}")
output = Path(OUTPUT_FILE)
assert not output.exists(), f"refusing to overwrite {output}"
preset = globals().get("PRESET","master")
if preset == "still":
    RANGE = globals().get("RANGE", (0, 0))
    if RANGE[0] != RANGE[1]:
        raise ValueError("The still preset requires a one-frame RANGE (inclusive in and out)")
    if output.suffix.lower() != ".png":
        raise ValueError("The still preset writes a numbered PNG; use a .png output path")
    if list(output.parent.glob(output.stem + "*.png")):
        raise FileExistsError(f"refusing to overwrite still sequence {output}")
assert call(project.SetCurrentRenderFormatAndCodec, *(("png", "RGB16") if preset == "still" else
            (("mp4", "H264") if preset in ("phone", "post") else ("mov", "ProRes422HQ"))))
settings = {"TargetDir":str(output.parent),"CustomName":output.stem,"ExportVideo":True,"ExportAudio":True,
            "FormatWidth":int(call(timeline.GetSettings)["timelineResolutionWidth"]),"FormatHeight":int(call(timeline.GetSettings)["timelineResolutionHeight"]),
            "ExportSubtitle":bool(globals().get("SUBTITLES",False))}
if globals().get("SUBTITLES"):
    settings["SubtitleFormat"] = "BurnIn"
start = call(timeline.GetStartFrame)
if globals().get("RANGE"):
    settings.update(SelectAllFrames=False,MarkIn=start+RANGE[0],MarkOut=start+RANGE[1])
    frames = RANGE[1]-RANGE[0]+1
else:
    settings["SelectAllFrames"] = True
    frames = call(timeline.GetEndFrame)-start
if preset == "master":
    settings.update(AudioCodec="lpcm", AudioBitDepth=24, AudioSampleRate=48000)
if preset == "still":
    settings["ExportAudio"] = False
if preset in ("phone", "post"):
    duration = frames/float(call(timeline.GetSettings)["timelineFrameRate"])
    # 8 Mbit/s: X Media Studio's 5-8 Mbit/s range, also inside X Ads' 6-10 Mbit/s 1080p range.
    # https://help.x.com/en/using-x/media-studio-faqs
    bitrate = 8000 if preset == "post" else int(28000000*8/duration/1000-320)
    settings.update(VideoQuality=bitrate,EncodingProfile="High",MultiPassEncode=True,NetworkOptimization=True,
                    AudioCodec="aac",AudioSampleRate=48000,ColorSpaceTag="Rec.709",GammaTag="Rec.709")
assert call(project.SetRenderSettings,settings), settings
job = call(project.AddRenderJob)
if not job:
    raise RuntimeError("AddRenderJob returned no job")
try:
    deadline = time.monotonic() + START_RENDERING_RETRY_SECONDS
    while not call(project.StartRendering,[job]):
        if time.monotonic() > deadline:
            raise RuntimeError(f"StartRendering refused job {job} for {START_RENDERING_RETRY_SECONDS} s")
        time.sleep(1)
    while True:
        result = call(project.GetRenderJobStatus,job)
        state = str(result.get("JobStatus", "")).lower()
        if state == "complete":
            break
        if "fail" in state or "cancel" in state:
            raise RuntimeError(f"Render {state}: {result}")
        time.sleep(2)
finally:
    marks_cleared = call(timeline.ClearMarkInOut, "all")
    job_deleted = call(project.DeleteRenderJob, job)
call(resolve.OpenPage,"edit")
if not marks_cleared or not job_deleted:
    raise RuntimeError(f"Could not clear render marks or delete completed job {job}")
if preset != "still":
    streams = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(output)],
                                        capture_output=True, text=True).stdout or "{}").get("streams", [])
    kinds = sorted(stream["codec_type"] for stream in streams)
    if "video" not in kinds:
        raise RuntimeError(f"{output} has no video stream (streams: {kinds or 'none'}); do not use it")
result.update(job=job, output=str(output), job_deleted=True)
print(result)

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

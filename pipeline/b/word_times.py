#!/usr/bin/env python3
"""Read Resolve word and segment times for a timeline's own sound, without pairing.
Written by AI on 2026-10-25 by GPT-6.1 Sol. Renders the timeline's sound itself since 2026-10-26 (Claude Opus 5.5,
stream B of the hill-climb): every cut's sound is cut from one file, which the old route refused.

word_times.py NAME [--media FILE]. Without --media, Resolve renders the timeline's mixed sound (audio only, 24-bit PCM
in a .mov, into .cache/pipeline-b/word-times/), imports it into the Generated bin and transcribes it, so the times are
those of the sound the viewer hears, on the timeline's clock. --media FILE transcribes a mix starting at frame zero.
Resolve's times locate words; they ran up to 0.7 s out on run 3 and dropped words, so a word's onset is settled on
the level trace (envelope.py), not here.
Since 2026-10-27 (Claude Opus 5.5, hill-climb stream L): Resolve refuses StartRendering now and then and accepts it seconds
later (run 4, story and editor), so the start is retried for up to 30 s, and the job is deleted on every way out.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
import DaVinciResolveScript

RENDERS = Path(__file__).resolve().parents[2] / ".cache/pipeline-b/word-times"
START_RENDERING_RETRY_SECONDS = 30


def render_timeline_sound(project, timeline):
    """The timeline's mixed sound as one file, rendered by Resolve, waited for in this process (it holds the lock)."""
    if project.IsRenderingInProgress():
        raise RuntimeError("Resolve is already rendering")
    RENDERS.mkdir(parents=True, exist_ok=True)
    name = f"{timeline.GetName().replace('/', '_')}-{uuid.uuid4().hex[:8]}"
    project.SetCurrentTimeline(timeline)
    if not (project.SetCurrentRenderMode(1) and project.SetCurrentRenderFormatAndCodec("mov", "ProRes422HQ")
            and project.SetRenderSettings({"TargetDir": str(RENDERS), "CustomName": name, "ExportVideo": False,
                                           "ExportAudio": True, "AudioCodec": "lpcm", "AudioBitDepth": 24,
                                           "AudioSampleRate": 48000, "SelectAllFrames": True})):
        raise RuntimeError("Could not set the sound render")
    job = project.AddRenderJob()
    if not job:
        raise RuntimeError("AddRenderJob returned no job for the sound render")
    try:
        deadline = time.monotonic() + START_RENDERING_RETRY_SECONDS
        while not project.StartRendering([job]):
            if time.monotonic() > deadline:
                raise RuntimeError(f"StartRendering refused the sound render for {START_RENDERING_RETRY_SECONDS} s")
            time.sleep(1)
        while True:
            status = project.GetRenderJobStatus(job)
            state = str(status.get("JobStatus", "")).lower()
            if state == "complete":
                break
            if "fail" in state or "cancel" in state:
                raise RuntimeError(f"Sound render {state}: {status}")
            time.sleep(1)
    finally:
        project.DeleteRenderJob(job)
    files = list(RENDERS.glob(name + "*.mov"))
    if len(files) != 1:
        raise RuntimeError(f"Expected one rendered sound file, found {len(files)}")
    return files[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Timeline name in the current project")
    parser.add_argument("--media", type=Path, help="A mixed audio file starting at timeline frame zero")
    args = parser.parse_args()
    resolve = DaVinciResolveScript.scriptapp("Resolve")
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                     if project.GetTimelineByIndex(i).GetName() == args.name), None)
    if timeline is None:
        raise ValueError(f"Timeline not found: {args.name}")
    fps = float(timeline.GetSetting("timelineFrameRate"))
    duration = (timeline.GetEndFrame() - timeline.GetStartFrame()) / fps
    pool = project.GetMediaPool()
    source_start, source_end, offset = 0.0, duration, 0.0
    path = args.media.resolve(strict=True) if args.media else render_timeline_sound(project, timeline)
    def find(folder):
        for clip in folder.GetClipList() or []:
            if clip.GetClipProperty("File Path") == str(path):
                return clip
        for child in folder.GetSubFolderList() or []:
            found = find(child)
            if found:
                return found
    root = pool.GetRootFolder()
    item = find(root)
    if item is None:
        previous_folder = pool.GetCurrentFolder()
        generated = next((folder for folder in root.GetSubFolderList() or []
                          if folder.GetName() == "Generated"), None)
        if generated is None:
            generated = pool.AddSubFolder(root, "Generated")
        try:
            pool.SetCurrentFolder(generated)
            imported = pool.ImportMedia([str(path)])
            if not imported:
                raise RuntimeError(f"Resolve could not import {path}")
            item = imported[0]
        finally:
            pool.SetCurrentFolder(previous_folder)
    resolve.OpenPage("edit")
    if not item.TranscribeAudio(False):
        raise RuntimeError("Resolve TranscribeAudio returned False")
    transcript = item.GetTranscription()
    if not transcript or "segments" not in transcript:
        raise RuntimeError("Resolve returned no transcription segments")
    media_fps = float(item.GetClipProperty("FPS"))

    def seconds(timecode):
        hours, minutes, seconds, frames = map(int, timecode.split(":"))
        return hours * 3600 + minutes * 60 + seconds + frames / media_fps

    origin = seconds(item.GetClipProperty("Start TC"))

    def convert(entry):
        start, end = seconds(entry["start"]) - origin, seconds(entry["end"]) - origin
        if end <= source_start or start >= source_end:
            return None
        return {**{key: value for key, value in entry.items() if key not in ("words", "start", "end")},
                "start": round(start + offset, 6), "end": round(end + offset, 6)}

    segments, words = [], []
    for segment in transcript["segments"]:
        converted = convert(segment)
        if converted is not None:
            converted["words"] = [word for entry in segment.get("words", [])
                                  if (word := convert(entry)) is not None]
            segments.append(converted)
            words.extend(converted["words"])
    print(json.dumps({"timeline": args.name, "media": str(path), "clock": "timeline-relative seconds",
                      "source_start_s": source_start, "source_end_s": source_end,
                      "source_to_timeline_offset_s": offset, "words": words, "segments": segments}, indent=2))


if __name__ == "__main__":
    status = 0
    try:
        main()
    except Exception as error:
        print(json.dumps({"error": str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

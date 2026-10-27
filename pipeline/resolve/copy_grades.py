#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol."""

import argparse
import json
import sys
import os
from pathlib import Path
if "FROM_TIMELINE" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("edit_folder", type=Path)
    parser.add_argument("from_timeline")
    parser.add_argument("to_timeline")
    args = parser.parse_args()
    EDIT_FOLDER = args.edit_folder
    FROM_TIMELINE, TO_TIMELINE = args.from_timeline, args.to_timeline

expected_project = json.loads((Path(EDIT_FOLDER)/"edit/edit.json").read_text(encoding="utf-8"))["resolve_project"]

import time
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

source_timeline = next(t for i in range(1,call(project.GetTimelineCount)+1) if call((t:=call(project.GetTimelineByIndex,i)).GetName) == FROM_TIMELINE)
target_timeline = next(t for i in range(1,call(project.GetTimelineCount)+1) if call((t:=call(project.GetTimelineByIndex,i)).GetName) == TO_TIMELINE)

def video_items(timeline):
    return [item for track in range(1,call(timeline.GetTrackCount,"video")+1)
            for item in call(timeline.GetItemListInTrack,"video",track) or []]

def source_key(item):
    media = call(item.GetMediaPoolItem)
    path = call(media.GetClipProperty,"File Path") if media is not None else ""
    if not path:
        return None
    return path, call(item.GetSourceStartFrame), call(item.GetDuration)

sources = {}
for item in video_items(source_timeline):
    key = source_key(item)
    if key is not None:
        sources.setdefault(key,item)
matches, unmatched = [], []
for item in video_items(target_timeline):
    key = source_key(item)
    record = {"target_id":call(item.GetUniqueId),"name":call(item.GetName),"record_frame":call(item.GetStart),
              "source_key":key}
    source = sources.get(key)
    if source is None:
        unmatched.append(record)
    else:
        if not call(source.CopyGrades,[item]):
            raise RuntimeError(f"CopyGrades failed for {record}")
        matches.append({**record,"source_id":call(source.GetUniqueId)})
result = {"from_timeline":FROM_TIMELINE,"to_timeline":TO_TIMELINE,"matches":matches,"unmatched":unmatched}
print(json.dumps(result,indent=2))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

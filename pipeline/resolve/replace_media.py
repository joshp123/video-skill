#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol."""

import argparse
import json
import sys
import os
from pathlib import Path
if "TIMELINE_NAME" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("edit_folder", type=Path)
    parser.add_argument("timeline_name")
    parser.add_argument("media_file", type=Path)
    parser.add_argument("new_file", type=Path)
    args = parser.parse_args()
    EDIT_FOLDER = args.edit_folder
    TIMELINE_NAME, MEDIA_FILE, NEW_FILE = args.timeline_name, args.media_file, args.new_file

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

mp = call(project.GetMediaPool)
tl = next(t for i in range(1,call(project.GetTimelineCount)+1) if call((t:=call(project.GetTimelineByIndex,i)).GetName) == TIMELINE_NAME)
old_path, new_path = str(Path(MEDIA_FILE).resolve()), str(Path(NEW_FILE).resolve())

def items():
    return [(kind,track,item) for kind in ("video","audio","subtitle")
            for track in range(1,call(tl.GetTrackCount,kind)+1)
            for item in call(tl.GetItemListInTrack,kind,track) or []]

def record_ranges():
    return sorted((kind,track,call(item.GetStart),call(item.GetEnd)) for kind,track,item in items())

before = record_ranges()
replacements = []
for kind,track,item in items():
    if kind == "subtitle":
        continue
    media = call(item.GetMediaPoolItem)
    if media is not None and call(media.GetClipProperty,"File Path") == old_path:
        replacements.append({"item":item,"kind":kind,"track":track,"record_frame":call(item.GetStart),
                             "frames":call(item.GetDuration),"source_frame":call(item.GetSourceStartFrame)})
if not replacements:
    raise RuntimeError(f"No items use {old_path} on {TIMELINE_NAME!r}")
new_media = (call(mp.ImportMedia,[new_path]) or [None])[0]
if new_media is None:
    raise RuntimeError(f"Could not import {new_path}")
original_timeline = call(project.GetCurrentTimeline)
changed = []
try:
    if not call(project.SetCurrentTimeline,tl):
        raise RuntimeError(f"Could not select {TIMELINE_NAME!r}")
    for replacement in replacements:
        item = replacement["item"]
        if not call(tl.DeleteClips,[item],False):
            raise RuntimeError("Could not delete the old timeline item without ripple")
        source = replacement["source_frame"]
        new_item = (call(mp.AppendToTimeline,[{"mediaPoolItem":new_media,"mediaType":1 if replacement["kind"]=="video" else 2,
                    "trackIndex":replacement["track"],"recordFrame":replacement["record_frame"],
                    "startFrame":source,"endFrame":source+replacement["frames"]}]) or [None])[0]
        if new_item is None:
            raise RuntimeError(f"Could not append the replacement at {replacement['record_frame']}")
        actual = {"record_frame":call(new_item.GetStart),"frames":call(new_item.GetDuration),"source_frame":call(new_item.GetSourceStartFrame)}
        if any(actual[key] != replacement[key] for key in actual):
            raise RuntimeError(f"Replacement range differs: {actual}")
        if call(call(new_item.GetMediaPoolItem).GetClipProperty,"File Path") != new_path:
            raise RuntimeError("Replacement item does not use the imported file")
        changed.append({key:value for key,value in replacement.items() if key != "item"})
    after = record_ranges()
    if before != after:
        raise RuntimeError("Timeline item count or record ranges changed during replacement")
    result = {"timeline":TIMELINE_NAME,"old_file":old_path,"new_file":new_path,"replaced":changed,
              "items_before":len(before),"items_after":len(after),"record_ranges_unchanged":True}
finally:
    call(project.SetCurrentTimeline,original_timeline)
print(json.dumps(result,indent=2))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

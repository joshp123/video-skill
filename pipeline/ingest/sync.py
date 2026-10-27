#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol."""

import argparse
import datetime
import json
from pathlib import Path
if "FIRST_FILE" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("first_file", type=Path)
    parser.add_argument("second_file", type=Path)
    parser.add_argument("--write", type=Path, metavar="EDIT_JSON")
    parser.add_argument("--name", help="media entry: lav, or cameras.wide")
    args = parser.parse_args()
    PROJECT_NAME = args.project_name
    FIRST_FILE, SECOND_FILE = args.first_file, args.second_file
    WRITE, NAME = args.write, args.name

expected_project = PROJECT_NAME

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
root = call(mp.GetRootFolder)
def find(folder, path):
    for item in call(folder.GetClipList) or []:
        if call(item.GetClipProperty, "File Path") == str(path):
            return item
    for child in call(folder.GetSubFolderList) or []:
        item = find(child, path)
        if item is not None:
            return item

def import_media(path, bin_name):
    item = find(root, path)
    if item is None:
        folder = next((child for child in call(root.GetSubFolderList) or [] if call(child.GetName) == bin_name), None)
        if folder is None:
            folder = call(mp.AddSubFolder, root, bin_name)
        call(mp.SetCurrentFolder, folder)
        item = call(mp.ImportMedia, [str(path)])[0]
    return item

first = import_media(Path(FIRST_FILE).resolve(), "Source")
second = import_media(Path(SECOND_FILE).resolve(), "Source")
call(resolve.OpenPage, "edit")
original = call(project.GetCurrentTimeline)
tl = call(mp.CreateEmptyTimeline, "scratch sync " + datetime.datetime.now().strftime("%Y-%m-%d %H%M%S%f"))
call(project.SetCurrentTimeline, tl)
try:
    start = call(tl.GetStartFrame)
    call(tl.AddTrack, "video")
    call(tl.AddTrack, "audio", "stereo")
    items = []
    for track, item in enumerate((first, second), 1):
        items.extend(call(mp.AppendToTimeline, [{"mediaPoolItem": item, "mediaType": kind, "trackIndex": track, "recordFrame": start} for kind in (1, 2)]))
    t0 = time.monotonic()
    assert call(tl.AutoAlignClips, items, {"SyncUsing": resolve.AUTO_ALIGN_CLIPS_USING_WAVEFORM, "UseTrack": resolve.AUTO_ALIGN_CLIPS_WAVEFORM_TRACK_AUTOMATIC})
    front, wide = call(tl.GetItemListInTrack, "audio", 1)[0], call(tl.GetItemListInTrack, "audio", 2)[0]
    fps = float(call(tl.GetSettings)["timelineFrameRate"])
    source_origins = []
    for item in (first, second):
        h, m, sec, frame = map(int, call(item.GetClipProperty, "Start TC").split(":"))
        source_origins.append(h*3600 + m*60 + sec + frame/float(call(item.GetClipProperty, "FPS")))
    record_difference = call(wide.GetStart, True)-call(front.GetStart, True)
    first_source = call(front.GetSourceStartTime)-source_origins[0]
    second_source = call(wide.GetSourceStartTime)-source_origins[1]
    offset = record_difference/fps + first_source-second_source
    print(f"first time = second time + {offset:.9f}")
    print(json.dumps({"offset_s": offset, "seconds": round(time.monotonic()-t0, 3), "fps": fps, "audio_record_difference_frames": record_difference, "first_source_s": first_source, "second_source_s": second_source}))
    if globals().get("WRITE"):
        path = Path(WRITE)
        data = json.loads(path.read_text())
        entry = data["media"]
        for key in NAME.split("."):
            entry = entry[key]
        old = json.dumps(entry["offset_s"])
        # Replace only this media entry, retaining other workers' data verbatim.
        raw = path.read_text()
        import re
        key = NAME.split(".")[-1]
        pattern = r'("'+re.escape(key)+r'"\s*:\s*\{[^}]*?"offset_s"\s*:\s*)'+re.escape(old)
        updated, count = re.subn(pattern, lambda match: match[1]+str(offset), raw, count=1)
        assert count == 1
        path.write_text(updated)
finally:
    call(project.SetCurrentTimeline, original)
    assert call(mp.DeleteTimelines, [tl])

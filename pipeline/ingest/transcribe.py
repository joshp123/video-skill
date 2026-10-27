#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol."""

import argparse
import json
from pathlib import Path
if "MEDIA_FILE" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("media_file", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--offset", type=float, default=0)
    args = parser.parse_args()
    PROJECT_NAME = args.project_name
    MEDIA_FILE, OUT, OFFSET = args.media_file, args.out, args.offset

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

def seconds(tc, fps):
    h, m, s, f = map(int, tc.split(":"))
    return h * 3600 + m * 60 + s + f / fps

path = Path(MEDIA_FILE).resolve()
item = import_media(path, "Source")
call(resolve.OpenPage, "edit")
t0 = time.monotonic()
assert call(item.TranscribeAudio, False)
transcript = call(item.GetTranscription)
fps = float(call(item.GetClipProperty, "FPS"))
origin = seconds(call(item.GetClipProperty, "Start TC"), fps)
offset = globals().get("OFFSET", 0)
words, lines = [], []
for segment in transcript["segments"]:
    lines.append(f"{seconds(segment['start'], fps)-origin+offset:.3f} --> {seconds(segment['end'], fps)-origin+offset:.3f}  {segment['text'].strip()}")
    for word in segment["words"]:
        if word["text"].strip() == "(...)":
            continue
        words.append({"start": seconds(word["start"], fps)-origin+offset, "end": seconds(word["end"], fps)-origin+offset, "word": word["text"].strip()})
Path(str(OUT)+".json").write_text(json.dumps({"audio": str(path), "offset_seconds": offset, "words": words}, indent=2)+"\n")
Path(str(OUT)+".txt").write_text("\n".join(lines)+"\n")
print(json.dumps({"words": len(words), "segments": len(lines), "seconds": round(time.monotonic()-t0, 3)}))

#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol. Saves despite a playback-rate mismatch since 2026-10-26 (Claude Opus 5.5, stream B).
Makes the cameras' multicam "cameras" (pipeline/b/multicam.py) and reports each angle's file and offset, for
inventory.md, since 2026-10-26 (Claude Opus 5.5, stream I)."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Read from "2026-10-14 where-was-i short" on 2026-10-22.
# Its useInverseDRT was 0; Josh explicitly requested 1 for new projects.
COLOUR_SETTINGS = {
    "colorScienceMode": "davinciYRGBColorManagedv2",
    "colorSpaceTimeline": "DaVinci WG/Intermediate",
    "colorSpaceOutput": "Rec.709 Gamma 2.4",
    "inputDRT": "DaVinci",
    "outputDRT": "DaVinci",
    "timelineInputResMismatchBehavior": "scaleToCrop",
    "useInverseDRT": "1",
}

if "PROJECT_NAME" not in globals() or "EDIT_FOLDER" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("edit_folder", type=Path)
    arguments = parser.parse_args()
    PROJECT_NAME, EDIT_FOLDER = arguments.project_name, arguments.edit_folder

edit_folder = Path(EDIT_FOLDER).resolve()
edit = json.loads((edit_folder / "edit/edit.json").read_text(encoding="utf-8"))
if "resolve" not in globals():
    import DaVinciResolveScript
    resolve = DaVinciResolveScript.scriptapp("Resolve")
manager = resolve.GetProjectManager()
current = manager.GetCurrentProject()
expected_project = edit["resolve_project"]
# Creating the edit's own project must work before that project exists. Pin
# navigation to the starting project; all settings/imports below pin to the target.
if PROJECT_NAME == expected_project or (current and current.GetName() == PROJECT_NAME):
    expected_project = current.GetName() if current else None

def call(method, *args):
    deadline = time.monotonic() + 1800
    while True:
        current = manager.GetCurrentProject()
        if (current.GetName() if current else None) == expected_project:
            return method(*args)
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Expected project {expected_project!r} was unavailable for 30 minutes")
        time.sleep(30)

print(f"Creating or loading {PROJECT_NAME!r} makes it current, closing the open project.", flush=True)
project_names = call(manager.GetProjectListInCurrentFolder)
if PROJECT_NAME in project_names:
    project = call(manager.LoadProject, PROJECT_NAME)
else:
    project = call(manager.CreateProject, PROJECT_NAME)
if not project:
    raise RuntimeError(f"Could not create or load {PROJECT_NAME!r}")
expected_project = PROJECT_NAME
if call(project.GetTimelineCount):
    raise RuntimeError(f"Refusing to change {PROJECT_NAME!r}: it already has timelines")

settings = dict(COLOUR_SETTINGS,
                timelineResolutionWidth=str(edit["format"]["width"]),
                timelineResolutionHeight=str(edit["format"]["height"]),
                timelineFrameRate=str(edit["format"]["fps"]),
                perfCacheClipsLocation=str(edit_folder.parent.parent / "Resolve Cache"))
for key, value in settings.items():
    if not call(project.SetSettings, {key: value}):
        raise RuntimeError(f"Could not set {key}={value!r}")
read_settings = call(project.GetSettings)
for key, value in settings.items():
    actual = read_settings[key]
    agrees = float(actual) == float(value) if key == "timelineFrameRate" else str(actual) == value
    if not agrees:
        raise RuntimeError(f"{key}: requested {value!r}, read back {actual!r}")

groups = {call(group.GetName): group for group in call(project.GetColorGroupsList)}
for camera in edit["media"]["cameras"].values():
    name = camera["colour_group"]
    if name not in groups:
        group = call(project.AddColorGroup, name)
        if not group or call(group.GetName) != name:
            raise RuntimeError(f"Could not create colour group {name!r}")
        groups[name] = group

media_pool = call(project.GetMediaPool)
root = call(media_pool.GetRootFolder)
source = next((folder for folder in call(root.GetSubFolderList)
               if call(folder.GetName) == "Source"), None)
if source is None:
    source = call(media_pool.AddSubFolder, root, "Source")
if not source or not call(media_pool.SetCurrentFolder, source):
    raise RuntimeError("Could not select the Source bin")
existing_media = {call(item.GetClipProperty, "File Path"): item for item in call(source.GetClipList)}
imported_media = []
for name, media in [*edit["media"]["cameras"].items(), ("lav", edit["media"]["lav"])]:
    path = str((edit_folder / media["file"]).resolve())
    item = existing_media.get(path)
    if item is None:
        imported = call(media_pool.ImportMedia, [path])
        if not imported or len(imported) != 1:
            raise RuntimeError(f"Could not import {path!r}")
        item = imported[0]
        existing_media[path] = item
    if name != "lav":
        if not call(item.SetClipProperty, "Input Color Space", media["log"]):
            raise RuntimeError(f"Could not set {name}'s input colour space")
        if call(item.GetClipProperty, "Input Color Space") != media["log"]:
            raise RuntimeError(f"Input colour space readback failed for {name}")
    imported_media.append({"name": name, "file": call(item.GetClipProperty, "File Path"),
                           "input_colour_space": call(item.GetClipProperty, "Input Color Space")})
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "b"))
import multicam
camera_files = [Path(row["file"]) for row in imported_media if row["name"] != "lav"]
existing = [item for item in call(source.GetClipList) if call(item.GetName) == "cameras"]
if not existing:
    call(media_pool.SetCurrentFolder, source)
    cameras = call(multicam.make_from_files, resolve, project, camera_files, "cameras")
else:
    cameras = {"multicam": "cameras", "angles": call(multicam.read_angles, resolve, project, existing[0])}
read_settings = call(project.GetSettings)
# timelinePlaybackFrameRate cannot be set by script (SetSetting returned False for "25", "25.0" and 25, run 3); it
# changes viewer playback only, renders use timelineFrameRate. Reported, not a reason to leave the project unsaved.
playback_rate_differs = float(read_settings["timelinePlaybackFrameRate"]) != float(read_settings["timelineFrameRate"])
if not call(manager.SaveProject):
    raise RuntimeError(f"Could not save {PROJECT_NAME!r}")
result = {"project": call(project.GetName), "settings": {key: read_settings[key] for key in [*settings, "timelinePlaybackFrameRate"]},
          "colour_groups": [call(group.GetName) for group in call(project.GetColorGroupsList)],
          "media": imported_media, "cameras_multicam": cameras, "source_bin_items": len(call(source.GetClipList)), "saved": True}
if playback_rate_differs:
    result["playback_frame_rate_differs"] = (f"viewer plays at {read_settings['timelinePlaybackFrameRate']} fps, the timeline runs at "
                                             f"{read_settings['timelineFrameRate']} (no script can set it); viewer playback only, renders are unaffected")
print(json.dumps(result, indent=2))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

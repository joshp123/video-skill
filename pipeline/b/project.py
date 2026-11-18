"""Make the edit list's Resolve project, ready to place into: one command, run once per video.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2, from pipeline/resolve/create_project.py.

project.py EDIT_LIST

Creates the project the list names (`resolve_project`) with its project media location, render cache and gallery on the
media drive, colour management as the look needs it (DaVinci YRGB Color Managed, DaVinci Wide Gamut / Intermediate,
Rec.709 Gamma 2.4 out, DaVinci DRTs, inverse DRT on, scale to crop), the list's resolution and frame rate, one colour
group per camera, the cameras and the lav imported into a "Source" bin with each camera's input colour space (`log` in
`cameras`), and the cameras' multicam `multicam` synced by their sound. Every setting is read back. An existing
project of that name is opened and only what is missing is added; one that already holds timelines is left alone.
Prints the multicam's angles (each camera file's offset in multicam frames), which place.py reads itself.
"""
import argparse
import json
from pathlib import Path

import multicam
import session

COLOUR = {"colorScienceMode": "davinciYRGBColorManagedv2", "colorSpaceTimeline": "DaVinci WG/Intermediate",
          "colorSpaceOutput": "Rec.709 Gamma 2.4", "inputDRT": "DaVinci", "outputDRT": "DaVinci",
          "timelineInputResMismatchBehavior": "scaleToCrop", "useInverseDRT": "1"}


def media_in(folder):
    return {item.GetClipProperty("File Path"): item for item in folder.GetClipList() or []}


def run(list_path):
    data = json.loads(list_path.read_text())
    folder = list_path.parent
    name = data["resolve_project"]
    resolve = session.start()
    manager = resolve.GetProjectManager()
    current = manager.GetCurrentProject()
    if current and current.GetName() == name:
        project = current
    elif name in (manager.GetProjectListInCurrentFolder() or []):
        resolve, project = session.connect(name)
    else:
        if current and current.GetName() != session.UNNAMED:
            session.save(resolve)
        location = session.MEDIA / "Resolve Project Media" / name
        location.mkdir(parents=True, exist_ok=True)
        project = manager.CreateProject(name, str(location))
        session.no_dialogs("CreateProject")
        if not project:
            raise RuntimeError(f"CreateProject({name!r}) failed")
    if project.GetTimelineCount():
        raise RuntimeError(f"{name!r} already holds timelines; project.py only prepares a new project")
    settings = dict(COLOUR, timelineResolutionWidth=str(data["format"]["width"]),
                    timelineResolutionHeight=str(data["format"]["height"]), timelineFrameRate=str(data["fps"]),
                    perfCacheClipsLocation=str(session.MEDIA / "Resolve Cache"),
                    colorGalleryStillsLocation=str(session.MEDIA / "Resolve Project Media" / name / "Gallery"))
    Path(settings["colorGalleryStillsLocation"]).mkdir(parents=True, exist_ok=True)
    for key, value in settings.items():
        if not project.SetSettings({key: value}):
            raise RuntimeError(f"Could not set {key}={value!r}")
    read = project.GetSettings()
    wrong = {key: read.get(key) for key, value in settings.items()
             if (float(read.get(key)) != float(value) if key == "timelineFrameRate" else str(read.get(key)) != value)}
    if wrong:
        raise RuntimeError(f"Settings read back differently: {wrong}")
    groups = {group.GetName() for group in project.GetColorGroupsList() or []}
    for camera in data["cameras"].values():
        if camera["group"] not in groups:
            if not project.AddColorGroup(camera["group"]):
                raise RuntimeError(f"Could not add colour group {camera['group']!r}")
            groups.add(camera["group"])
    pool = project.GetMediaPool()
    root = pool.GetRootFolder()
    source = next((f for f in root.GetSubFolderList() or [] if f.GetName() == "Source"), None) or pool.AddSubFolder(root, "Source")
    pool.SetCurrentFolder(source)
    media = media_in(source)
    imported = {}
    files = {key: (folder / camera["file"]).resolve() for key, camera in data["cameras"].items()}
    files["lav"] = (folder / data["sound"]["lav"]).resolve()
    for key, path in files.items():
        if str(path) not in media:
            item = (pool.ImportMedia([str(path)]) or [None])[0]
            if item is None:
                raise RuntimeError(f"Could not import {path}")
            media[str(path)] = item
        item = media[str(path)]
        if key != "lav":
            log = data["cameras"][key]["log"]
            if item.GetClipProperty("Input Color Space") != log and not item.SetClipProperty("Input Color Space", log):
                raise RuntimeError(f"Could not set {key}'s input colour space to {log!r}")
            if item.GetClipProperty("Input Color Space") != log:
                raise RuntimeError(f"{key}'s input colour space reads {item.GetClipProperty('Input Color Space')!r}")
        imported[key] = {"file": str(path), "input_colour_space": item.GetClipProperty("Input Color Space")}
    existing = [item for item in source.GetClipList() or [] if item.GetName() == data["multicam"]]
    if existing:
        cameras = {"multicam": data["multicam"], "angles": multicam.read_angles(resolve, project, existing[0])}
    else:
        cameras = multicam.make_from_files(resolve, project, [files[key] for key in data["cameras"]], data["multicam"])
    session.save(resolve)
    return {"project": name, "settings": {key: read[key] for key in settings}, "colour_groups": sorted(groups),
            "media": imported, "multicam": cameras}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_list", type=Path)
    args = parser.parse_args()
    session.main(lambda: run(args.edit_list.resolve()))

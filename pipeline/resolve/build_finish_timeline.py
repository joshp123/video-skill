"""Build a new finishing timeline from the cut list and transparent graphics clips.

Written by AI on 2026-10-21 by GPT-6.1 Sol; originally by Claude Opus 5.5. Edited the same day by Claude Fable 5.1:
one project-level colour-group lookup, the frame-rate and colour-management checks, and errors for a missing clip or dialogue.
Run through Resolve MCP with resolve, EDIT_FOLDER, TIMELINE_NAME and GRAPHICS_DIR; NATIVE_MANIFEST optional
(default build/graphics-native/manifest.json: graphics built in Resolve as their own timelines, placed above the cameras).
DIALOGUE_FILE optionally selects a version's dialogue (default build/dialogue.wav).
Existing timeline names are refused. Camera grades are read directly from edit/edit.json and applied to clip node 1.
CAMERAS_ONLY / --cameras-only builds cameras and dialogue without requiring graphic manifests; panel framing is retained.
Written by AI on 2026-10-22 by GPT-6.1 Sol: dialogue pieces follow audio-segment boundaries, including the lead-in.
22 Oct, Claude Fable 5.1: each camera's primaries grade (`media.cameras.<name>.grade`) is applied to its clips (grade_cameras.py).
"""
import json
import os
import sys
import time
from pathlib import Path

def cdl_from_grade(grade):
    """The ASC CDL dict Resolve takes, from the edit data's grade (slope, offset, power as [r, g, b], saturation)."""
    def triple(key):
        v = grade.get(key, [0.0, 0.0, 0.0] if key == "offset" else [1.0, 1.0, 1.0])
        return " ".join(f"{float(x):.6g}" for x in v)
    return {"NodeIndex": "1", "Slope": triple("slope"), "Offset": triple("offset"), "Power": triple("power"),
            "Saturation": f"{float(grade.get('saturation', 1.0)):.6g}"}


def panel_transform(framing, width, height, panel_rect, source_width, source_height):
    """The panel framing, expressed in the full portrait frame so his face sits in the panel rectangle."""
    _, top, _, panel_h = panel_rect
    full_scale = max(width / source_width, height / source_height)
    panel_scale = max(width / source_width, panel_h / source_height)
    f = framing
    zoom = f["zoom"] * panel_scale / full_scale
    # Same picture as the panel timeline, moved from the frame's centre to the panel's centre.
    tilt = f["tilt"] - ((top + panel_h / 2) - height / 2)
    # Crop the picture at the panel's bottom edge. CropBottom is in the clip's fitted pixels (before Zoom).
    fitted_bottom = height / 2 - tilt + source_height * full_scale / 2 * zoom
    crop = max(0.0, (fitted_bottom - (top + panel_h)) / zoom)
    return {"ZoomX": zoom, "ZoomY": zoom, "Pan": f["pan"] * panel_scale / full_scale, "Tilt": tilt, "CropBottom": crop}


def full_transform(framing, punch, height):
    f = framing
    zoom = f["zoom"] * punch
    tilt = (f.get("eye_y", height / 2) + f["tilt"] - height / 2) * punch + height / 2 - f.get("eye_y", height / 2)
    return {"ZoomX": zoom, "ZoomY": zoom, "Pan": f["pan"] * punch, "Tilt": tilt}


def folder(media_pool, name):
    root = media_pool.GetRootFolder()
    found = next((f for f in root.GetSubFolderList() if f.GetName() == name), None)
    return found or media_pool.AddSubFolder(root, name)


def append_dialogue_pieces(media_pool, timeline, dialogue, cut, call):
    start = call(timeline.GetStartFrame)
    boundaries = [0, *[segment["rec_in_frame"] for segment in cut["audio_clips"][1:]],
                  int(cut["duration_frames"])]
    placed = []
    for source_in, source_out in zip(boundaries, boundaries[1:]):
        audio = (call(media_pool.AppendToTimeline, [{"mediaPoolItem": dialogue,
                 "startFrame": source_in, "endFrame": source_out, "mediaType": 2,
                 "trackIndex": 1, "recordFrame": start + source_in}]) or [None])[0]
        if audio is None or int(call(audio.GetStart)) != start + source_in or int(call(audio.GetDuration)) != source_out - source_in:
            raise RuntimeError(f"Dialogue placement failed at frame {source_in}")
        placed.append({"dialogue": True, "track": 1, "record_frame": int(call(audio.GetStart)),
                       "source_frame": source_in, "frames": int(call(audio.GetDuration))})
    return placed


def run(resolve, edit_folder, timeline_name, graphics_dir, dialogue_file="build/dialogue.wav",
        native_manifest="build/graphics-native/manifest.json", cameras_only=False):
    root = Path(edit_folder)
    edit = json.loads((root / "edit/edit.json").read_text(encoding="utf-8"))
    cut = json.loads((root / "build/cutlist.json").read_text(encoding="utf-8"))
    manifest = [] if cameras_only else json.loads((root / graphics_dir / "manifest.json").read_text(encoding="utf-8"))
    def call(method, *args):
        deadline = time.monotonic() + 1800
        while resolve.GetProjectManager().GetCurrentProject().GetName() != edit["resolve_project"]:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Expected project {edit['resolve_project']!r} was unavailable for 30 minutes")
            time.sleep(30)
        return method(*args)
    fps, width, height = cut["fps"], cut["format"]["width"], cut["format"]["height"]
    project = resolve.GetProjectManager().GetCurrentProject()
    if project.GetName() != edit["resolve_project"]:
        raise RuntimeError(f"Open {edit['resolve_project']!r} first")
    for i in range(1, project.GetTimelineCount() + 1):
        if project.GetTimelineByIndex(i).GetName() == timeline_name:
            raise RuntimeError(f"Timeline {timeline_name!r} exists; pick a new name")
    media_pool = project.GetMediaPool()
    settings = project.GetSettings()
    if float(settings["timelineFrameRate"]) != float(fps):
        raise RuntimeError(f"The project runs at {settings['timelineFrameRate']} fps; the cut list is {fps} fps")
    if not str(settings["colorScienceMode"]).startswith("davinciYRGBColorManaged") or not str(settings["colorSpaceOutput"]).startswith("Rec.709"):
        raise RuntimeError(f"The project is not colour managed to Rec.709: {settings['colorScienceMode']}, {settings['colorSpaceOutput']}")

    folders = [media_pool.GetRootFolder()]
    by_path = {}
    while folders:
        current = folders.pop()
        folders.extend(current.GetSubFolderList())
        by_path.update({item.GetClipProperty("File Path"): item for item in current.GetClipList()})
    cameras, resolutions = {}, {}
    for name, meta in cut["media"]["cameras"].items():
        path = str((root / meta["file"]).resolve())
        item = by_path.get(path)
        if item is None:
            media_pool.SetCurrentFolder(folder(media_pool, "Cameras"))
            item = (media_pool.ImportMedia([path]) or [None])[0]
        if item is None:
            raise RuntimeError(f"Could not import camera {name}: {path}")
        if item.GetClipProperty("Input Color Space") != meta["log"] and (not item.SetClipProperty("Input Color Space", meta["log"]) or item.GetClipProperty("Input Color Space") != meta["log"]):
            raise RuntimeError(f"Could not set {name} input to {meta['log']}")
        cameras[name] = item
        resolutions[name] = tuple(int(value.strip()) for value in item.GetClipProperty("Resolution").split("x"))

    graphics_bin = folder(media_pool, "Graphics")
    media_pool.SetCurrentFolder(graphics_bin)
    have = {item.GetClipProperty("File Path"): item for item in graphics_bin.GetClipList()}
    # Two manifests: rendered clips (the terminal kinds, Remotion) and graphics built in Resolve as their own
    # timelines (build/graphics-native/manifest.json). A graphic may have both (a title over a terminal): the
    # rendered clip goes first so the native one lands above it.
    native_path = root / native_manifest
    native = json.loads(native_path.read_text(encoding="utf-8")) if not cameras_only and native_path.exists() else []
    by_id = {g["id"]: g for g in manifest}
    native_by_id = {g["id"]: g for g in native}
    missing = [graphic["id"] for graphic in cut["graphics"] if graphic["id"] not in by_id and graphic["id"] not in native_by_id]
    if missing and not cameras_only:
        raise RuntimeError(f"No rendered clip in {graphics_dir} and no built timeline in {native_manifest} for: {', '.join(missing)}")
    timelines_by_name = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i)
                         for i in range(1, project.GetTimelineCount() + 1)}
    wanted = []  # (manifest entry, media pool item), in cut-list order
    for graphic in ([] if cameras_only else cut["graphics"]):
        if graphic["id"] in by_id:
            g = by_id[graphic["id"]]
            path = str((root / graphics_dir / g["file"]).resolve())
            item = have.get(path) or (media_pool.ImportMedia([path]) or [None])[0]
            if item is None:
                raise RuntimeError(f"Could not import {path}")
            wanted.append((g, item))
        if graphic["id"] in native_by_id:
            g = native_by_id[graphic["id"]]
            built = timelines_by_name.get(g["timeline"])
            item = built.GetMediaPoolItem() if built else None
            if item is None:
                raise RuntimeError(f"No timeline named {g['timeline']!r} in the project for graphic {g['id']}")
            wanted.append((g, item))
    dialogue_path = str((root / dialogue_file).resolve())
    dialogue = by_path.get(dialogue_path) or have.get(dialogue_path) or (media_pool.ImportMedia([dialogue_path]) or [None])[0]
    if dialogue is None:
        raise RuntimeError(f"Could not import the dialogue: {dialogue_path}")

    # Colour groups belong to the project: GetColorGroupsList returned every group whichever timeline was current (21 Oct).
    existing_groups = {group.GetName(): group for group in (project.GetColorGroupsList() or [])}
    for name in {meta["colour_group"] for meta in cut["media"]["cameras"].values()}:
        if name not in existing_groups:
            group = project.AddColorGroup(name)
            if group is None:
                raise RuntimeError(f"Could not create colour group {name!r}")
            existing_groups[name] = group
    groups = {camera: existing_groups[meta["colour_group"]]
              for camera, meta in cut["media"]["cameras"].items()}
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    project.SetCurrentTimeline(timeline)
    timeline.SetSettings({"useCustomSettings": "1"})
    for key in ["colorScienceMode", "isAutoColorManage", "rcmPresetMode", "colorSpaceTimeline",
                "colorSpaceOutput", "inputDRT", "outputDRT", "disableFusionToneMapping",
                "timelineInputResMismatchBehavior"]:
        if not timeline.SetSettings({key: str(settings[key])}) or str(timeline.GetSettings()[key]) != str(settings[key]):
            raise RuntimeError(f"Could not inherit {key}")
    for key, value in [("timelineResolutionWidth", width), ("timelineResolutionHeight", height),
                       ("timelineOutputResolutionWidth", width), ("timelineOutputResolutionHeight", height),
                       ("useInverseDRT", 1)]:
        if not timeline.SetSettings({key: str(value)}) or str(timeline.GetSettings()[key]) != str(value):
            raise RuntimeError(f"Could not set {key}={value}")
    while timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
    start = timeline.GetStartFrame()

    panels = [(g["in_resolved"]["frame"], g["out_resolved"]["frame"], cut["layouts"][g["layout"]])
              for g in cut["graphics"] if "in_resolved" in g and "out_resolved" in g
              and cut["layouts"][g["layout"]].get("graphic") and cut["layouts"][g["layout"]].get("picture")]
    pieces = []
    for clip in cut["clips"]:
        a, b = clip["rec_in_frame"], clip["rec_in_frame"] + clip["frames"]
        edges = sorted({a, b, *[edge for lo, hi, layout in panels for edge in (lo, hi) if a < edge < b]})
        for lo, hi in zip(edges, edges[1:]):
            panel = next((layout for left, right, layout in reversed(panels) if left <= lo and hi <= right), None)
            pieces.append((clip, lo, hi, panel))
    placed = []
    for clip, lo, hi, panel in pieces:
        source_in = clip["camera_src_in_frame"] + (lo - clip["rec_in_frame"])
        item = (media_pool.AppendToTimeline([{"mediaPoolItem": cameras[clip["camera"]], "startFrame": source_in,
                "endFrame": source_in + (hi - lo), "mediaType": 1, "trackIndex": 1,
                "recordFrame": start + lo}]) or [None])[0]
        if item is None or int(item.GetStart()) != start + lo or int(item.GetDuration()) != hi - lo:
            raise RuntimeError(f"Camera placement failed at frame {lo}")
        camera = clip["camera"]
        metadata = cut["media"]["cameras"][camera]
        transform = (panel_transform(panel["framings"][clip.get("panel_framing") or camera], width, height,
                                     panel["picture"], *resolutions[camera]) if panel
                     else full_transform(metadata["framing"], clip.get("zoom", 1.0), height))
        transform = {"CropLeft": 0, "CropRight": 0, "CropTop": 0, "CropBottom": 0, **transform}
        if not item.SetProperties(transform):
            raise RuntimeError(f"Could not frame frame {lo}")
        if not item.AssignToColorGroup(groups[clip["camera"]]):
            raise RuntimeError(f"Could not assign frame {lo} to its camera's colour group")
        grade = edit["media"]["cameras"][camera].get("grade")
        if grade and not item.SetCDL(cdl_from_grade(grade)):
            raise RuntimeError(f"Could not grade frame {lo} ({camera})")
        placed.append({"track": 1, "record_frame": int(item.GetStart()), "frames": int(item.GetDuration()),
                       "source_frame": source_in, "camera": camera, "transform": transform,
                       "colour_group": metadata["colour_group"]})

    occupied = {}
    for g, media_item in wanted:
        lo, hi = g["timeline_in_frame"], g["timeline_in_frame"] + g["frames"]
        track = 2
        while any(left < hi and lo < right for left, right in occupied.get(track, [])):
            track += 1
        while timeline.GetTrackCount("video") < track:
            timeline.AddTrack("video")
        item = (media_pool.AppendToTimeline([{"mediaPoolItem": media_item, "startFrame": 0,
                "endFrame": g["frames"], "mediaType": 1, "trackIndex": track,
                "recordFrame": start + lo}]) or [None])[0]
        if item is None or int(item.GetStart()) != start + lo or int(item.GetDuration()) != g["frames"]:
            raise RuntimeError(f"Graphic {g['id']} placement failed")
        occupied.setdefault(track, []).append((lo, hi))
        placed.append({"id": g["id"], "track": track, "record_frame": int(item.GetStart()),
                       "frames": int(item.GetDuration())})

    placed.extend(append_dialogue_pieces(media_pool, timeline, dialogue, cut, call))

    resolve.GetProjectManager().SaveProject()
    return {"timeline": timeline_name, "end_frame": int(timeline.GetEndFrame()) - start,
            "expected": int(cut["duration_frames"]), "placed": placed}


if "resolve" in globals() and "EDIT_FOLDER" in globals():
    result = run(resolve, EDIT_FOLDER, TIMELINE_NAME, GRAPHICS_DIR,
                 globals().get("DIALOGUE_FILE", "build/dialogue.wav"),
                 globals().get("NATIVE_MANIFEST", "build/graphics-native/manifest.json"),
                 globals().get("CAMERAS_ONLY", False))
    print(json.dumps(result, indent=2))
elif __name__ == "__main__":
    import argparse
    import DaVinciResolveScript
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_folder")
    parser.add_argument("timeline_name")
    parser.add_argument("--graphics-dir", default="build/graphics-v1")
    parser.add_argument("--dialogue", default="build/dialogue.wav")
    parser.add_argument("--native-manifest", default="build/graphics-native/manifest.json")
    parser.add_argument("--cameras-only", action="store_true")
    args = parser.parse_args()
    result = run(DaVinciResolveScript.scriptapp("Resolve"), args.edit_folder, args.timeline_name,
                 args.graphics_dir, args.dialogue, args.native_manifest, args.cameras_only)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

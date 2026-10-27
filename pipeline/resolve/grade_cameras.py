"""Apply each camera's primaries grade from the edit data to its clips on a timeline, by script, no LUT.

Written by AI on 2026-10-22 by Claude Fable 5.1, after Josh: "why does it need screen try harder to find equally
good headless way (no LUT bullshit must match darren approach)".
Run through Resolve MCP or external scripting with resolve, EDIT_FOLDER and TIMELINE_NAME, or from a shell:
grade_cameras.py EDIT_FOLDER TIMELINE_NAME.

The grade is an ASC CDL per camera in edit/edit.json, `media.cameras.<name>.grade`:
  {"slope": [r, g, b], "offset": [r, g, b], "power": [r, g, b], "saturation": s}
slope is gain, offset is lift, power is gamma (1.0 each means no change), saturation 1.0 means no change. The
colourist decides the values by looking at frames of both cameras at the same moment (SKILL.md, roles/colour.md);
this script only applies them: TimelineItem.SetCDL on node 1 of every video clip whose media file is that
camera's file. Cameras without a grade are left alone. Resolve 21.1's scripting cannot put a grade on a colour
group's graph (Graph.ApplyGradeFromDRX returns False on group graphs, tested 22 Oct) and cannot add nodes, so the
grade lives on the clips, from the data, and the timeline builder applies it on every build.
"""
import json
import sys
import os
from pathlib import Path


def timeline_named(project, name):
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t.GetName() == name:
            return t
    return None


def cdl_from_grade(grade):
    def triple(key):
        v = grade.get(key, [1.0, 1.0, 1.0] if key != "offset" else [0.0, 0.0, 0.0])
        assert len(v) == 3, (key, v)
        return " ".join(f"{float(x):.6g}" for x in v)
    return {"NodeIndex": "1", "Slope": triple("slope"), "Offset": triple("offset"), "Power": triple("power"),
            "Saturation": f"{float(grade.get('saturation', 1.0)):.6g}"}


def apply_grades(timeline, cameras, edit_folder):
    """cameras: edit.json's media.cameras. Returns per camera the clips graded, and the unmatched clips."""
    by_path = {}
    for name, camera in cameras.items():
        if camera.get("grade"):
            by_path[os.path.realpath(str((Path(edit_folder) / camera["file"]).resolve()))] = (name, cdl_from_grade(camera["grade"]))
    graded, unmatched = {}, []
    for index in range(1, timeline.GetTrackCount("video") + 1):
        for item in timeline.GetItemListInTrack("video", index) or []:
            media = item.GetMediaPoolItem()
            path = media and media.GetClipProperty("File Path")
            key = os.path.realpath(path) if path else None
            if key in by_path:
                name, cdl = by_path[key]
                if not item.SetCDL(cdl):
                    raise RuntimeError(f"SetCDL failed on {item.GetName()} at {item.GetStart()}")
                graded.setdefault(name, 0)
                graded[name] += 1
            elif index == 1:
                unmatched.append(item.GetName())
    return {"graded": graded, "cdl": {name: cdl for name, cdl in by_path.values()}, "v1_clips_without_grade": sorted(set(unmatched))}


def run(resolve, edit_folder, timeline_name):
    edit_folder = Path(edit_folder)
    edit = json.loads((edit_folder / "edit" / "edit.json").read_text())
    project = resolve.GetProjectManager().GetCurrentProject()
    if project.GetName() != edit["resolve_project"]:
        raise RuntimeError(f"open project is {project.GetName()!r}, the edit data says {edit['resolve_project']!r}")
    timeline = timeline_named(project, timeline_name)
    if timeline is None:
        raise RuntimeError(f"no timeline named {timeline_name!r}")
    result = apply_grades(timeline, edit["media"]["cameras"], edit_folder)
    resolve.GetProjectManager().SaveProject()
    result["timeline"] = timeline_name
    return result


if "resolve" in globals() and "EDIT_FOLDER" in globals():
    result = run(resolve, EDIT_FOLDER, TIMELINE_NAME)
    print(result)
elif __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_folder")
    parser.add_argument("timeline_name")
    args = parser.parse_args()
    import DaVinciResolveScript
    print(run(DaVinciResolveScript.scriptapp("Resolve"), args.edit_folder, args.timeline_name))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

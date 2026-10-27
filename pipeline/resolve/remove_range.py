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
    parser.add_argument("in_frame", type=int)
    parser.add_argument("out_frame", type=int)
    args = parser.parse_args()
    EDIT_FOLDER = args.edit_folder
    TIMELINE_NAME, IN_FRAME, OUT_FRAME = args.timeline_name, args.in_frame, args.out_frame

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

tl = next(t for i in range(1,call(project.GetTimelineCount)+1) if call((t:=call(project.GetTimelineByIndex,i)).GetName) == TIMELINE_NAME)
start = call(tl.GetStartFrame)
inside, straddles = [], []
for kind in ("video", "audio", "subtitle"):
    for track in range(1,call(tl.GetTrackCount,kind)+1):
        for item in call(tl.GetItemListInTrack,kind,track) or []:
            a,b = call(item.GetStart)-start,call(item.GetEnd)-start
            if a < OUT_FRAME and b > IN_FRAME:
                if IN_FRAME <= a and b <= OUT_FRAME:
                    inside.append(item)
                else:
                    straddles.append({"track":f"{kind}{track}","name":call(item.GetName),"start_frame":a,"end_frame":b})
if straddles:
    result = {"removed":False,"straddles":straddles}
else:
    result = {"removed":call(tl.DeleteClips,inside,True),"items":len(inside),"frames":OUT_FRAME-IN_FRAME}
    if result["removed"]:
        audio = call(tl.GetItemListInTrack,"audio",1) or []
        join_fades = []
        for edge, fade in (("end","FadeOut"),("start","FadeIn")):
            neighbours = [item for item in audio if call(item.GetEnd if edge == "end" else item.GetStart)-start == IN_FRAME]
            if len(neighbours) != 1:
                raise RuntimeError(f"Expected one A1 piece whose {edge} is at the join {IN_FRAME}; found {len(neighbours)}")
            item = neighbours[0]
            before = call(item.GetFades)
            requested = {**before,fade:1}
            if not call(item.SetFades,requested):
                raise RuntimeError(f"Could not set {fade} at the join")
            after = call(item.GetFades)
            if after.get(fade) != 1:
                raise RuntimeError(f"{fade} readback differs: {after}")
            join_fades.append({"edge":edge,"record_start":call(item.GetStart)-start,
                               "record_end":call(item.GetEnd)-start,"before":before,"after":after})
        result["join_frame"] = IN_FRAME
        result["join_fades"] = join_fades
print(json.dumps(result,indent=2))

if __name__ == "__main__":
    sys.stdout.flush()
    os._exit(0)

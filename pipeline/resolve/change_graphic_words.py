#!/usr/bin/env python3
"""Change the words of one native graphic in place, without rebuilding it: re-reads words.md (a closing page's slots
and a title's slot), lays the graphic out again and sets the Text+ and box inputs of its composition, in the timeline
build/graphics-native/manifest.json names; the manifest then records which words each slot shows. A cut list built
from another edit.json is refused.

Written by AI on 2026-10-22 by Claude Opus 5.5, from the native graphics test's change_words.py.
Run from a shell: change_graphic_words.py EDIT_FOLDER GRAPHIC_ID. Through the Resolve MCP: resolve, EDIT_FOLDER and
GRAPHIC_ID in the namespace. The project the edit data names must be open. A title whose parts or pills change in
number needs a rebuild (build_graphics.py).
A title's band opacity is also re-applied from the cut list's content.title.band; rebuild the cut list after changing it in edit.json.
"""
import json
import os
import sys
from pathlib import Path


def change(resolve, edit_folder, graphic_id):
    edit_folder = Path(edit_folder).resolve()
    sys.path.insert(0, str(edit_folder.parent / "pipeline/resolve"))  # build_graphics.py, also through the MCP
    import build_graphics
    edit, cut = build_graphics.read_edit(edit_folder)
    look = json.loads((edit_folder.parent / "looks" / edit["look"] / "look.json").read_text())
    manifest_path = edit_folder / "build/graphics-native/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entry = next(entry for entry in manifest if entry["id"] == graphic_id)
    graphic = next(graphic for graphic in cut["graphics"] if graphic["id"] == graphic_id)
    title = graphic["content"].get("title")
    width, height = cut["format"]["width"], cut["format"]["height"]
    units = build_graphics.FusionUnits(look, width, height)
    markdown = (edit_folder / "words.md").read_text()
    inputs = {}
    if graphic["kind"] == "closing":
        words = {}
        for field, heading in graphic["content"]["slots"].items():
            words[field], entry["slots"][field] = build_graphics.slot_words(markdown, heading)
        inputs.update(build_graphics.closing_inputs(units, build_graphics.closing_layout(words, look, width), words))
    if title:
        title_words, entry["slots"]["title"] = build_graphics.slot_words(markdown, title["slot"])
        layout = build_graphics.title_layout(title, title_words, look, width)
        inputs.update(build_graphics.title_inputs(units, layout, title))

    project = resolve.GetProjectManager().GetCurrentProject()
    if project.GetName() != edit["resolve_project"]:
        raise RuntimeError(f"Open {edit['resolve_project']!r} first")
    timeline = next(project.GetTimelineByIndex(index) for index in range(1, project.GetTimelineCount() + 1)
                    if project.GetTimelineByIndex(index).GetName() == entry["timeline"])
    comp = timeline.GetItemListInTrack("video", 1)[0].GetFusionCompByIndex(1)
    tools = {name: comp.FindTool(name) for name in inputs}
    missing = [name for name, tool in tools.items() if tool is None]
    if title and comp.FindTool(f"Part{len(layout['parts'])}"):
        missing.append(f"no Part{len(layout['parts'])}")
    if missing:
        raise RuntimeError(f"{entry['timeline']} does not fit the new words ({', '.join(missing)}): rebuild it with build_graphics.py")
    comp.Lock()
    for name, values in inputs.items():
        for key, value in values.items():
            tools[name].SetInput(key, value)
    comp.Unlock()
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    return {"timeline": entry["timeline"], "inputs_set": sum(len(values) for values in inputs.values()),
            "slots": entry["slots"]}


if __name__ == "__main__" or "EDIT_FOLDER" in globals():
    if "EDIT_FOLDER" not in globals():
        import argparse
        parser = argparse.ArgumentParser(description="Change one native graphic's words in place.")
        parser.add_argument("edit_folder", type=Path)
        parser.add_argument("graphic_id")
        arguments = parser.parse_args()
        EDIT_FOLDER, GRAPHIC_ID = arguments.edit_folder, arguments.graphic_id
    if "resolve" not in globals():
        import DaVinciResolveScript
        resolve = DaVinciResolveScript.scriptapp("Resolve")
    result = change(resolve, EDIT_FOLDER, GRAPHIC_ID)
    print(json.dumps(result, indent=1))
    if __name__ == "__main__":
        sys.stdout.flush()
        os._exit(0)

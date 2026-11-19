#!/usr/bin/env python3
"""The look's Fusion templates as title items on a timeline: place them, set their inputs, read them back.

Written by AI on 2026-10-25 by Claude Opus 5.5. Rewritten on 2026-10-26 by Claude Opus 5.5 (hill-climb stream I) from
stream H's proven route: a graphic is a title item on V4 with the template's composition and its inputs set on the
item; there is no timeline per graphic.

A library for build.py and edit.py; it has no command of its own.

A title row is {template, inputs, record, frames}. `template` names pipeline/b/templates/<look>/<template>.setting; each
input is set on the template's published control of that name. A text input whose template control is a character
style (the title's Title) takes [[ ]] around the words the look highlights (the pill; they never break across lines)
and a newline where a line must break; Text+ wraps the rest. Points are [x, y] in Fusion's units (0 to 1, y up); a
photo path is relative to the edit list. Nothing here lays anything out: the template and Text+ do.

Placing (place_titles): each title is inserted past the timeline's end and moved onto its track (17 Nov, 21.2).
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
sys.path.insert(0, str(HERE))
STYLE_ENABLED = 2000  # Fusion's character-style property for "shading element on", indexed by element - 1
import session  # noqa: E402
STAGING = session.CACHE / "pipeline-b/graphic"
FUSION_OWN_CONTROLS = {"Comments", "CommentsNest", "HideInputs"}  # on every tool, macros included; never a template's input


def lua_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def highlight_elements(tool):
    """The template's highlight, from the styled tool's Comments ("Highlight 4=1 3=0": shading element 4 on, 3 off)."""
    return dict(pair.split("=") for pair in re.findall(r"\d+=\d", tool.GetInput("Comments") or ""))


def set_styled_text(tool, marked):
    """Set a character-styled text: the words in [[ ]] get the template's highlight, the rest the opposite. Fusion's
    API cannot set a character style, so the style goes in through LoadSettings from a file."""
    comments = tool.GetInput("Comments") or ""
    highlight = highlight_elements(tool)
    plain, marked_ranges = "", []
    for index, part in enumerate(re.split(r"\[\[(.+?)\]\]", marked)):
        if index % 2:
            part = part.replace(" ", "\u00a0")
            marked_ranges.append((len(plain), len(plain) + len(part) - 1))
        plain += part
    styles = []
    for element, value in highlight.items():
        styles.append(f"{{ {STYLE_ENABLED}, 0, {len(plain)}, Index = {int(element) - 1}, Value = {1 - int(value)} }}")
        styles += [f"{{ {STYLE_ENABLED}, {first}, {last}, Index = {int(element) - 1}, Value = {int(value)} }}"
                   for first, last in marked_ranges]
    settings = (f'{{ Tools = ordered() {{ ["{tool.GetAttrs()["TOOLS_Name"]}"] = StyledTextCLS {{ Inputs = {{ Text = Input {{ '
                f'Value = StyledText {{ Array = {{ {", ".join(styles)} }}, Value = {lua_string(plain)} }} }} }} }} }} }}')
    with tempfile.NamedTemporaryFile("w", suffix=".setting", delete=False, encoding="utf-8") as file:
        file.write(settings)
    try:
        if not tool.LoadSettings(file.name):
            raise RuntimeError(f"Fusion refused the styled text for {tool.GetAttrs()['TOOLS_Name']}")
        tool.SetInput("Comments", comments)  # LoadSettings resets the inputs the file leaves out
    finally:
        os.unlink(file.name)


def styled_text(tool):
    """The styled text read back in the list's terms: [[ ]] round each range that carries the highlight."""
    STAGING.mkdir(parents=True, exist_ok=True)
    path = STAGING / "styled-text.setting"
    if not tool.SaveSettings(str(path)):
        raise RuntimeError(f"Fusion would not save {tool.GetAttrs()['TOOLS_Name']}")
    saved = path.read_text(encoding="utf-8")
    path.unlink()
    plain = tool.GetInput("Text")
    element, value = next(iter(highlight_elements(tool).items()))
    ranges = sorted((int(first), int(last)) for first, last in re.findall(
        rf"\{{\s*{STYLE_ENABLED},\s*(\d+),\s*(\d+),\s*Index = {int(element) - 1},\s*Value = {int(value)}\s*\}}", saved))
    marked, cursor = "", 0
    for first, last in ranges:
        marked += plain[cursor:first] + "[[" + plain[first:last + 1].replace("\u00a0", " ") + "]]"
        cursor = last + 1
    return marked + plain[cursor:]


def input_value(value, base, staging):
    """A point as Fusion's {1: x, 2: y}; a photo path made absolute, copied under staging when its name ends in a digit
    (a Loader reads such a file as one frame of an image sequence)."""
    if isinstance(value, list):
        return {1: value[0], 2: value[1]}
    if isinstance(value, str) and (base / value).is_file():
        path = (base / value).resolve()
        if re.search(r"\d$", path.stem):
            staging.mkdir(parents=True, exist_ok=True)
            path = Path(shutil.copyfile(path, staging / f"{path.stem} photo{path.suffix}"))
        return str(path)
    return value


def macro_of(comp):
    return next(tool for tool in comp.GetToolList(False).values() if tool.GetAttrs()["TOOLS_RegID"] == "MacroOperator")


def apply_inputs(comp, inputs, frames, base):
    """Set a template composition's published inputs, its frame range and its output."""
    macro = macro_of(comp)
    published = {each.GetAttrs()["INPS_ID"] for each in macro.GetInputList().values()} | {
        each.GetAttrs()["INPS_Name"] for each in macro.GetInputList().values()}
    for key, value in inputs.items():
        tool = comp.FindTool(key)
        if tool and tool.GetAttrs()["TOOLS_RegID"] == "StyledTextCLS":
            set_styled_text(tool, value)
            continue
        if key not in published:
            raise KeyError(f"{macro.GetAttrs()['TOOLS_Name']} has no input {key!r}")
        macro.SetInput(key, input_value(value, base, STAGING / "photos"))
    comp.SetAttrs({"COMPN_GlobalStart": 0, "COMPN_GlobalEnd": frames - 1, "COMPN_RenderStart": 0,
                   "COMPN_RenderEnd": frames - 1})
    media_out = comp.AddTool("MediaOut", -32768, -32768)
    media_out.ConnectInput("Input", macro)  # after the comp is unlocked, or the render skips it (tools/resolve.md)


def read_title(item):
    """A title item in the list's terms: its template (the macro's name, which is the template's without spaces) and
    every published input, the styled text with its [[ ]] ranges."""
    comp = item.GetFusionCompByIndex(1)
    macro = macro_of(comp)
    inputs = {}
    for each in macro.GetInputList().values():
        key = each.GetAttrs()["INPS_ID"]
        if key in FUSION_OWN_CONTROLS:
            continue
        tool = comp.FindTool(key)
        if tool and tool.GetAttrs()["TOOLS_RegID"] == "StyledTextCLS":
            inputs[key] = styled_text(tool)
            continue
        value = macro.GetInput(key)
        inputs[key] = [value[1], value[2]] if isinstance(value, dict) else value
    return {"template": macro.GetAttrs()["TOOLS_Name"], "inputs": inputs, "compositions": item.GetFusionCompCount()}


def fusion_tool_name(template):
    """Fusion names a macro after its template without the spaces ("Signpost Title" is SignpostTitle)."""
    return template.replace(" ", "")


def timecode(frame, fps):
    """A non-drop-frame timecode for an absolute frame."""
    seconds, frames = divmod(frame, fps)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours % 24:02}:{minutes:02}:{seconds:02}:{frames:02}"


def place_titles(resolve, project, timeline, track, titles, templates, base, empty_track=True):
    """Insert every title row on video TRACK (empty) of TIMELINE, the current timeline, with its inputs set.
    `InsertFusionTitleIntoTimeline` inserts at the playhead between the marks, as a ripple insert; at the timeline's end
    there is nothing to ripple. So each title is inserted past the end, exactly its length (the marks), and moved onto
    TRACK at its record frame with SetPosition (tested 17 Nov on 21.2: exact lengths, nothing else moved)."""
    start, fps = timeline.GetStartFrame(), float(timeline.GetSettings()["timelineFrameRate"])
    while timeline.GetTrackCount("video") < track:
        timeline.AddTrack("video")
    if empty_track and timeline.GetItemListInTrack("video", track):
        raise ValueError(f"V{track} must be empty for the titles")
    resolve.OpenPage("edit")
    placed = []
    for row in sorted(titles, key=lambda row: row["record"]):
        where = f"title at {row['record']}"
        end = timeline.GetEndFrame()
        if (not timeline.SetMarkInOut(end - start, end - start + row["frames"] - 1)
                or not timeline.SetCurrentTimecode(timecode(end, round(fps)))):
            raise RuntimeError(f"Could not set the marks for the {where}")
        item = timeline.InsertFusionTitleIntoTimeline("Text+")
        timeline.ClearMarkInOut("all")
        if item is None or item.GetDuration() != row["frames"]:
            raise RuntimeError(f"InsertFusionTitleIntoTimeline did not make the {where} {row['frames']} frames long")
        if (not item.SetPosition({"trackIndex": track, "startFrame": start + row["record"]})
                or item.GetTrackTypeAndIndex() != ["video", track] or item.GetStart() - start != row["record"]):
            raise RuntimeError(f"Could not move the {where} onto V{track}")
        template = templates / f"{row['template']}.setting"
        comp = item.ImportFusionComp(str(template)) if template.is_file() else None
        if comp is None or item.GetFusionCompCount() != 1:
            raise RuntimeError(f"Could not load {template} as the {where}'s only composition")
        apply_inputs(comp, row["inputs"], row["frames"], base)
        placed.append(item)
    return placed

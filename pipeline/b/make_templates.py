#!/usr/bin/env python3
"""Make a look's Fusion title templates: one .setting per graphic kind (title, photo card, closing page), each a macro
whose published inputs are every word, photo path, place and size an editor changes, with the look's type, colours and
safe area baked in and the colour node at the end (Rec.709 in, so colours come out as typed). Text+ lays out and wraps
its own words; the title's pill is a Text+ border on the words a character style switches on (graphic.py sets it).

Written by AI on 2026-10-25 by Claude Opus 5.5.
Run once per look, with a project open: make_templates.py LOOK_FOLDER [NAME...]. The graphs are template_kinds.py's.
Builds each graph in a scratch timeline
"b graphic template <kind>", saves its tools as a macro into pipeline/b/templates/<look>/<Name>.setting through
Fusion's own writer (bmd.writefile), then deletes the scratch timeline. Install nothing: graphic.py loads the files.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "resolve"))
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
import build_graphics as bg  # noqa: E402  the proven Fusion units, Text+ calibration and timeline settings

WIDTH, HEIGHT = 1080, 1920
# Text+ shading-element units, measured on 25 Oct against a render (Futura Bold 78 px): an Extend of 0.1 grows a border
# by 13 px a side at Size 0.11749, so one unit is 1.667 em of the text's type.
EM_PER_EXTEND = 1.667
# Text+'s bare border (Extend 0) runs 0.26 em beyond the pen at each side and from the face's ascent above the first
# baseline to its descent below the last; its Offset is in frame widths (0.042 moved it 45 px), measured the same day.
BARE_SIDE_EM = 0.279
SOFTNESS_PX_PER_UNIT = 0.78  # Softness 34.7 gave a 10-90% edge of 75 px; a 120 px linear ramp's is 96 px


def element_inputs(n, css, level, priority, **more):
    red, green, blue, alpha = bg.colour(css)
    return {f"Enabled{n}": 1, f"ElementShape{n}": 2, f"Level{n}": level, f"PriorityBack{n}": priority,
            f"Red{n}": red, f"Green{n}": green, f"Blue{n}": blue, f"Alpha{n}": alpha,
            **{f"{key}{n}": value for key, value in more.items()}}


class Template(bg.Graph):
    """One template's graph, in its own scratch timeline; publish() saves it as a macro."""

    def __init__(self, project, pool, look, look_folder, kind):
        self.project, self.pool, self.kind = project, pool, kind
        self.timeline_name = f"b graphic template {kind}"
        stale = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetName() == self.timeline_name]
        pool.DeleteTimelines(stale)  # a scratch timeline an interrupted run left behind
        item = bg.graphic_timeline(project, pool, self.timeline_name, WIDTH, HEIGHT, 2500)  # tools keep this as their range
        super().__init__(item, look, look_folder, WIDTH, HEIGHT, 100000)
        self.names, self.published = [], []

    def add(self, regid, name=None, **inputs):
        tool = super().add(regid, name, **inputs)
        self.names.append(tool.GetAttrs()["TOOLS_Name"])
        return tool

    def text(self, name, face_name, px, css, shadow=None, **inputs):
        """A Text+ in the look's face, its outline and shadow following its Size when an editor changes it."""
        tool = self.add("TextPlus", name, LayoutType=1, Wrap=1, LayoutHeight=self.fusion["textBoxHeight"] / HEIGHT,
                        **self.text_inputs(face_name, px, css, shadow))
        self.set(tool, **inputs)
        tool.Thickness2.SetExpression(f"{self.fusion['strokePx'] / self.fusion['strokePxPerThickness']}/Size")
        if shadow:
            size, offset = tool.GetInput("Size"), tool.GetInput("Offset3")
            tool.Offset3.SetExpression(f"Point({offset[1] * size}/Size, {offset[2] * size}/Size)")
        return tool

    def border(self, tool, n, css, level, priority, sides_em, top_em, bottom_em, round_=0, face_name="Futura Bold",
               right_em=0, **more):
        """Shading element n of a Text+ as a box behind its words: sides_em beyond the pen each side, top_em above
        the first baseline, bottom_em below the last, in ems of its type; moved right_em to the right."""
        face, size = bg.face_of(self.look, face_name), tool.GetInput("Size")
        px = size * 100 / face["textSizePer100Px"]
        grow = (top_em + bottom_em - face["ascentEm"] - face["descentEm"]) / 2
        shift = (face["ascentEm"] - face["descentEm"] - top_em + bottom_em) / 2  # down, in ems
        self.set(tool, **element_inputs(n, css, level, priority, Round=round_, ExtendVertical=grow / EM_PER_EXTEND,
                                        ExtendHorizontal=(sides_em - BARE_SIDE_EM) / EM_PER_EXTEND, **more))
        # The box keeps its place on the words at any Size.
        tool[f"Offset{n}"].SetExpression(f"Point({right_em * px / WIDTH / size}*Size, {-shift * px / WIDTH / size}*Size)")

    def photo(self, name):
        """A photo filling the frame (centred, cropped), from Display P3 when PhotoIsDisplayP3 is 1."""
        loader = self.add("Loader", name, Clip=str(HERE / "templates/no photo.png"),
                          Depth=bg.LOADER_FLOAT32, HoldLastFrame=100000)
        cover = self.add("Letterbox", f"{name}Cover", Mode=1)
        self.link(cover, "Input", loader)
        p3 = self.add("ColorSpaceTransform", f"{name}FromP3", Blend=0, **self.fusion["photoColourNodes"]["Display P3"])
        self.link(p3, "Input", cover)
        last = self.add("BrightnessContrast", f"{name}Clip", ClipBlack=1, ClipWhite=1)
        self.link(last, "Input", p3)
        self.published += [(name, name, "Clip"), ("PhotoIsDisplayP3", f"{name}FromP3", "Blend")]
        return last

    def publish(self, last, name, inputs, out_folder):
        """The colour node after last, then every tool built here as one macro in out_folder/name.setting."""
        node = self.add("ColorSpaceTransform", "ColourNode", **self.fusion["colourNode"])
        self.link(node, "Input", last)
        self.comp.Unlock()
        path = out_folder / f"{name}.setting"
        path.unlink(missing_ok=True)
        published = ", ".join(f'{{ "{n}", "{op}", "{source}" }}' for n, op, source in self.published + inputs)
        self.comp.Execute(f'''
local list = {{}}
for _, n in ipairs({{ {", ".join(f'"{n}"' for n in self.names)} }}) do list[#list + 1] = comp:FindTool(n) end
local inputs = {{}}
for i, p in ipairs({{ {published} }}) do
  inputs[p[1]] = {{ __ctor = "InstanceInput", SourceOp = p[2], Source = p[3], Name = p[1], Page = "Controls" }}
end
local tools = comp:CopySettings(list).Tools
bmd.writefile([[{path}]], {{ Tools = {{ ["{name}"] = {{ __ctor = "MacroOperator", Inputs = inputs,
  Outputs = {{ MainOutput1 = {{ __ctor = "InstanceOutput", SourceOp = "ColourNode", Source = "Output" }} }},
  ViewInfo = {{ __ctor = "GroupInfo" }}, Tools = tools }} }} }})''')
        deadline = time.time() + 20  # Execute returns before Fusion has run the script
        while not (path.exists() and path.stat().st_size) and time.time() < deadline:
            time.sleep(0.25)
        time.sleep(0.5)
        path.write_text(f"-- {name}: made by pipeline/b/make_templates.py from {self.look_folder.name}/look.json "
                        f"(written by AI on 2026-10-25 by Claude Opus 5.5). Remake it rather than editing it.\n"
                        + path.read_text())  # fails here if Fusion wrote nothing
        self.pool.DeleteTimelines([self.project.GetCurrentTimeline()])
        return {"template": str(path), "inputs": [n for n, _, _ in self.published + inputs]}


def main():
    import DaVinciResolveScript
    from template_kinds import KINDS
    look_folder = Path(sys.argv[1]).resolve()
    only = sys.argv[2:] or list(KINDS)
    look = json.loads((look_folder / "look.json").read_text())
    out = HERE / "templates" / look_folder.name
    out.mkdir(parents=True, exist_ok=True)
    if not (HERE / "templates/no photo.png").exists():  # what a photo input shows until it is set: nothing
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black@0:s=2x2,format=rgba",
                        "-frames:v", "1", str(HERE / "templates/no photo.png")], check=True)
    resolve = DaVinciResolveScript.scriptapp("Resolve")
    project = resolve.GetProjectManager().GetCurrentProject()
    pool = project.GetMediaPool()
    pool.SetCurrentFolder(bg.folder(pool, "b graphics"))
    previous = project.GetCurrentTimeline()
    made = []
    for name in only:
        t = Template(project, pool, look, look_folder, name.split()[-1].lower())
        last, inputs = KINDS[name](t, look)
        made.append(t.publish(last, name, inputs, out))
    if previous:
        project.SetCurrentTimeline(previous)
    print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)

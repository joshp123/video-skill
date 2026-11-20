"""Fusion unit conversions, font layout helpers, and Graph builder used by pipeline/b/make_templates.py and template_kinds.py."""
import math
import re
import subprocess
import warnings

LOADER_FLOAT32 = 5  # a Loader's Depth: float32 (the colour node bands 8-bit photos in the shadows)
FLOAT32 = 4         # Background and Text+ Depth: float32
INHERITED_TIMELINE_SETTINGS = [
    "colorScienceMode", "isAutoColorManage", "rcmPresetMode", "colorSpaceTimeline",
    "colorSpaceOutput", "inputDRT", "outputDRT", "disableFusionToneMapping",
    "timelineInputResMismatchBehavior",
]


def face_of(look, name):
    return look["fusion"]["faces"][name]


def text_width(text, px, face):
    """Width of a run of text: a monospace face's advance, or the face's advances and kerning."""
    if "advanceEm" in face:
        return len(text) * face["advanceEm"] * px
    metrics = face["metrics"]
    units = sum(metrics["advances"].get(character, metrics["fontSize"]) for character in text)
    units += sum(metrics["kerning"].get(text[index - 1:index + 1], 0) for index in range(1, len(text)))
    return units * px / metrics["fontSize"]


def line_box(px, face, line_height=None):
    """(baseline below the line box's top, line box height)."""
    ascent, descent, gap = (round(face[key] * px) for key in ("ascentEm", "descentEm", "lineGapEm"))
    if line_height is None:
        return math.floor(gap / 2) + ascent, ascent + descent + gap
    return math.floor((line_height - ascent - descent) / 2) + ascent, line_height


def snap(box):
    return tuple(round(value) for value in box)


def wrap(text, width, measure, hyphens=False):
    """Greedy line breaking at spaces (and after hyphens when asked)."""
    lines, line = [], ""
    for word in text.split(" "):
        pieces = [piece + "-" for piece in word.split("-")[:-1]] + [word.split("-")[-1]] if hyphens else [word]
        for index, piece in enumerate(pieces):
            joiner = " " if (index == 0 and line) else ""
            if line and measure(line + joiner + piece) > width:
                lines.append(line)
                line = piece
            else:
                line += joiner + piece
    return lines + [line]


def closing_layout(words, look, width):
    """Layout geometry for the Signpost Closing Fusion template."""
    card = look["fusion"]["closing"]
    head, ask, prompt, cta, mission = (card[key] for key in ("headline", "ask", "prompt", "cta", "mission"))
    left, right = card["margin"], width - card["margin"]
    page, heights = {"left": left, "right": right}, {}

    def lines_of(part, text, room):
        return [line for forced in re.split(r"\s+/\s+", text.strip())
                for line in wrap(forced, room, lambda run: text_width(run, part["fontSize"], face_of(look, part["face"])))]

    if "headline" in words:
        page["head_lines"] = lines_of(head, words["headline"], right - left)
        heights["headline"] = len(page["head_lines"]) * head["fontSize"] * head["lineHeight"]
    if "ask" in words:
        page["ask_lines"] = lines_of(ask, words["ask"], right - left)
        ask_baseline, ask_pitch = line_box(ask["fontSize"], face_of(look, ask["face"]))
        heights["ask"] = len(page["ask_lines"]) * ask_pitch
    if "prompt" in words:
        inset = prompt["borderWidth"] + prompt["padding"][1]
        page["prompt_lines"] = lines_of(prompt, words["prompt"], right - left - 2 * inset)
        box_width = (text_width(page["prompt_lines"][0], prompt["fontSize"], face_of(look, prompt["face"])) + 2 * inset
                     if len(page["prompt_lines"]) == 1 else right - left)
        heights["prompt"] = (len(page["prompt_lines"]) * prompt["fontSize"] * prompt["lineHeight"]
                             + 2 * (prompt["padding"][0] + prompt["borderWidth"]))
    if "pill" in words:
        cta_pad = [cta["fontSize"] * em for em in cta["paddingEm"]]
        page["cta_lines"] = lines_of(cta, words["pill"], right - left - 2 * cta_pad[1])
        cta_width = max(text_width(line, cta["fontSize"], face_of(look, cta["face"])) for line in page["cta_lines"]) + 2 * cta_pad[1]
        heights["pill"] = len(page["cta_lines"]) * cta["fontSize"] * cta["lineHeight"] + 2 * cta_pad[0]
    if "mission" in words:
        page["mission_lines"] = lines_of(mission, words["mission"], right - left)
        heights["mission"] = len(page["mission_lines"]) * mission["fontSize"] * mission["lineHeight"]

    middle = [name for name in ("ask", "prompt", "pill") if name in words]
    blocks = [block for block in (["headline"] if "headline" in words else [], middle,
                                  ["mission"] if "mission" in words else []) if block]
    block_heights = [sum(heights[name] for name in block) + card["gap"] * (len(block) - 1) for block in blocks]
    band = card["bottom"] - card["top"]
    if "headline" in words and "mission" in words:
        gap, y = (band - sum(block_heights)) / (len(blocks) - 1), card["top"]
    else:
        gap = card["gap"]
        y = card["top"] + (band - sum(block_heights) - gap * (len(blocks) - 1)) / 2
    tops = {}
    for block, block_height in zip(blocks, block_heights):
        part_top = y
        for name in block:
            tops[name] = part_top
            part_top += heights[name] + card["gap"]
        y += block_height + gap

    if "headline" in words:
        pitch = head["fontSize"] * head["lineHeight"]
        page["head"] = (tops["headline"] + line_box(head["fontSize"], face_of(look, head["face"]), pitch)[0], pitch)
    if "ask" in words:
        page["ask"] = (tops["ask"] + ask_baseline, ask_pitch)
    if "prompt" in words:
        border, pitch = prompt["borderWidth"], prompt["fontSize"] * prompt["lineHeight"]
        box_left, box_top = width / 2 - box_width / 2, tops["prompt"]
        page["box"] = snap((box_left, box_top, box_left + box_width, box_top + heights["prompt"]))
        page["box_inside"] = snap((box_left + border, box_top + border, box_left + box_width - border,
                                   box_top + heights["prompt"] - border))
        page["prompt"] = (box_left + inset, box_left + box_width - inset, box_top + border + prompt["padding"][0]
                          + line_box(prompt["fontSize"], face_of(look, prompt["face"]), pitch)[0], pitch)
    if "pill" in words:
        page["cta_box"] = snap((width / 2 - cta_width / 2, tops["pill"], width / 2 + cta_width / 2, tops["pill"] + heights["pill"]))
        page["cta_baseline"] = tops["pill"] + cta_pad[0] + line_box(cta["fontSize"], face_of(look, cta["face"]),
                                                                    cta["fontSize"] * cta["lineHeight"])[0]
    if "mission" in words:
        pitch = mission["fontSize"] * mission["lineHeight"]
        page["mission"] = (tops["mission"] + line_box(mission["fontSize"], face_of(look, mission["face"]), pitch)[0], pitch)
    safe = look["fusion"]["safeArea"]
    for name, part, rows_key, position_key in (
        ("headline", head, "head_lines", "head"), ("ask", ask, "ask_lines", "ask"),
        ("prompt", prompt, "prompt_lines", "prompt"), ("pill", cta, "cta_lines", "cta_baseline"),
        ("mission", mission, "mission_lines", "mission")
    ):
        if name not in words:
            continue
        face, px = face_of(look, part["face"]), part["fontSize"]
        text_left, room = left, right - left
        if name == "prompt":
            text_left, text_right, baseline, pitch = page[position_key]
            room = text_right - text_left
        elif name == "pill":
            baseline, pitch = page[position_key], px * part["lineHeight"]
            room -= 2 * cta_pad[1]
        else:
            baseline, pitch = page[position_key]
        for index, row in enumerate(page[rows_key]):
            measured = text_width(row, px, face)
            row_left = text_left if name == "prompt" else width / 2 - measured / 2
            row_right = row_left + measured
            bottom = baseline + index * pitch + face["descentEm"] * px
            if measured > room:
                warnings.warn(f"Closing {name} line {row!r} is {measured:.1f}px wide; margins allow {room:.1f}px")
            if bottom > safe["buttonsTop"] and row_right > safe["buttonsLeft"]:
                warnings.warn(f"Closing {name} line {row!r} reaches x={row_right:.1f}, y={bottom:.1f}, across the safe area x={safe['buttonsLeft']} below y={safe['buttonsTop']}")
    return page


def colour(css):
    """'#D9531E', 'rgb(21,18,14)' or 'rgba(0,0,0,.6)' as (r, g, b, a), 0..1, display values."""
    if css.startswith("#"):
        return tuple(int(css[index:index + 2], 16) / 255 for index in (1, 3, 5)) + (1.0,)
    parts = [float(part) for part in re.findall(r"[\d.]+", css)]
    return tuple(part / 255 for part in parts[:3]) + ((parts[3],) if len(parts) > 3 else (1.0,))


class FusionUnits:
    """Fusion inputs for places, boxes and text given in frame pixels."""

    def __init__(self, look, width, height):
        self.look, self.fusion, self.width, self.height = look, look["fusion"], width, height

    def at(self, x, y):
        return {1: x / self.width, 2: 1 - y / self.height}

    def box_inputs(self, left, top, right, bottom, radius):
        width, height = right - left, bottom - top
        return {"Center": self.at((left + right) / 2, (top + bottom) / 2), "Width": width / self.width,
                "Height": height / self.height, "CornerRadius": min(1.0, radius / (min(width, height) / 2)) if radius else 0}

    def text_inputs(self, face_name, px, css, shadow=None):
        face = face_of(self.look, face_name)
        size = px / 100 * face["textSizePer100Px"]
        red, green, blue, alpha = colour(css)
        inputs = {"Font": face["font"], "Style": face["style"], "Size": size, "Depth": FLOAT32,
                  "Red1": red, "Green1": green, "Blue1": blue, "Alpha1": alpha}
        if self.fusion["strokePx"]:
            inputs.update({"Enabled2": 1, "ElementShape2": 1, "OutsideOnly2": 1, "Red2": red, "Green2": green,
                           "Blue2": blue, "Alpha2": alpha,
                           "Thickness2": self.fusion["strokePx"] / (self.fusion["strokePxPerThickness"] * size)})
        if shadow and shadow != "none":
            dx, dy, blur = (float(value) for value in re.findall(r"-?[\d.]+", shadow[:shadow.index("rgb")])[:3])
            sred, sgreen, sblue, salpha = colour(shadow[shadow.index("rgb"):])
            sigma, per_softness = self.fusion["shadowSoftness"]
            softness = (blur / 2 - sigma) / per_softness
            offset = self.fusion["shadowOffsetPerSize"] * size
            inputs.update({"Enabled3": 1, "ElementShape3": 0, "Red3": sred, "Green3": sgreen, "Blue3": sblue,
                           "Alpha3": salpha, "Softness3": 1, "SoftnessX3": softness, "SoftnessY3": softness,
                           "PriorityBack3": -10, "Offset3": {1: dx / offset, 2: -dy / offset}})
        return inputs

    def block_center(self, face_name, px, left, right, first_baseline):
        face = face_of(self.look, face_name)
        top = first_baseline - face["firstBaselinePerSize"] * px / 100 * face["textSizePer100Px"]
        return self.at((left + right) / 2, top + self.fusion["textBoxHeight"] / 2)

    def block_inputs(self, lines, face_name, px, left, right, first_baseline, pitch):
        size = px / 100 * face_of(self.look, face_name)["textSizePer100Px"]
        return {"StyledText": "\n".join(lines), "Center": self.block_center(face_name, px, left, right, first_baseline),
                "LineSpacing": pitch / (self.fusion["linePitchPerSize"] * size)}


class Graph(FusionUnits):
    """A Fusion title's composition, built in frame pixels."""

    def __init__(self, title_item, look, look_folder, width, height, frames):
        super().__init__(look, width, height)
        self.look_folder, self.frames = look_folder, frames
        self.comp = title_item.GetFusionCompByIndex(1)
        self.comp.Lock()
        found = {tool.GetAttrs()["TOOLS_RegID"]: tool for tool in self.comp.GetToolList(False).values()}
        found["TextPlus"].Delete()
        self.media_out = found["MediaOut"]

    def add(self, regid, name=None, **inputs):
        tool = self.comp.AddTool(regid, -32768, -32768)
        if name:
            tool.SetAttrs({"TOOLS_Name": name})
        self.set(tool, **inputs)
        return tool

    def set(self, tool, **inputs):
        for key, value in inputs.items():
            tool.SetInput(key, value)

    def link(self, tool, input_name, source):
        tool.ConnectInput(input_name, source)

    def over(self, background, foreground, **inputs):
        merge = self.add("Merge", **inputs)
        self.link(merge, "Background", background)
        self.link(merge, "Foreground", foreground)
        return merge

    def fill(self, css, name=None):
        red, green, blue, alpha = colour(css)
        return self.add("Background", name, TopLeftRed=red, TopLeftGreen=green, TopLeftBlue=blue, TopLeftAlpha=alpha,
                        Depth=FLOAT32)

    def clear(self):
        return self.fill("rgba(0,0,0,0)")

    def box(self, css, left, top, right, bottom, radius, name=None):
        mask = self.add("RectangleMask", name, **self.box_inputs(left, top, right, bottom, radius))
        shape = self.fill(css)
        self.link(shape, "EffectMask", mask)
        return shape

    def finish(self, last):
        node = self.add("ColorSpaceTransform", "ColourNode", **self.fusion["colourNode"])
        self.link(node, "Input", last)
        self.link(self.media_out, "Input", node)
        self.comp.Unlock()


def image_info(path):
    found = dict(re.findall(r"^\s*(\w+): (.*)$", subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "profile", str(path)],
        capture_output=True, text=True, check=True).stdout, flags=re.M))
    return int(found["pixelWidth"]), int(found["pixelHeight"]), found.get("profile")


def folder(media_pool, name):
    root = media_pool.GetRootFolder()
    found = next((each for each in root.GetSubFolderList() if each.GetName() == name), None)
    return found or media_pool.AddSubFolder(root, name)


def graphic_timeline(project, media_pool, name, width, height, frames):
    settings = project.GetSettings()
    timeline = media_pool.CreateEmptyTimeline(name)
    project.SetCurrentTimeline(timeline)
    timeline.SetSettings({"useCustomSettings": "1"})
    for key in INHERITED_TIMELINE_SETTINGS:
        if not timeline.SetSettings({key: str(settings[key])}) or str(timeline.GetSettings()[key]) != str(settings[key]):
            raise RuntimeError(f"Could not inherit {key}")
    for key, value in [("timelineResolutionWidth", width), ("timelineResolutionHeight", height),
                       ("timelineOutputResolutionWidth", width), ("timelineOutputResolutionHeight", height),
                       ("useInverseDRT", 1)]:
        if not timeline.SetSettings({key: str(value)}) or str(timeline.GetSettings()[key]) != str(value):
            raise RuntimeError(f"Could not set {key}={value}")
    timeline.SetMarkInOut(0, frames - 1)
    timeline.SetCurrentTimecode(timeline.GetStartTimecode())
    item = timeline.InsertFusionTitleIntoTimeline("Text+")
    timeline.ClearMarkInOut()
    return item

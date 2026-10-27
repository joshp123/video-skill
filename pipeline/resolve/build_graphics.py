#!/usr/bin/env python3
"""Build a video's native graphics in Resolve: every photo grid, photo panel and closing page, and a title on any
graphic, as one Fusion composition in its own small timeline, from the cut list, the look and words.md. The terminal
kinds stay Remotion clips (pipeline/graphics); over a terminal only its title is built here.

Written by AI on 2026-10-22 by Claude Opus 5.5, from the native graphics test of 21 Oct
(.cache/native-graphics-test/scripts: build_intro.py, build_closing.py, layout.py, fb.py, ngtl.py).

Run from a shell: build_graphics.py EDIT_FOLDER [--output MANIFEST] [--timeline-prefix PREFIX]. Through the Resolve MCP:
resolve and EDIT_FOLDER, with optional OUTPUT_FILE and TIMELINE_PREFIX in the namespace.
The project the edit data names must be open; each graphic gets a new timeline named
"<video> graphic <id> <cut>" (a number added if that name is taken), or "<prefix> graphic <id> <cut>".
Writes --output (default build/graphics-native/manifest.json), refusing to overwrite it:
[{id, timeline, timeline_in_frame, frames, slots: {field: "final" | "proposed" | "placeholder"}}], which the timeline
builder places above the cameras. change_graphic_words.py uses the layout functions here to change words in place.

A closing page draws the parts its slots name; a title's words come from the words.md heading its slot names, with a
[[bracketed]] part on the pill and " / " for a line break. A cut list built from another edit.json is refused.

Positions are frame pixels from the top left, laid out as Chrome lays out the same values; the look's fusion section
converts them to Fusion's units.
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

NATIVE_KINDS = {"photo-grid", "photo-panel", "closing"}
CLOSING_PARTS = ("headline", "ask", "prompt", "pill", "mission")
CUE_VERBS = {"photo-grid": {"show", "label"}, "photo-panel": {"show"}, "closing": set()}
LOADER_FLOAT32 = 5  # a Loader's Depth: float32 (the colour node bands 8-bit photos in the shadows)
FLOAT32 = 4         # Background and Text+ Depth: float32
INHERITED_TIMELINE_SETTINGS = ["colorScienceMode", "isAutoColorManage", "rcmPresetMode", "colorSpaceTimeline",
                               "colorSpaceOutput", "inputDRT", "outputDRT", "disableFusionToneMapping",
                               "timelineInputResMismatchBehavior"]


# Text layout: what the browser works out by itself, from the look's font measurements.

def face_of(look, name):
    return look["fusion"]["faces"][name]


def text_width(text, px, face):
    """Width of a run of text: a monospace face's advance, or the face's advances and kerning; a character the face
    lacks (the pin) is one em, as the fallback face draws it."""
    if "advanceEm" in face:
        return len(text) * face["advanceEm"] * px
    metrics = face["metrics"]
    units = sum(metrics["advances"].get(character, metrics["fontSize"]) for character in text)
    units += sum(metrics["kerning"].get(text[index - 1:index + 1], 0) for index in range(1, len(text)))
    return units * px / metrics["fontSize"]


def line_box(px, face, line_height=None):
    """(baseline below the line box's top, line box height), as Chrome computes them: ascent and descent rounded to
    whole pixels, the half-leading above the text rounded down. A pin in the line leaves it as it is (measured)."""
    ascent, descent, gap = (round(face[key] * px) for key in ("ascentEm", "descentEm", "lineGapEm"))
    if line_height is None:
        return math.floor(gap / 2) + ascent, ascent + descent + gap
    return math.floor((line_height - ascent - descent) / 2) + ascent, line_height


def snap(box):
    """Chrome paints boxes on whole pixels (text it places to fractions of a pixel)."""
    return tuple(round(value) for value in box)


def wrap(text, width, measure, hyphens=False):
    """Greedy line breaking at spaces (and after hyphens when asked), as the browser does."""
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


def title_lines(words, px, face, pill_pad, room):
    """A title's lines of parts [(text, on_pill)] from its words: a part in [[double brackets]] goes on the pill, a /
    between words breaks the line, and a line wider than room wraps at its spaces, a pill kept whole."""

    def parts_of(units):
        parts = []
        for text, pill in units:
            if parts and not pill and not parts[-1][1]:
                parts[-1] = (parts[-1][0] + text, False)
            else:
                parts.append((text, pill))
        if parts and not parts[0][1]:
            parts[0] = (parts[0][0].lstrip(), False)
        if parts and not parts[-1][1]:
            parts[-1] = (parts[-1][0].rstrip(), False)
        return [part for part in parts if part[0]]

    def line_width(units):
        return sum(text_width(text, px, face) + (2 * pill_pad if pill else 0) for text, pill in parts_of(units))

    lines = []
    for forced in re.split(r"\s+/\s+", words.strip()):
        units = []
        for index, piece in enumerate(re.split(r"\[\[(.+?)\]\]", forced)):
            units += [(piece, True)] if index % 2 else [(word, False) for word in re.findall(r"\s*\S+\s*", piece)]
        line = []
        for unit in units:
            if line and line_width(line + [unit]) > room:
                lines.append(parts_of(line))
                line = []
            line.append(unit)
        lines.append(parts_of(line))
    for line in lines:
        measured = line_width(line)
        if measured > room:
            raise ValueError(f"Title line {' '.join(text for text, _ in line)!r} is {measured:.1f}px wide; margins allow {room:.1f}px")
    return lines


def title_layout(title, words, look, width):
    """The title: its words in lines (title_lines), each line centred, its parts side by side, a pill part on a box
    padded by the look."""
    values = look["fusion"]["title"]
    face, px = face_of(look, values["face"]), title["fontSize"]
    pitch, pill_height = px * values["lineHeight"], px * values["pill"]["lineHeight"]
    pad = [px * em for em in values["pill"]["paddingEm"]]  # top, sides, bottom
    lines = title_lines(words, px, face, pad[1], width - 2 * values["margin"])
    top = title["centerY"] - pitch * len(lines) / 2
    parts, line_top = [], top
    for line in lines:
        widths = [text_width(text, px, face) + (2 * pad[1] if pill else 0) for text, pill in line]
        x = width / 2 - sum(widths) / 2
        baseline = line_top + line_box(px, face, pitch)[0]
        line_bottom = line_top + pitch
        for (text, pill), part_width in zip(line, widths):
            box = None
            if pill:
                box_top = baseline - line_box(px, face, pill_height)[0] - pad[0]
                box = snap((x, box_top, x + part_width, box_top + pad[0] + pill_height + pad[2]))
                line_bottom = max(line_bottom, box[3])
            parts.append({"text": text, "x": x + (pad[1] if box else 0), "baseline": baseline, "box": box})
            x += part_width
        line_top = line_bottom
    reach = values["band"]["reach"]
    return {"parts": parts, "band": (top - reach, pitch * len(lines) + 2 * reach)}


def closing_layout(words, look, width):
    """The closing page from the parts its slots name, top to bottom: the headline; the ask, the prompt box and the
    button, the look's gap between them; the mission line. With a headline and a mission line the parts span the band
    from the look's top to its bottom, equal space between them; without either, they close up, the look's gap
    between them, centred in the band. Each part is centred and wrapped inside the margins."""
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


def label_layout(text, sublabel, size, left, top, max_width, look):
    """A photo label's box and lines: the label wrapped inside the box, a smaller sublabel under it; the box as wide
    as its widest line, up to max_width."""
    label = look["fusion"]["photoLabel"]
    face = face_of(look, label["face"])
    pad_y, pad_x = label["padding"]
    pitch = size * label["lineHeight"]
    room = max_width - 2 * pad_x
    lines = wrap(text, room, lambda run: text_width(run, size, face))
    content = text_width(text, size, face)
    placed, y = [], top + pad_y
    for line in lines:
        baseline, height = line_box(size, face, pitch)
        placed.append({"text": line, "x": left + pad_x, "baseline": y + baseline})
        y += height
    sub = None
    if sublabel:
        values = look["fusion"]["photoPanel"]["sublabel"]
        sub_size = size * values["scale"]
        content = max(content, text_width(sublabel, sub_size, face_of(look, values["face"])))
        y += values["gap"]
        baseline, height = line_box(sub_size, face_of(look, values["face"]), sub_size * label["lineHeight"])
        sub = {"text": sublabel, "x": left + pad_x, "baseline": y + baseline, "size": sub_size}
        y += height
    box = (left, top, left + min(max_width, content + 2 * pad_x), y + pad_y)
    return {"lines": placed, "sublabel": sub, "box": box}


def label_max_width(region_right, left, top, inset, look, width):
    """Room for a label from its left edge: to the region's edge less the inset; below the platform's buttons' top,
    never past their left edge."""
    safe = look["fusion"]["safeArea"]
    limit = safe["buttonsLeft"] if top >= safe["buttonsTop"] else width
    return min(region_right - inset, limit) - left


def photo_tiles(region, count, columns):
    """The grid's tiles in a region, row by row: (left, top, width, height)."""
    x, y, width, height = region
    columns = min(columns, count or 1)
    rows = math.ceil(count / columns)
    return [(x + (index % columns) * width / columns, y + (index // columns) * height / rows, width / columns,
             height / rows) for index in range(count)]


# Fusion.

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
        """A point in frame pixels from the top left, as Fusion's normalised point from the bottom left."""
        return {1: x / self.width, 2: 1 - y / self.height}

    def box_inputs(self, left, top, right, bottom, radius):
        """A Rectangle mask's inputs for a box in frame pixels."""
        width, height = right - left, bottom - top
        return {"Center": self.at((left + right) / 2, (top + bottom) / 2), "Width": width / self.width,
                "Height": height / self.height, "CornerRadius": min(1.0, radius / (min(width, height) / 2)) if radius else 0}

    def gradient_inputs(self, left, top, right, bottom, stops):
        """A gradient Background's inputs, black at the given opacities [(pixels from the top, opacity)], and where
        its merge puts it."""
        height = bottom - top
        return ({"Width": right - left, "Height": height,
                 "Gradient": {offset / height: [0, 0, 0, opacity] for offset, opacity in stops}},
                {"Center": self.at((left + right) / 2, (top + bottom) / 2)})

    def text_inputs(self, face_name, px, css, shadow=None):
        """Text+ in display colours, at a size in frame pixels; Chrome draws letters a little heavier than their
        outlines, so each text has an outline of its own colour (the look's strokePx); a CSS text-shadow is the text's
        own shadow element."""
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
        """Where a top-anchored text box goes so that its first baseline lands on first_baseline."""
        face = face_of(self.look, face_name)
        top = first_baseline - face["firstBaselinePerSize"] * px / 100 * face["textSizePer100Px"]
        return self.at((left + right) / 2, top + self.fusion["textBoxHeight"] / 2)

    def block_inputs(self, lines, face_name, px, left, right, first_baseline, pitch):
        """A text box's words and place: lines broken as the browser breaks them, first baseline and pitch in pixels."""
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

    def animate(self, tool, input_name, keys):
        """Linear keyframes {frame: value} on one input."""
        tool.AddModifier(input_name, "BezierSpline")
        inputs = tool.GetInputList()
        ids = [each.GetAttrs()["INPS_ID"] for each in inputs.values()]
        spline = inputs[ids.index(input_name) + 1].GetConnectedOutput().GetTool()
        spline.SetKeyFrames({frame: {1: value, "Flags": {"Linear": True}} for frame, value in keys.items()}, True)

    def shown(self, merge, start, end):
        """A merged layer seen on comp frames start (inclusive) to end (exclusive). A new spline holds a key at
        frame 0, so the keys start there."""
        keys = {0: 1 if start <= 0 else 0}
        if start > 0:
            keys.update({start - 1: 0, start: 1})
        if end < self.frames:
            keys.update({end - 1: 1, end: 0})
        if len(keys) > 1:
            self.animate(merge, "Blend", keys)

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
        """A rounded rectangle in frame pixels (a radius of half the height or more is a pill)."""
        mask = self.add("RectangleMask", name, **self.box_inputs(left, top, right, bottom, radius))
        shape = self.fill(css)
        self.link(shape, "EffectMask", mask)
        return shape

    def gradient(self, background, left, top, right, bottom, stops, name=None):
        """Black at the given opacities [(pixels from the top, opacity)], from top to bottom, over background."""
        band_inputs, place = self.gradient_inputs(left, top, right, bottom, stops)
        band = self.add("Background", name, UseFrameFormatSettings=0)
        self.set(band, Type="Gradient", Depth=FLOAT32, Start={1: 0.5, 2: 1}, End={1: 0.5, 2: 0}, **band_inputs)
        return self.over(background, band, name=f"{name}Place" if name else None, **place)

    def line(self, words, face_name, px, css, x, baseline, centred=False, shadow=None, name=None):
        """One line of text with its baseline at (x, baseline), starting at x or centred on it."""
        return self.add("TextPlus", name, StyledText=words, Center=self.at(x, baseline),
                        HorizontalLeftCenterRight=0 if centred else -1, HorizontalJustificationNew=3 if centred else 0,
                        CenterOnBaseOfFirstLine=1, **self.text_inputs(face_name, px, css, shadow))

    def block(self, lines, face_name, px, css, left, right, first_baseline, pitch, centred=True, shadow=None, name=None):
        """Lines of text in a box from left to right, each centred (or from the left), first baseline and line pitch in
        pixels; the lines are broken as the browser breaks them."""
        tool = self.add("TextPlus", name, LayoutType=1, Wrap=1, LayoutWidth=(right - left) / self.width,
                        LayoutHeight=self.fusion["textBoxHeight"] / self.height, VerticalTopCenterBottom=-1,
                        VerticalJustificationNew=0, HorizontalLeftCenterRight=0 if centred else -1,
                        **self.text_inputs(face_name, px, css, shadow))
        self.set(tool, **self.block_inputs(lines, face_name, px, left, right, first_baseline, pitch))
        return tool

    def photo(self, path, size, profile, box_width, box_height, position, name):
        """A photo covering a box of box_width x box_height at object-position (x, y) in 0..1: a Letterbox that fills
        the box's width (a taller photo) or height (a wider one), cropped to the box; then from its colour profile to
        the frame's, as the browser converts it. Letterbox's Center is the point of the scaled photo that sits at the
        box's centre, in fractions of the photo from its bottom left (measured 22 Oct)."""
        loader = self.add("Loader", name, Clip=str(path), Depth=LOADER_FLOAT32)
        self.set(loader, HoldLastFrame=self.frames)
        x, y = position
        scale = max(box_width / size[0], box_height / size[1])
        scaled_width, scaled_height = size[0] * scale, size[1] * scale
        cover = self.add("Letterbox", UseFrameFormatSettings=0)
        self.set(cover, Width=box_width, Height=box_height, Mode=1 if size[0] / size[1] > box_width / box_height else 0,
                 Center={1: ((scaled_width - box_width) * x + box_width / 2) / scaled_width,
                         2: 1 - ((scaled_height - box_height) * y + box_height / 2) / scaled_height})
        self.link(cover, "Input", loader)
        last = self.add("Crop", XSize=box_width, YSize=box_height)
        self.link(last, "Input", cover)
        conversion = self.fusion["photoColourNodes"].get(profile)
        if conversion:
            converted = self.add("ColorSpaceTransform", **conversion)
            self.link(converted, "Input", last)
            last = self.add("BrightnessContrast", ClipBlack=1, ClipWhite=1)
            self.link(last, "Input", converted)
        return last

    def line_with_images(self, background, words, face_name, px, css, x, baseline, shadow, name):
        """One line of text over background, its characters with an image in the fallback face (the pin) drawn from
        that image, as Chrome draws them: Fusion's Text+ draws colour emoji darker. Each image is a square of one em
        from its pen position, its top imageTopEm from the baseline; the text between is in Text+ runs."""
        fallback, face = face_of(self.look, self.fusion["fallbackFace"]), face_of(self.look, face_name)
        last, start = background, 0
        for position, character in enumerate(words + "\0"):
            if character != "\0" and character not in fallback.get("images", {}):
                continue
            run = words[start:position].lstrip(" ")
            if run:
                run_x = x + text_width(words[:position - len(run)], px, face)
                last = self.over(last, self.line(run, face_name, px, css, run_x, baseline, shadow=shadow,
                                                 name=f"{name}Run{start}"))
            if character != "\0":
                image = self.look_folder / fallback["images"][character]
                loader = self.add("Loader", f"{name}Image{position}", Clip=str(image), Depth=LOADER_FLOAT32,
                                  PostMultiplyByAlpha=1)
                self.set(loader, HoldLastFrame=self.frames)
                scaled = self.add("Transform", Size=px / image_info(image)[0])
                self.link(scaled, "Input", loader)
                left, top = x + text_width(words[:position], px, face), baseline + fallback["imageTopEm"] * px
                last = self.over(last, scaled, Center=self.at(left + px / 2, top + px / 2))
            start = position + 1
        return last

    def label(self, background, layout, size, name):
        """A photo label over background: its box, its lines and its sublabel."""
        label = self.fusion["photoLabel"]
        last = self.over(background, self.box(label["background"], *layout["box"], label["borderRadius"], name=f"{name}Box"))
        for index, line in enumerate(layout["lines"]):
            last = self.line_with_images(last, line["text"], label["face"], size, label["color"], line["x"], line["baseline"],
                                         label["shadow"], f"{name}Line{index}")
        sub = layout["sublabel"]
        if sub:
            last = self.over(last, self.line(sub["text"], self.fusion["photoPanel"]["sublabel"]["face"], sub["size"],
                                             label["color"], sub["x"], sub["baseline"], shadow=label["shadow"],
                                             name=f"{name}Sublabel"))
        return last

    def finish(self, last):
        """Display values in, so every colour typed in comes out as typed: Rec.709 to the timeline's linear DWG."""
        node = self.add("ColorSpaceTransform", "ColourNode", **self.fusion["colourNode"])
        self.link(node, "Input", last)
        self.link(self.media_out, "Input", node)
        self.comp.Unlock()


def title_band(layout, title, look, width):
    """The title's soft band: its box and its stops, clear to the title's opacity over the soft edge and back."""
    top, height = layout["band"]
    edge = look["fusion"]["title"]["band"]["softEdge"]
    return (0, top, width, top + height), [(0, 0), (edge, title["band"]), (height - edge, title["band"]), (height, 0)]


def title_inputs(g, layout, title):
    """The Text+ and box inputs a title's words set: each part's words and place, each pill's box, the band."""
    inputs = {}
    if title["band"] > 0:
        box, stops = title_band(layout, title, g.look, g.width)
        inputs["Band"], inputs["BandPlace"] = g.gradient_inputs(*box, stops)
    for index, part in enumerate(layout["parts"]):
        inputs[f"Part{index}"] = {"StyledText": part["text"], "Center": g.at(part["x"], part["baseline"])}
        if part["box"]:
            inputs[f"Pill{index}"] = g.box_inputs(*part["box"], title["fontSize"])
    return inputs


def closing_inputs(g, page, words):
    """The Text+ and box inputs the closing page's words set, for the parts it has."""
    card, terminal = g.fusion["closing"], g.look["terminal"]
    head, ask, prompt, cta, mission = (card[key] for key in ("headline", "ask", "prompt", "cta", "mission"))
    left, right = page["left"], page["right"]
    radius, border = terminal["panel"]["borderRadius"], prompt["borderWidth"]
    inputs = {}
    if "headline" in words:
        inputs["Headline"] = g.block_inputs(page["head_lines"], head["face"], head["fontSize"], left, right, *page["head"])
    if "ask" in words:
        inputs["Ask"] = g.block_inputs(page["ask_lines"], ask["face"], ask["fontSize"], left, right, *page["ask"])
    if "prompt" in words:
        inputs["BoxEdge"] = g.box_inputs(*page["box"], radius)
        inputs["BoxFill"] = g.box_inputs(*page["box_inside"], radius - border)
        inputs["Prompt"] = g.block_inputs(page["prompt_lines"], prompt["face"], prompt["fontSize"], *page["prompt"])
    if "pill" in words:
        inputs["Button"] = g.box_inputs(*page["cta_box"], page["cta_box"][3] - page["cta_box"][1])
        size = cta["fontSize"] / 100 * face_of(g.look, cta["face"])["textSizePer100Px"]
        inputs["ButtonWords"] = {"StyledText": "\n".join(page["cta_lines"]), "Center": g.at(g.width / 2, page["cta_baseline"]),
                                 "LineSpacing": cta["fontSize"] * cta["lineHeight"] / (g.fusion["linePitchPerSize"] * size)}
    if "mission" in words:
        inputs["Mission"] = g.block_inputs(page["mission_lines"], mission["face"], mission["fontSize"], left, right, *page["mission"])
    return inputs


def draw_title(g, last, title, words):
    """The title over last: a soft dark band, plain parts in the look's type and shadow, a pill part on its box."""
    values, pill = g.fusion["title"], g.look["subtitles"]["activeWord"]
    layout = title_layout(title, words, g.look, g.width)
    if title["band"] > 0:
        box, stops = title_band(layout, title, g.look, g.width)
        last = g.gradient(last, *box, stops, name="Band")
    px = title["fontSize"]
    for index, part in enumerate(layout["parts"]):
        if part["box"]:
            last = g.over(last, g.box(pill["background"], *part["box"], px, name=f"Pill{index}"))
            last = g.over(last, g.line(part["text"], values["face"], px, pill["color"], part["x"], part["baseline"],
                                       name=f"Part{index}"))
        else:
            last = g.over(last, g.line(part["text"], values["face"], px, values["color"], part["x"], part["baseline"],
                                       shadow=values["shadow"], name=f"Part{index}"))
    return last


def draw_photo_grid(g, graphic, plan):
    """Photos in tiles over the look's background, each from its arrival frame, darkened by the content's darken;
    the labels from the label cue."""
    look, frames = g.look, plan["frames"]
    layout = plan["layout"]
    region = layout.get("graphic") or [0, 0, g.width, g.height]
    background_height = layout["picture"][1] if layout.get("picture") else g.height
    last = g.box(look["background"], 0, 0, g.width, background_height, 0, name="Background")
    tiles_layer = g.clear()
    tiles = photo_tiles(region, len(plan["photos"]), g.fusion["photoGrid"]["columns"])
    for index, (photo, (left, top, width, height)) in enumerate(zip(plan["photos"], tiles)):
        if index not in plan["arrivals"]:
            continue
        tile = g.photo(photo["file"], photo["size"], photo["profile"], width, height, photo["position"], f"Photo{index}")
        tiles_layer = g.over(tiles_layer, tile, Center=g.at(left + width / 2, top + height / 2))
        g.shown(tiles_layer, plan["arrivals"][index], frames)
    darken = graphic["content"].get("darken")
    if darken:
        darker = g.add("BrightnessContrast", "Darken", Gain=1 - darken)
        g.link(darker, "Input", tiles_layer)
        tiles_layer = darker
    last = g.over(last, tiles_layer)
    if plan["labels_from"] is not None:
        labels_layer = g.clear()
        for index, photo in enumerate(plan["photos"]):
            if index in plan["arrivals"]:
                labels_layer = g.label(labels_layer, photo["label_layout"], plan["label_size"], f"Label{index}")
        last = g.over(last, labels_layer)
        g.shown(last, plan["labels_from"], frames)
    return last


def draw_photo_panel(g, graphic, plan):
    """The panel's photos in the layout's picture region, each from its cue to its until (or the graphic's end), the
    later over the earlier: each covering the region, under the look's scrim, with its label."""
    left, top, width, height = plan["layout"]["picture"]
    scrim = g.fusion["photoPanel"]["scrim"]
    last = g.clear()
    for index, item in enumerate(plan["items"]):
        photo = item["photo"]
        layer = g.over(g.clear(), g.photo(photo["file"], photo["size"], photo["profile"], width, height, photo["position"],
                                          f"Photo{index}"), Center=g.at(left + width / 2, top + height / 2))
        scrim_top = top + scrim["top"]
        layer = g.gradient(layer, left, scrim_top, left + width, scrim_top + scrim["stops"][-1][0], scrim["stops"])
        layer = g.label(layer, photo["label_layout"], g.fusion["photoLabel"]["fontSize"], f"Label{index}")
        last = g.over(last, layer, name=f"Show{index}")
        g.shown(last, item["start"], item["end"])
    return last


def draw_closing(g, graphic, plan):
    """The closing page, its parts as its slots name them: the footage darkens to the look's level, then the page
    becomes the plain background; the words fade in."""
    card, terminal, words = g.fusion["closing"], g.look["terminal"], plan["words"]
    head, ask, prompt, cta, mission = (card[key] for key in ("headline", "ask", "prompt", "cta", "mission"))
    page = closing_layout(words, g.look, g.width)
    fade = card["fade"]
    background = g.fill(g.look["background"], name="Background")
    g.animate(background, "TopLeftAlpha", {0: 0, fade["darkFrames"]: fade["darkTo"], fade["darkFrames"] + fade["plainFrames"]: 1})
    left, right, shadow = page["left"], page["right"], card["shadow"]
    radius, border = terminal["panel"]["borderRadius"], prompt["borderWidth"]
    words_layer = g.clear()
    if "headline" in words:
        words_layer = g.over(words_layer, g.block(page["head_lines"], head["face"], head["fontSize"], card["color"], left,
                                                  right, *page["head"], shadow=shadow, name="Headline"))
    if "ask" in words:
        words_layer = g.over(words_layer, g.block(page["ask_lines"], ask["face"], ask["fontSize"], ask["color"], left,
                                                  right, *page["ask"], shadow=shadow, name="Ask"))
    if "prompt" in words:
        words_layer = g.over(words_layer, g.box(terminal["prompt"], *page["box"], radius, name="BoxEdge"))
        words_layer = g.over(words_layer, g.box(prompt["background"], *page["box_inside"], radius - border, name="BoxFill"))
        words_layer = g.over(words_layer, g.block(page["prompt_lines"], prompt["face"], prompt["fontSize"], terminal["text"],
                                                  *page["prompt"], centred=False, name="Prompt"))
    if "pill" in words:
        words_layer = g.over(words_layer, g.box(cta["background"], *page["cta_box"], page["cta_box"][3] - page["cta_box"][1],
                                                name="Button"))
        button_words = g.line("\n".join(page["cta_lines"]), cta["face"], cta["fontSize"], cta["color"], g.width / 2,
                              page["cta_baseline"], centred=True, name="ButtonWords")
        g.set(button_words, **closing_inputs(g, page, words)["ButtonWords"])
        words_layer = g.over(words_layer, button_words)
    if "mission" in words:
        words_layer = g.over(words_layer, g.block(page["mission_lines"], mission["face"], mission["fontSize"], mission["color"],
                                                  left, right, *page["mission"], shadow=shadow, name="Mission"))
    last = g.over(background, words_layer, name="Page")
    g.animate(last, "Blend", {frame: min(1, (frame + 1) / fade["textFrames"]) for frame in range(fade["textFrames"])})
    return last


# The edit data.

def read_edit(edit_folder):
    """The edit data and its cut list; a cut list built from other cut inputs is refused (a camera's grade or a
    mixer field is not a cut input, so changing one does not stale the cut list: cut/build_cutlist.py, cut_inputs)."""
    import importlib.util
    edit = json.loads((edit_folder / "edit/edit.json").read_text())
    cut = json.loads((edit_folder / "build/cutlist.json").read_text())
    spec = importlib.util.spec_from_file_location("build_cutlist", edit_folder.parent / "pipeline/cut/build_cutlist.py")
    cut_builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cut_builder)
    if cut.get("cut_inputs") != cut_builder.cut_inputs(edit):
        raise RuntimeError("The cut list was built from other cut inputs than edit.json holds now. Rebuild the cut list and align it first.")
    return edit, cut


def slot_words(markdown, heading):
    """A slot's words and their source: its Final: line, else its Proposed: line, else a labelled placeholder."""
    sections = re.split(rf"^## {re.escape(heading)}\s*$", markdown, flags=re.M)
    if len(sections) < 2:
        raise ValueError(f"words.md has no heading for the slot: {heading}")
    body = re.split(r"^## ", sections[1], flags=re.M)[0]
    for source in ("Final", "Proposed"):
        found = re.search(rf"^{source}:[ \t]*(.*)$", body, flags=re.M)
        if found and found.group(1).strip():
            return found.group(1).strip(), source.lower()
    return f"[{heading}: Josh's words]", "placeholder"


def aligned_frame(cut, anchor):
    """The forced-alignment frame of an anchor: its first word's start, or with edge "end" its last word's end,
    moved by offset_s (matched as the cut builder matches words)."""
    tokens = []
    for word in (word for word in cut["words"] if word["line"] == anchor["line"]):
        for text in (word.get("source_word") or word["word"]).split():
            tokens.append((text, word.get("aligned_start_frame"), word.get("aligned_end_frame")))

    def plain(text):
        return re.sub(r"[^a-z0-9']", "", text.lower().replace("’", "'"))
    target = [plain(text) for text in (anchor.get("word") or anchor["at"]).split()]
    matches = 0
    for index in range(len(tokens) - len(target) + 1):
        if [plain(text) for text, _, _ in tokens[index:index + len(target)]] != target:
            continue
        if matches != anchor.get("n", 0):
            matches += 1
            continue
        frame = tokens[index + len(target) - 1][2] if anchor.get("edge") == "end" else tokens[index][1]
        if frame is None:
            raise ValueError(f"Aligned cue time absent: {anchor['line']}: {' '.join(target)}")
        return frame + math.floor(anchor.get("offset_s", 0) * cut["fps"] + 0.5)
    raise ValueError(f"Aligned cue word absent: {anchor['line']}: {' '.join(target)}")


def image_info(path):
    """An image file's pixel width, height and colour profile, as macOS's sips reads them from the file."""
    found = dict(re.findall(r"^\s*(\w+): (.*)$", subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "profile", str(path)],
        capture_output=True, text=True, check=True).stdout, flags=re.M))
    return int(found["pixelWidth"]), int(found["pixelHeight"]), found.get("profile")


def read_photos(edit_folder, content, staging, graphic_id):
    """The graphic's photos from its list file (or those its use names), each with the file a Loader reads, its pixel
    size, its colour profile and its object-position. A Loader reads a file whose name ends in digits as a frame of an
    image sequence (00.jpeg to 05.jpeg showed the last photo in every tile), so such a file is copied to a name that
    does not."""
    photos = json.loads((edit_folder / content["photos"]).read_text())["photos"]
    if "use" in content:
        by_label = {photo["label"]: photo for photo in photos}
        missing = [label for label in content["use"] if label not in by_label]
        if missing:
            raise ValueError(f"Unknown photo label: {', '.join(missing)}")
        photos = [by_label[label] for label in content["use"]]
    read = []
    for index, photo in enumerate(photos):
        path = (edit_folder / photo["path"]).resolve()
        if re.search(r"\d$", path.stem):
            staging.mkdir(parents=True, exist_ok=True)
            copy = staging / f"{graphic_id} {index:02d} photo{path.suffix}"
            shutil.copyfile(path, copy)
            path = copy
        width, height, profile = image_info(path)
        x, y = (float(value.rstrip("%")) / 100 for value in photo.get("position", "50% 50%").split())
        read.append({**photo, "file": path, "size": (width, height), "profile": profile, "position": (x, y)})
    return read


def cue_photo_indexes(photos, cue, graphic_id):
    """A cue names one photo by its label or its file name; a cue with no target names them all."""
    if "target" not in cue:
        return list(range(len(photos)))
    named = [index for index, photo in enumerate(photos) if cue["target"] in (photo["label"], Path(photo["path"]).name)]
    if len(named) != 1:
        raise ValueError(f"{graphic_id}: the cue target names {len(named)} photos, not one: {cue['target']}")
    return named


def plan_graphic(graphic, edit_folder, cut, look, markdown, staging):
    """Everything a graphic's composition needs from the data, read before anything is built in Resolve."""
    if not graphic.get("in_resolved") or not graphic.get("out_resolved"):
        raise ValueError(f"Unresolved graphic anchor: {graphic['id']}")
    kind, start = graphic["kind"], graphic["in_resolved"]["frame"]
    stray = [cue["do"] for cue in graphic.get("cues", []) if kind in CUE_VERBS and cue["do"] not in CUE_VERBS[kind]]
    if stray:
        raise ValueError(f"Graphic {graphic['id']} ({kind}) has a cue verb no {kind} draws: {stray[0]}")
    width = cut["format"]["width"]
    plan = {"start": start, "frames": graphic["out_resolved"]["frame"] - start, "layout": cut["layouts"][graphic["layout"]],
            "slots": {}}

    def item_start(cue):
        """A timed item's first comp frame: its cue word's aligned frame, or the graphic's first frame (first_frame)."""
        return 0 if graphic.get("first_frame") else aligned_frame(cut, cue["at"]) - start

    if kind == "photo-grid":
        photos = read_photos(edit_folder, graphic["content"], staging, graphic["id"])
        arrivals, labels_from = {}, None
        for cue in graphic.get("cues", []):
            if cue["do"] == "show":
                for index in cue_photo_indexes(photos, cue, graphic["id"]):
                    arrivals.setdefault(index, item_start(cue))
            elif labels_from is None:
                labels_from = item_start(cue)
        if graphic.get("first_frame"):
            arrivals = {index: 0 for index in range(len(photos))}
        region = plan["layout"].get("graphic") or [0, 0, width, cut["format"]["height"]]
        grid, label = look["fusion"]["photoGrid"], look["fusion"]["photoLabel"]
        tiles = photo_tiles(region, len(photos), grid["columns"])
        boxes = []
        for photo, (left, top, tile_width, _) in zip(photos, tiles):
            label_left, label_top = left + grid["labelInset"], top + max(grid["labelInset"], grid["labelTop"] - top)
            boxes.append((label_left, label_top, label_max_width(left + tile_width, label_left, label_top, grid["labelInset"], look, width)))
        # The largest size, in quarter pixels, at which every label fits its lines.
        size = label["fontSize"]
        face = face_of(look, label["face"])
        while not all(len(wrap(label["prefix"] + photo["label"], room - 2 * label["padding"][1],
                               lambda run: text_width(run, size, face))) <= label["maxLines"]
                      for photo, (_, _, room) in zip(photos, boxes)):
            size -= 0.25
        for photo, (label_left, label_top, room) in zip(photos, boxes):
            photo["label_layout"] = label_layout(label["prefix"] + photo["label"], None, size, label_left, label_top, room, look)
        plan.update(photos=photos, arrivals=arrivals, labels_from=labels_from, label_size=size)
    elif kind == "photo-panel":
        photos = read_photos(edit_folder, graphic["content"], staging, graphic["id"])
        left, top, region_width, _ = plan["layout"]["picture"]
        inset, label = look["fusion"]["photoPanel"]["labelInset"], look["fusion"]["photoLabel"]
        label_left, label_top = left + inset, top + inset
        room = label_max_width(left + region_width, label_left, label_top, inset, look, width)
        for photo in photos:
            photo["label_layout"] = label_layout(label["prefix"] + photo["label"], photo.get("sublabel"), label["fontSize"],
                                                 label_left, label_top, room, look)
        items = []
        for cue in graphic.get("cues", []):
            end = aligned_frame(cut, cue["until"]) - start if "until" in cue else plan["frames"]
            for index in cue_photo_indexes(photos, cue, graphic["id"]):
                items.append({"photo": photos[index], "start": item_start(cue), "end": end})
        plan["items"] = [item for item in items if item["start"] < item["end"] and item["start"] < plan["frames"] and item["end"] > 0]
    elif kind == "closing":
        unknown = [field for field in graphic["content"]["slots"] if field not in CLOSING_PARTS]
        if unknown:
            raise ValueError(f"{graphic['id']}: a closing page has no part named {', '.join(unknown)}")
        plan["words"] = {}
        for field, heading in graphic["content"]["slots"].items():
            plan["words"][field], plan["slots"][field] = slot_words(markdown, heading)
    if graphic["content"].get("title"):
        plan["title_words"], plan["slots"]["title"] = slot_words(markdown, graphic["content"]["title"]["slot"])
    return plan


# Resolve.

def folder(media_pool, name):
    root = media_pool.GetRootFolder()
    found = next((each for each in root.GetSubFolderList() if each.GetName() == name), None)
    return found or media_pool.AddSubFolder(root, name)


def graphic_timeline(project, media_pool, name, width, height, frames):
    """A timeline with the project's colour management, the format and inverse DRT on (as the timeline builder makes
    the finishing timeline), holding one Fusion title of the graphic's length; returns the title's timeline item."""
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
    # A title inserted by script lands at the playhead between the marks.
    timeline.SetMarkInOut(0, frames - 1)
    timeline.SetCurrentTimecode(timeline.GetStartTimecode())
    item = timeline.InsertFusionTitleIntoTimeline("Text+")
    timeline.ClearMarkInOut()
    return item


def build(resolve, edit_folder, output=None, timeline_prefix=None):
    edit_folder = Path(edit_folder).resolve()  # a Fusion Loader cannot find a relative path
    edit, cut = read_edit(edit_folder)
    look_folder = edit_folder.parent / "looks" / edit["look"]
    look = json.loads((look_folder / "look.json").read_text())
    markdown = (edit_folder / "words.md").read_text()
    manifest_path = edit_folder / (output or "build/graphics-native/manifest.json")
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite {manifest_path}; choose a new --output path")
    out = manifest_path.parent
    width, height = cut["format"]["width"], cut["format"]["height"]
    graphics = [graphic for graphic in cut["graphics"] if graphic["kind"] in NATIVE_KINDS or graphic["content"].get("title")]
    plans = [plan_graphic(graphic, edit_folder, cut, look, markdown, out / "photos") for graphic in graphics]

    project = resolve.GetProjectManager().GetCurrentProject()
    if project.GetName() != edit["resolve_project"]:
        raise RuntimeError(f"Open {edit['resolve_project']!r} first")
    if resolve.GetCurrentPage() != "edit":
        resolve.OpenPage("edit")
    previous = project.GetCurrentTimeline()
    media_pool = project.GetMediaPool()
    media_pool.SetCurrentFolder(folder(media_pool, f"{timeline_prefix} graphics" if timeline_prefix else "Graphics"))
    taken = {project.GetTimelineByIndex(index).GetName() for index in range(1, project.GetTimelineCount() + 1)}
    manifest, seconds = [], {}
    for graphic, plan in zip(graphics, plans):
        begin = time.time()
        name = base = f"{timeline_prefix or edit['video']} graphic {graphic['id']} {edit['cut']}"
        number = 2
        while name in taken:
            name, number = f"{base} {number}", number + 1
        taken.add(name)
        g = Graph(graphic_timeline(project, media_pool, name, width, height, plan["frames"]), look, look_folder, width, height,
                  plan["frames"])
        if graphic["kind"] == "photo-grid":
            last = draw_photo_grid(g, graphic, plan)
        elif graphic["kind"] == "photo-panel":
            last = draw_photo_panel(g, graphic, plan)
        elif graphic["kind"] == "closing":
            last = draw_closing(g, graphic, plan)
        else:
            last = g.clear()
        if graphic["content"].get("title"):
            last = draw_title(g, last, graphic["content"]["title"], plan["title_words"])
        g.finish(last)
        manifest.append({"id": graphic["id"], "timeline": name, "timeline_in_frame": plan["start"],
                         "frames": plan["frames"], "slots": plan["slots"]})
        seconds[graphic["id"]] = round(time.time() - begin, 2)
    if previous:
        project.SetCurrentTimeline(previous)
    built_names = {project.GetTimelineByIndex(index).GetName() for index in range(1, project.GetTimelineCount() + 1)}
    missing = [entry["timeline"] for entry in manifest if entry["timeline"] not in built_names]
    if missing or not resolve.GetProjectManager().SaveProject():
        raise RuntimeError(f"Could not save built graphic timelines; missing: {missing}")
    out.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x") as manifest_file:
        manifest_file.write(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    return {"manifest": str(manifest_path), "timelines": [entry["timeline"] for entry in manifest],
            "build_seconds": seconds}


if __name__ == "__main__" or "EDIT_FOLDER" in globals():
    if "EDIT_FOLDER" not in globals():
        import argparse
        parser = argparse.ArgumentParser(description="Build a video's native graphics in Resolve.")
        parser.add_argument("edit_folder", type=Path)
        parser.add_argument("--output", type=Path, help="Manifest path, relative to the edit folder or absolute; refuses overwrite.")
        parser.add_argument("--timeline-prefix", help="Prefix for new graphic timelines and their bin.")
        arguments = parser.parse_args()
        EDIT_FOLDER, OUTPUT_FILE, TIMELINE_PREFIX = arguments.edit_folder, arguments.output, arguments.timeline_prefix
    if "resolve" not in globals():
        import DaVinciResolveScript
        resolve = DaVinciResolveScript.scriptapp("Resolve")
    result = build(resolve, EDIT_FOLDER, globals().get("OUTPUT_FILE"), globals().get("TIMELINE_PREFIX"))
    print(json.dumps(result, indent=1))
    if __name__ == "__main__":
        sys.stdout.flush()
        os._exit(0)

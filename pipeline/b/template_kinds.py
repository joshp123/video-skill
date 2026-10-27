#!/usr/bin/env python3
"""The Signpost look's graphic kinds as Fusion graphs, for make_templates.py: a title over an optional photo, the
opening title, the closing page, a photo card with its pin label, and the highlight round real app pixels. Each function builds its tools on a Template and returns its last
tool and its published inputs (name, tool, input). Values come from the look's look.json; defaults that are a graphic's
own (a title's size and place, the closing page's part positions) are inputs.

Written by AI on 2026-10-25 by Claude Opus 5.5. Opening title, highlight and the closing page's AddressSize added
26 Oct by Claude Opus 5.5 (look and layout, hill-climb stream C).
"""
import build_graphics as bg
import graphic  # set_styled_text
from make_templates import HEIGHT, SOFTNESS_PX_PER_UNIT, WIDTH


def title(t, look, px=78, centre_y=760):
    """A title over an optional photo: lines centred on Position and wrapped inside the look's margins by Text+, words in
    [[ ]] on the pill (the character style graphic.py sets), a soft dark band behind the lines. The default size and
    Position are the codex-switch opening's."""
    values, pill = look["fusion"]["title"], look["subtitles"]["activeWord"]
    face = bg.face_of(look, values["face"])
    centred = dict(VerticalTopCenterBottom=0, VerticalJustificationNew=3, HorizontalLeftCenterRight=0,
                   HorizontalJustificationNew=3)
    last = t.photo("Photo")
    words = t.text("TitleText", values["face"], px, values["color"], values["shadow"], **centred,
                   LayoutWidth=(WIDTH - 2 * values["margin"]) / WIDTH, Center=t.at(WIDTH / 2, centre_y),
                   LineSpacing=values["lineHeight"] * 100 / (t.fusion["linePitchPerSize"] * face["textSizePer100Px"]))
    top, side, bottom = values["pill"]["paddingEm"]
    half_leading = (values["pill"]["lineHeight"] - face["ascentEm"] - face["descentEm"]) / 2
    t.border(words, 4, pill["background"], 2, -5, side, face["ascentEm"] + half_leading + top,
             face["descentEm"] + half_leading + bottom, round_=1)
    styled = words.AddModifier("StyledText", "StyledTextCLS") and words.StyledText.GetConnectedOutput().GetTool()
    styled.SetAttrs({"TOOLS_Name": "Title"})
    t.names.append("Title")
    styled.SetInput("Comments", "Highlight 4=1 3=0")  # on the pill: the pill on, the shadow off (graphic.py reads it)
    graphic.set_styled_text(styled, "A title on two lines,\nwith words on the [[pill]]")
    # The band is a second Text+ on the same words, its own fill off: inside one Text+ the shadow cut into the band.
    band_tool = t.add("TextPlus", "TitleBand", LayoutType=1, Wrap=1, Enabled1=0, Font=words.GetInput("Font"),
                      Style=words.GetInput("Style"), LayoutHeight=words.GetInput("LayoutHeight"), **centred)
    for name in ("StyledText", "Center", "Size", "LayoutWidth", "LineSpacing"):
        band_tool[name].SetExpression(f"TitleText.{name}")
    band = values["band"]
    edge = (band["reach"] - band["softEdge"] / 2) / px
    t.border(band_tool, 5, "rgba(0,0,0,0.85)", 0, -20, 20, face["ascentEm"] + edge, face["descentEm"] + edge - 4 / px,
             Softness=1, SoftnessX=band["softEdge"] / 3.46 / SOFTNESS_PX_PER_UNIT,
             SoftnessY=band["softEdge"] / 3.46 / SOFTNESS_PX_PER_UNIT)
    last = t.over(last, band_tool, name="BandOver")
    last = t.over(last, words, name="TitleOver")
    return last, [("Title", "Title", "Text"), ("Position", "TitleText", "Center"), ("Size", "TitleText", "Size"),
                  ("BandOpacity", "TitleBand", "Alpha5")]


def opening_title(t, look):
    """The title as the video's opening card: the look's opening size, high in the frame, its dark band on."""
    opening = look["fusion"]["title"]["opening"]
    return title(t, look, opening["fontSize"], opening["centreY"])


def closing(t, look):
    """The closing page over the footage: the footage darkens to the look's level, then the plain background; the
    headline, the ask and the address on the look's button fade in. Each part wraps inside the margins; its Position
    (the default is the look's centred group for a one-line headline, a two-line ask and a one-line address) is the
    editor's to move when the words take more or fewer lines."""
    card, fade = look["fusion"]["closing"], look["fusion"]["closing"]["fade"]
    page = bg.closing_layout({"headline": "Headline", "ask": "The ask, / on two lines.", "pill": "owner/repository"},
                             look, WIDTH)  # the default Positions: where the look's layout puts parts of these lines
    background = t.fill(look["background"], name="Background")
    # The fade's timings are inputs (DarkFrames, DarkTo, PlainFrames; the look's values by default): the footage
    # darkens linearly to DarkTo over DarkFrames, then reaches the plain background PlainFrames later. Added 27 Oct by
    # Claude Opus 5.5 (motion, codex-switch run 4), so a video whose phone encode breaks up in the dark phase can
    # shorten it per row.
    t.add("Custom", "Fade", NumberIn1=fade["darkFrames"], NumberIn2=fade["darkTo"], NumberIn3=fade["plainFrames"])
    background.TopLeftAlpha.SetExpression(
        "iif(time < Fade.NumberIn1, time / Fade.NumberIn1 * Fade.NumberIn2, "
        "min(1, Fade.NumberIn2 + (time - Fade.NumberIn1) / Fade.NumberIn3 * (1 - Fade.NumberIn2)))")
    parts = []
    for name, part, lines, (baseline, pitch), colour, shadow in (
            ("Headline", card["headline"], page["head_lines"], page["head"], card["color"], card["shadow"]),
            ("Ask", card["ask"], page["ask_lines"], page["ask"], card["ask"].get("color", card["color"]), card["shadow"]),
            ("Address", card["cta"], page["cta_lines"],
             (page["cta_baseline"], card["cta"]["fontSize"] * card["cta"]["lineHeight"]), card["cta"]["color"], None)):
        parts.append(t.text(f"{name}Text", part["face"], part["fontSize"], colour, shadow, VerticalTopCenterBottom=-1,
                            VerticalJustificationNew=0, HorizontalLeftCenterRight=0, HorizontalJustificationNew=3,
                            LayoutWidth=(page["right"] - page["left"]) / WIDTH, **t.block_inputs(
                                lines, part["face"], part["fontSize"], page["left"], page["right"], baseline, pitch)))
    cta = card["cta"]
    pad_y, pad_x = cta["paddingEm"]
    face = bg.face_of(look, cta["face"])
    half_leading = (cta["lineHeight"] - face["ascentEm"] - face["descentEm"]) / 2
    t.border(parts[2], 4, cta["background"], 0, -5, pad_x, face["ascentEm"] + half_leading + pad_y,
             face["descentEm"] + half_leading + pad_y, round_=1, face_name=cta["face"])
    words = t.over(parts[0], parts[1], name="AskOver")
    words = t.over(words, parts[2], name="AddressOver")
    last = t.over(background, words, name="Page")
    t.animate(last, "Blend", {frame: min(1, (frame + 1) / fade["textFrames"]) for frame in range(fade["textFrames"])})
    published = []
    for name in ("Headline", "Ask", "Address"):
        published += [(name, f"{name}Text", "StyledText"), (f"{name}Position", f"{name}Text", "Center")]
    # A long address fits at a smaller size; a page of fewer parts uses the space with larger headline and ask
    # (HeadlineSize, AskSize added 26 Oct by Claude Opus 5.5, motion on codex-switch run 4; defaults unchanged).
    return last, published + [("AddressSize", "AddressText", "Size"), ("HeadlineSize", "HeadlineText", "Size"),
                              ("AskSize", "AskText", "Size"), ("DarkFrames", "Fade", "NumberIn1"),
                              ("DarkTo", "Fade", "NumberIn2"), ("PlainFrames", "Fade", "NumberIn3")]


def photo_card(t, look):
    """A photo filling the frame with its label at the top left of the safe area: the pin, then the words, on the
    look's dark rounded backing, wrapping inside the frame's margin."""
    label, inset, top = look["fusion"]["photoLabel"], look["fusion"]["photoPanel"]["labelInset"], look["fusion"]["safeArea"]["top"]
    px, face = label["fontSize"], bg.face_of(look, label["face"])
    pad_y, pad_x = label["padding"]
    pin_em = 1 + bg.text_width(" ", px, face) / px  # the pin, one em, and a space before the words
    left = inset + pad_x + pin_em * px
    baseline = top + pad_y + bg.line_box(px, face, px * label["lineHeight"])[0]
    last = t.photo("Photo")
    text = t.text("LabelText", label["face"], px, label["color"], label["shadow"], StyledText="Lisbon",
                  LayoutWidth=(WIDTH - inset - left) / WIDTH, VerticalTopCenterBottom=-1, VerticalJustificationNew=0,
                  HorizontalLeftCenterRight=-1, HorizontalJustificationNew=0,
                  **{key: value for key, value in t.block_inputs(["Lisbon"], label["face"], px, left, WIDTH - inset,
                                                                  baseline, px * label["lineHeight"]).items() if key != "StyledText"})
    half_leading = (label["lineHeight"] - face["ascentEm"] - face["descentEm"]) / 2
    pad = pad_x / px
    t.border(text, 4, label["background"], 0, -20, pad + pin_em / 2, face["ascentEm"] + half_leading + pad_y / px,
             face["descentEm"] + half_leading + pad_y / px, round_=label["borderRadius"] / (px * label["lineHeight"] + 2 * pad_y) * 2,
             face_name=label["face"], right_em=-pin_em / 2)
    last = t.over(last, text, name="LabelOver")
    pin = t.add("Loader", "Pin", Clip=str(t.look_folder / face_images(look)), Depth=bg.LOADER_FLOAT32, PostMultiplyByAlpha=1,
                HoldLastFrame=100000)
    scaled = t.add("Transform", "PinSize", Size=px / bg.image_info(t.look_folder / face_images(look))[0])
    t.link(scaled, "Input", pin)
    image_top = baseline + look["fusion"]["faces"][look["fusion"]["fallbackFace"]]["imageTopEm"] * px
    last = t.over(last, scaled, name="PinOver", Center=t.at(inset + pad_x + px / 2, image_top + px / 2))
    return last, [("Label", "LabelText", "StyledText")]


def highlight(t, look):
    """An outline in the look's orange round a region of real app pixels: its inner edge Padding px outside the region's
    ink box (RegionLeft, RegionTop, RegionRight, RegionBottom: inclusive frame pixels from the top left), the look's
    stroke and corner radius, the radius capped at half the inner height so a one-line region gets a pill."""
    values = look["fusion"]["highlight"]
    stroke, corner = values["strokePx"], values["cornerRadiusPx"]
    region = t.add("Custom", "Region", NumberIn1=480, NumberIn2=900, NumberIn3=599, NumberIn4=959,
                   NumberIn5=values["paddingPx"])
    left, top, right, bottom, padding = (f"Region.NumberIn{n}" for n in range(1, 6))
    masks = {}
    for name, grow in (("Outer", stroke), ("Inner", 0)):
        width = f"({right} + 1 - {left} + 2 * ({padding} + {grow}))"
        height = f"({bottom} + 1 - {top} + 2 * ({padding} + {grow}))"
        radius = f"(min({corner}, ({bottom} + 1 - {top} + 2 * {padding}) / 2) + {grow})"
        mask = t.add("RectangleMask", name, **({"PaintMode": "Subtract"} if grow == 0 else {}))
        mask.Center.SetExpression(f"Point(({left} + {right} + 1) / 2 / {WIDTH}, 1 - ({top} + {bottom} + 1) / 2 / {HEIGHT})")
        mask.Width.SetExpression(f"{width} / {WIDTH}")
        mask.Height.SetExpression(f"{height} / {HEIGHT}")
        mask.CornerRadius.SetExpression(f"min(1, {radius} / (min({width}, {height}) / 2))")
        masks[name] = mask
    t.link(masks["Inner"], "EffectMask", masks["Outer"])
    outline = t.fill(values["colour"], name="Outline")
    t.link(outline, "EffectMask", masks["Inner"])
    return outline, [("RegionLeft", "Region", "NumberIn1"), ("RegionTop", "Region", "NumberIn2"),
                     ("RegionRight", "Region", "NumberIn3"), ("RegionBottom", "Region", "NumberIn4"),
                     ("Padding", "Region", "NumberIn5")]


def face_images(look):
    return next(iter(look["fusion"]["faces"][look["fusion"]["fallbackFace"]]["images"].values()))


KINDS = {"Signpost Title": title, "Signpost Opening": opening_title, "Signpost Closing": closing,
         "Signpost Photo": photo_card, "Signpost Highlight": highlight}

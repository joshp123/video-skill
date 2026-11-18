"""Apply notes to a cut in place, on a duplicate, and bring the edit list in line: no rebuild.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2.

note.py EDIT_LIST --from CUT --to NEW CHANGES.json

Duplicates timeline CUT as NEW (CUT, which Josh may have seen or changed himself, is left alone), makes every change
in CHANGES.json on NEW, writes the same changes into EDIT_LIST (the old list is kept beside it as
edit-list.before-<NEW>.json), and reads NEW back against the new list: exit 0 only when the timeline holds exactly
what the list says, so nothing else moved. Then make NEW's finish timeline with finish.py.

CHANGES.json is a list; each change is one of:
  {"title": INDEX, "inputs": {NAME: VALUE}}           a title's inputs set on its item (a word change: ms)
  {"segment": INDEX, "camera": NAME, "framing"?: {}}  the segment's angle switched (through the timeline file) and
                                                      its framing set; the list's source_in follows the new camera
  {"join": INDEX, "move_s": SECONDS}                  roll the sound join between audio rows INDEX and INDEX + 1 by
                                                      SECONDS (later is positive): both pieces stay in sync with the
                                                      picture; the crossfade moves with it (through the file)
  {"caption": INDEX, "text"?: ..., "start"?: s, "end"?: s, "words"?: [...]}
                                                      a caption retyped or retimed; the caption track is rewritten from
                                                      the list (through the file)
The changes that need the timeline file share one export and import (timeline_file.py). Prints, per change, what it
did and how long it took.
"""
import argparse
import json
import shutil
import time
from pathlib import Path

import graphic
import multicam
import place
import readback
import session
import sound
import timeline_file

LOOKS = place.LOOKS


def set_title_inputs(item, inputs, base):
    comp = item.GetFusionCompByIndex(1)
    macro = graphic.macro_of(comp)
    for key, value in inputs.items():
        tool = comp.FindTool(key)
        if tool and tool.GetAttrs()["TOOLS_RegID"] == "StyledTextCLS":
            graphic.set_styled_text(tool, value)
        elif not macro.SetInput(key, graphic.input_value(value, base, graphic.STAGING / "photos")):
            raise RuntimeError(f"Could not set the title's {key!r}")


def item_at(timeline, kind, track, record):
    start = timeline.GetStartFrame()
    found = [i for i in timeline.GetItemListInTrack(kind, track) or [] if i.GetType() != "transition" and round(i.GetStart() - start) == record]
    if len(found) != 1:
        raise RuntimeError(f"{len(found)} items on {kind} {track} at frame {record}")
    return found[0]


def run(list_path, cut, new, changes):
    data = json.loads(list_path.read_text())
    folder = list_path.parent
    began = time.monotonic()
    resolve, project = session.connect(data["resolve_project"])
    source = session.timeline_named(project, cut)
    if source is None:
        raise ValueError(f"No timeline {cut!r}")
    if session.timeline_named(project, new):
        raise ValueError(f"Timeline {new!r} exists")
    timeline = source.DuplicateTimeline(new)
    if timeline is None:
        raise RuntimeError("DuplicateTimeline failed")
    project.SetCurrentTimeline(timeline)
    done, fps = [], float(data["fps"])
    start = timeline.GetStartFrame()
    angles, captions_changed, crossfades_changed = {}, False, False
    angle_of = None
    try:
        for change in changes:
            t = time.monotonic()
            if "title" in change:
                row = data["titles"][change["title"]]
                set_title_inputs(item_at(timeline, "video", place.TITLES_TRACK, row["record"]), change["inputs"], folder)
                row["inputs"].update(change["inputs"])
                what = f"title {change['title']} inputs {sorted(change['inputs'])}"
            elif "segment" in change:
                row = data["segments"][change["segment"]]
                if angle_of is None:
                    pool_item = place.media_named(project.GetMediaPool(), data["multicam"])
                    angle_of = {d["file"]: (a, d["offset_frames"]) for a, d in multicam.read_angles(resolve, project, pool_item).items()}
                old_file = str((folder / data["cameras"][row["camera"]]["file"]).resolve())
                new_file = str((folder / data["cameras"][change["camera"]]["file"]).resolve())
                angles[row["record"]] = angle_of[new_file][0]
                row["source_in"] += angle_of[old_file][1] - angle_of[new_file][1]  # the same multicam frame, the other camera's own frame
                row["camera"] = change["camera"]
                if "framing" in change:
                    row["framing"] = change["framing"]
                    if not item_at(timeline, "video", place.CAMERAS_TRACK, row["record"]).SetProperties(change["framing"]):
                        raise RuntimeError(f"Could not frame segment {change['segment']}")
                what = f"segment {change['segment']} to {change['camera']}"
            elif "join" in change:
                k, d = change["join"], change["move_s"]
                out_row, in_row = data["audio"][k], data["audio"][k + 1]
                items = sorted((i for i in timeline.GetItemListInTrack("audio", sound.DIALOGUE_TRACK) or [] if i.GetType() != "transition"),
                               key=lambda i: i.GetStart(True))
                cut_frame = start + in_row["record_s"] * fps
                outgoing = next(i for i in items if abs(i.GetEnd(True) - cut_frame) < 1e-3)
                incoming = next(i for i in items if abs(i.GetStart(True) - cut_frame) < 1e-3)
                steps = ((incoming, "left"), (outgoing, "right")) if d > 0 else ((outgoing, "right"), (incoming, "left"))
                for item, side in steps:
                    ok = (item.SetLeftOffset(item.GetLeftOffset(True) + d * fps, True) if side == "left"
                          else item.SetRightOffset(item.GetRightOffset(True) - d * fps, True))
                    if not ok:
                        raise RuntimeError(f"Could not move the {side} edge of the join {k}")
                at = start + (in_row["record_s"] + d) * fps
                has_crossfade = any(i.GetType() == "transition" and i.GetStart(True) < at < i.GetEnd(True)
                                    for i in timeline.GetItemListInTrack("audio", sound.DIALOGUE_TRACK) or [])
                if out_row.get("crossfade_ms") and not has_crossfade and not outgoing.AddTransition(
                        {"type": sound.CROSSFADE, "category": "audio", "position": "end", "alignment": "center", "duration": 2}):
                    raise RuntimeError(f"Could not put the crossfade back at join {k}")  # trimming an edge removes it (17 Nov)
                out_row["source_out_s"] = round(out_row["source_out_s"] + d, 6)
                in_row["source_in_s"] = round(in_row["source_in_s"] + d, 6)
                in_row["record_s"] = round(in_row["record_s"] + d, 6)
                crossfades_changed = True
                what = f"join {k} moved {d * 1000:+.0f} ms"
            elif "caption" in change:
                row = data["captions"][change["caption"]]
                row.update({key: change[key] for key in ("text", "start", "end", "words") if key in change})
                captions_changed = True
                what = f"caption {change['caption']}"
            else:
                raise ValueError(f"Unknown change {change}")
            done.append({"change": what, "seconds": round(time.monotonic() - t, 3)})
        if angles or captions_changed or crossfades_changed:
            t = time.monotonic()
            crossfades = None
            if crossfades_changed:
                crossfades = [{"track": (sound.DIALOGUE_TRACK if x["outgoing"].startswith("piece") else sound.ROOM_TONE_TRACK),
                               "start": (x["at"] - x["length"] / 2) * fps, "length": x["length"] * fps}
                              for x in sound.planned_clips(data, folder)[2]]
            caption_spec = None
            if captions_changed:
                caption_file = folder / "build" / f"captions {new}.json"
                caption_spec = caption_json(data, caption_file)
            timeline, report = timeline_file.rewrite(resolve, project, timeline, folder / "build" / "note" / new, angles=angles or None,
                                                     crossfades=crossfades, captions=caption_spec,
                                                     look_track=LOOKS / data["look"] / "resolve" / "caption-track.drt")
            done.append({"change": "timeline file pass", **{k: v for k, v in report.items() if k != "file"},
                         "seconds": round(time.monotonic() - t, 3)})
        place.name_tracks(timeline)
        session.save(resolve)
    except Exception:
        made = session.timeline_named(project, new)
        if made:
            project.GetMediaPool().DeleteTimelines([made])
        raise
    kept = list_path.with_name(f"{list_path.stem}.before-{new}.json")
    shutil.copyfile(list_path, kept)
    list_path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    if captions_changed:
        shutil.copyfile(folder / "build" / f"captions {new}.json", folder / "build" / "captions.json")
    t = time.monotonic()
    compared = place.compare(resolve, project, new, data, folder)
    return {"timeline": new, "changes": done, "list_before": str(kept),
            "readback_seconds": round(time.monotonic() - t, 2), "seconds": round(time.monotonic() - began, 1), **compared}


def caption_json(data, path):
    """The captions as the template takes them (captions.py), written to PATH."""
    import captions as caption_frames
    tmp = path.with_suffix(".list.json")
    tmp.write_text(json.dumps(data))
    caption_frames.build(tmp, path)
    tmp.unlink()
    return json.loads(path.read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_list", type=Path)
    parser.add_argument("--from", dest="cut", required=True)
    parser.add_argument("--to", dest="new", required=True)
    parser.add_argument("changes", type=Path)
    args = parser.parse_args()
    session.main(lambda: run(args.edit_list.resolve(), args.cut, args.new, json.loads(args.changes.read_text())))

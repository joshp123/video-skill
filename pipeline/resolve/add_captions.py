"""Put the video's captions, styled by the look, onto a timeline's subtitle track: by file, no interface.

Written by AI on 2026-10-22 by Claude Fable 5.1. Audio crossfades, title items and track names kept and checked on
2026-10-26 by Claude Opus 5.5 (stream I of the hill-climb). Audio fades, voice isolation and clip speed kept through the round
trip, and checked, on 2026-10-26 by Claude Opus 5.5 (stream B of the hill-climb): the import set every audio fade to 0
and the check did not look (run 3, builds 1 to 27).
Run through Resolve MCP or external scripting with resolve, EDIT_FOLDER and TIMELINE_NAME; OUTPUT_NAME (default: the
same name) and LOOK_TRACK (default: looks/<look>/resolve/caption-track.drt) optional. Or from a shell:
add_captions.py EDIT_FOLDER TIMELINE_NAME [--output-name NAME] [--look-track FILE].

Exports the timeline as a .drt into build/caption-tracks/<timeline>/, writes the look's caption track holding
build/captions.json into that file (pipeline/subtitles/write_caption_track.py), imports the file back as a new
timeline, sets each audio item's fades and voice isolation back as they were, and checks it: every caption's text and
frames read back; every video and audio item keeps its name, place, length, media pool item, source start, framing,
speed and retime, fades, voice isolation and grade node count. With the same output name the original is deleted once the
checks pass (so run it on the fresh build, or on a duplicate when a note changes the captions: a timeline Josh has
seen is never changed); with another name both stay. Captions already on the timeline are replaced.
"""
import json
import os
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path("/Volumes/Josh Extreme Pro USB4 4TB/Media/Edits/pipeline")
sys.path.insert(0, str(PIPELINE / "subtitles"))
import write_caption_track as caption_track


def timeline_named_id(timeline):
    return timeline.GetUniqueId() if hasattr(timeline, "GetUniqueId") else timeline.GetName()


def timeline_named(project, name):
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t.GetName() == name:
            return t
    return None


FRAMING_KEYS = ("ZoomX", "ZoomY", "Pan", "Tilt", "CropLeft", "CropRight", "CropTop", "CropBottom")
SETTING_KEYS = ("useCustomSettings", "timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight", "useInverseDRT",
                "colorScienceMode", "colorSpaceTimeline", "colorSpaceOutput")


def audio_state(item):
    """What the .drt import drops from an audio item: its fades and its voice isolation."""
    isolation = item.GetVoiceIsolationState() or {}
    return (tuple(sorted(item.GetFades().items())), bool(isolation.get("isEnabled")), isolation.get("amount"))


def video_state(item):
    return ((item.GetSpeed() or {}).get("Percentage"), item.GetProperty("RetimeProcess"))


def items_snapshot(timeline):
    """Every video and audio item: name, place, length, media pool item, source start, framing, grade node count, and
    its speed and retime (video) or its fades and voice isolation (audio). An audio crossfade is its type and its
    sub-frame start and end."""
    out = {}
    for kind in ("video", "audio"):
        for index in range(1, timeline.GetTrackCount(kind) + 1):
            rows = []
            for item in timeline.GetItemListInTrack(kind, index) or []:
                if item.GetType() == "transition":
                    rows.append((item.GetName(), item.GetStart(True), item.GetEnd(True), None, None, None, None, "transition"))
                    continue
                media = item.GetMediaPoolItem()
                try:
                    nodes = item.GetNodeGraph().GetNumNodes()
                except Exception:
                    nodes = None
                framing = tuple(item.GetProperty(k) for k in FRAMING_KEYS) if kind == "video" else None
                state = video_state(item) if kind == "video" else audio_state(item)
                rows.append((item.GetName(), int(item.GetStart()), int(item.GetDuration()),
                             media.GetUniqueId() if media else None, int(item.GetLeftOffset()), framing, nodes, state))
            out[f"{kind} {index}"] = rows
    return out


def track_names(timeline):
    return {(kind, index): timeline.GetTrackName(kind, index) for kind in ("video", "audio", "subtitle")
            for index in range(1, timeline.GetTrackCount(kind) + 1)}


def set_track_names(timeline, names):
    """A .drt import keeps track names or not; set them as they were either way."""
    for (kind, index), name in names.items():
        if index <= timeline.GetTrackCount(kind) and timeline.GetTrackName(kind, index) != name and not timeline.SetTrackName(kind, index, name):
            raise RuntimeError(f"could not name {kind} track {index} {name!r}")


def settings_snapshot(timeline):
    s = timeline.GetSettings() or {}
    return {k: str(s.get(k)) for k in SETTING_KEYS}


def captions_snapshot(timeline):
    start = timeline.GetStartFrame()
    out = []
    for index in range(1, timeline.GetTrackCount("subtitle") + 1):
        for item in timeline.GetItemListInTrack("subtitle", index) or []:
            out.append((item.GetName().replace(" ", "\n"), int(item.GetStart()) - start, int(item.GetEnd()) - start))
    return out


def restore_audio_states(timeline, states):
    """Set each audio item's fades and voice isolation to what it was before the round trip, track by track in order."""
    for track, rows in states.items():
        items = sorted(timeline.GetItemListInTrack("audio", track) or [], key=lambda item: item.GetStart(True))
        if len(items) != len(rows):
            raise RuntimeError(f"audio {track}: {len(items)} items after the import, {len(rows)} before")
        for item, state in zip(items, rows):
            if state == "transition":
                continue
            fades, isolated, amount = state
            if dict(fades) != item.GetFades() and not item.SetFades(dict(fades)):
                raise RuntimeError(f"audio {track}: SetFades refused {dict(fades)}")
            if isolated and not item.SetVoiceIsolationState({"isEnabled": True, "amount": amount}):
                raise RuntimeError(f"audio {track}: voice isolation could not be set back")


def run(resolve, edit_folder, timeline_name, output_name=None, look_track=None):
    """The video folder's build/captions.json onto the timeline, with the look named in edit/edit.json."""
    edit_folder = Path(edit_folder)
    edit = json.loads((edit_folder / "edit" / "edit.json").read_text())
    look_track = Path(look_track) if look_track else edit_folder.parent / "looks" / edit["look"] / "resolve" / "caption-track.drt"
    project = resolve.GetProjectManager().GetCurrentProject()
    if project.GetName() != edit["resolve_project"]:
        raise RuntimeError(f"open project is {project.GetName()!r}, the edit data says {edit['resolve_project']!r}")
    spec = json.loads((edit_folder / "build" / "captions.json").read_text())
    return put_captions(resolve, timeline_name, spec, look_track, edit_folder / "build" / "caption-tracks", output_name)


def put_captions(resolve, timeline_name, spec, look_track, work_folder, output_name=None):
    """Captions ({fps, captions}, as captions.py writes them) onto the timeline through a .drt round trip."""
    output_name = output_name or timeline_name
    look_track = Path(look_track)
    if not look_track.exists():
        raise FileNotFoundError(f"the look has no caption track: {look_track}")
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    media_pool = project.GetMediaPool()
    source = timeline_named(project, timeline_name)
    if source is None:
        raise RuntimeError(f"no timeline named {timeline_name!r}")
    if output_name != timeline_name and timeline_named(project, output_name):
        raise RuntimeError(f"a timeline named {output_name!r} exists")
    fps = float(source.GetSetting("timelineFrameRate"))
    if fps != float(spec["fps"]):
        raise RuntimeError(f"timeline runs at {fps} fps, the captions were built at {spec['fps']}")
    start = source.GetStartFrame()
    folder = Path(work_folder) / timeline_name.replace("/", "_")
    folder.mkdir(parents=True, exist_ok=True)
    exported, captioned = folder / "exported.drt", folder / "with-captions.drt"
    fresh = folder / "writing-exported.drt"
    if not source.Export(str(fresh), resolve.EXPORT_DRT, resolve.EXPORT_NONE) or not fresh.exists():
        raise RuntimeError("Timeline.Export failed")
    os.replace(fresh, exported)
    written = caption_track.write_caption_track(str(exported), str(look_track), spec["captions"], fps, start, str(captioned))
    expected_captions = [(c["text"],) + tuple(f - start for f in caption_track.caption_frames(c, fps, start)[:2]) for c in spec["captions"]]
    before = items_snapshot(source)
    audio_states = {int(track.split()[1]): [row[7] for row in rows] for track, rows in before.items() if track.startswith("audio")}
    settings_before = settings_snapshot(source)
    names_before = track_names(source)
    timelines_before = {timeline_named_id(project.GetTimelineByIndex(i)) for i in range(1, project.GetTimelineCount() + 1)}

    if output_name == timeline_name:
        if not source.SetName(f"{timeline_name} (before captions)"):
            raise RuntimeError("could not rename the source timeline")
    imported = media_pool.ImportTimelineFromFile(str(captioned), {"importSourceClips": False})
    # Everything the import added, the timeline it returned included: a wrong import can add nested ones too.
    added = [t for t in (project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1))
             if timeline_named_id(t) not in timelines_before]
    if not imported:
        if added:
            media_pool.DeleteTimelines(added)
        source.SetName(timeline_name)
        raise RuntimeError("ImportTimelineFromFile failed")
    try:
        if imported.GetName() != output_name and not imported.SetName(output_name):
            raise RuntimeError(f"could not name the imported timeline {output_name!r}")
        restore_audio_states(imported, audio_states)
        set_track_names(imported, {key: name for key, name in names_before.items() if key[0] != "subtitle"})
        got_captions = captions_snapshot(imported)
        after = items_snapshot(imported)
        faults = []
        if got_captions != expected_captions:
            missing = [c for c in expected_captions if c not in got_captions]
            extra = [c for c in got_captions if c not in expected_captions]
            faults.append(f"captions differ: {len(got_captions)} read back for {len(expected_captions)}; missing {missing[:3]}; extra {extra[:3]}")
        for track, rows in before.items():
            got = after.get(track, [])
            if [r[:6] for r in rows] != [r[:6] for r in got]:
                faults.append(f"{track}: items, source starts or framing differ: before {rows[:2]} after {got[:2]}")
            elif [r[7] for r in rows] != [r[7] for r in got]:
                changed = [(b, a) for b, a in zip(rows, got) if b[7] != a[7]]
                faults.append(f"{track}: speed, fades or voice isolation differ: {changed[:2]}")
            elif [r[6] for r in rows] != [r[6] for r in got]:
                faults.append(f"{track}: grade node counts differ: before {[r[6] for r in rows]} after {[r[6] for r in got]}")
        settings_after = settings_snapshot(imported)
        names_after = track_names(imported)
        if any(names_after.get(key) != name for key, name in names_before.items() if key[0] != "subtitle"):
            faults.append(f"track names differ: {names_before} -> {names_after}")
        if settings_after != settings_before:
            faults.append(f"timeline settings differ: {settings_before} -> {settings_after}")
        if len(added) != 1:
            faults.append(f"the import added {len(added)} timelines, expected 1: {[t.GetName() for t in added]}")
        if faults:
            raise RuntimeError("; ".join(faults))
    except Exception:
        media_pool.DeleteTimelines(added or [imported])
        if output_name == timeline_name:
            source.SetName(timeline_name)
        raise
    if output_name == timeline_name:
        if not media_pool.DeleteTimelines([source]):
            raise RuntimeError("the captioned timeline is in place but the original could not be deleted")
    project.SetCurrentTimeline(imported)
    manager.SaveProject()
    return {"timeline": output_name, "captions": len(got_captions), "words": sum(len(c["words"]) for c in spec["captions"]),
            "tracks_checked": list(before), "settings_checked": list(SETTING_KEYS), "framing_checked": list(FRAMING_KEYS),
            "exported": str(exported), "with_captions": str(captioned), "replaced_original": output_name == timeline_name}


if "resolve" in globals() and "EDIT_FOLDER" in globals():
    result = run(resolve, EDIT_FOLDER, TIMELINE_NAME, globals().get("OUTPUT_NAME"), globals().get("LOOK_TRACK"))
    print(result)
elif __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("edit_folder")
    parser.add_argument("timeline_name")
    parser.add_argument("--output-name")
    parser.add_argument("--look-track")
    args = parser.parse_args()
    import DaVinciResolveScript
    print(run(DaVinciResolveScript.scriptapp("Resolve"), args.edit_folder, args.timeline_name, args.output_name, args.look_track))

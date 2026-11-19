"""What only Resolve's timeline file reaches: each crossfade's sub-frame start and length, and the captions with each
word's time. One export, one rewrite, one import.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2; the multicam angle removed and the
snapshot helpers of resolve/add_captions.py folded in on 2026-11-19 (Claude Opus 5.5), when the cameras became two
tracks.

On 21.2 no script call gives a crossfade a sub-frame start or length (AddTransition takes whole frames; a two-frame
one centres on a sub-frame edit, a one-frame one does not; a placed transition cannot be moved or trimmed), and none
creates a caption, sets its text or its word times. The timeline's .drt holds both. So: export the timeline, rewrite
those parts of its file, import it as a new timeline, put back what the import drops (every audio fade, voice
isolation, track names, a disabled clip's colour group), check that every video and audio item kept its place, length,
source, framing, grade node count, colour group and enabled state, read the rewritten parts back, and only then delete the original and give the new one its
name. On any fault the import is deleted and the original keeps its name.

The import is a new timeline, so it has no render cache: every cached frame is worked out again, at the next render or
in the background (tested 19 Nov on the Mac mini: a cached 300-frame render took 3.2 s on the original, 49.3 s on its
import). Use it on a new build before the cache is filled, and after that only when nothing else will do.
"""
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "subtitles"))
import write_caption_track as caption_track  # noqa: E402

TRANSITION = re.compile(r"<Sm2TiTransition\b.*?</Sm2TiTransition>", re.S)
TRACK = re.compile(r"<Sm2TiTrack\b.*?</Sm2TiTrack>", re.S)
FRAMING_KEYS = ("ZoomX", "ZoomY", "Pan", "Tilt", "CropLeft", "CropRight", "CropTop", "CropBottom")
# Not useCustomSettings: on 21.2 an API-made timeline lacks the key and its imported copy reads "1" (17 Nov).
SETTING_KEYS = ("timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight", "useInverseDRT",
                "colorScienceMode", "colorSpaceTimeline", "colorSpaceOutput")


def entries_of(path):
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def write_drt(entries, path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


def export(resolve, timeline, path):
    """The timeline's .drt at PATH, and its entries."""
    path = Path(path)
    fresh = path.with_name("writing-" + path.name)
    if not timeline.Export(str(fresh), resolve.EXPORT_DRT, resolve.EXPORT_NONE):
        raise RuntimeError(f"Export of {timeline.GetName()!r} failed")
    os.replace(fresh, path)
    return entries_of(path)


def frames_text(value):
    """A frame count as the .drt writes it: whole, or whole|little-endian double of the fraction."""
    whole = int(value // 1)
    fraction = value - whole
    return f"{whole}|{struct.pack('<d', fraction).hex()}" if fraction > 1e-9 else str(whole)


def frames_value(text):
    if "|" in text:
        whole, hexed = text.split("|")
        return int(whole) + struct.unpack("<d", bytes.fromhex(hexed))[0]
    return float(text)


def with_whole_start(blob_hex, whole):
    """A transition's FieldsBlob holds its whole start frame in field 21 (October, 21.1); 21.2 may compress the blob."""
    payload = caption_track.decode_blob(blob_hex)
    assert payload[0] == 0x0a, payload[:4].hex()
    i = payload.index(b"\xa8\x01")
    _, end = caption_track.read_varint(payload, i + 2)
    new = bytearray(payload[:i + 2] + caption_track.write_varint(whole) + payload[end:])
    new[1] += len(new) - len(payload)
    return caption_track.encode_blob(bytes(new))


def set_crossfades(sequence, crossfades, start):
    """Each {track, start, length} given (frames from the timeline's first): that track's transitions, in order, take
    exactly these."""
    vec = re.search(r"<AudioTrackVec>.*?</AudioTrackVec>", sequence, re.S)[0]
    new_vec = vec
    for index, track in enumerate(TRACK.findall(vec), 1):
        wanted = sorted((x for x in crossfades if x["track"] == index), key=lambda x: x["start"])
        found = sorted(TRANSITION.findall(track), key=lambda t: frames_value(re.search(r"<Start>(.*?)</Start>", t)[1]))
        if len(wanted) != len(found):
            raise RuntimeError(f"A{index}: {len(found)} transitions in the file, {len(wanted)} crossfades wanted")
        changed = track
        for element, x in zip(found, wanted):
            first = start + x["start"]
            new = re.sub(r"<Start>.*?</Start>", f"<Start>{frames_text(first)}</Start>", element, count=1)
            new = re.sub(r"<Duration>.*?</Duration>", f"<Duration>{frames_text(x['length'])}</Duration>", new, count=1)
            blob = re.search(r"<FieldsBlob>([0-9a-f]+)</FieldsBlob>", new)[1]
            changed = changed.replace(element, new.replace(blob, with_whole_start(blob, int(first // 1))), 1)
        new_vec = new_vec.replace(track, changed, 1)
    return sequence.replace(vec, new_vec, 1)


def own_sequence(entries, timeline_name):
    """The .drt's own timeline sequence: the one the media pool entry of the exported timeline points at."""
    folder = next(data.decode() for name, data in entries.items() if name.endswith("MpFolder.xml"))
    clips = re.findall(r"<Sm2MpTimelineClip .*?</Sm2MpTimelineClip>", folder, re.S)
    if len(clips) > 1:
        clips = [c for c in clips if re.search(r"<Name>(.*?)</Name>", c)[1] == timeline_name]
    [clip] = clips
    exported = re.search(r'<Sm2Sequence DbId="([0-9a-f-]+)"', clip)[1]
    [name] = [n for n, data in entries.items() if n.startswith("SeqContainer/") and f"<Sequence>{exported}</Sequence>" in data.decode()]
    return name


def items(timeline):
    """Every video and audio item but the transitions: name, place, length, media, source start, framing, grade node
    count, colour group, and its speed and retime (video) or its fades and voice isolation (audio)."""
    out = {}
    for kind in ("video", "audio"):
        for index in range(1, timeline.GetTrackCount(kind) + 1):
            rows = []
            for item in timeline.GetItemListInTrack(kind, index) or []:
                if item.GetType() == "transition":
                    continue
                media, graph, group = item.GetMediaPoolItem(), item.GetNodeGraph(), item.GetColorGroup()
                if kind == "video":
                    state = (tuple(item.GetProperty(k) for k in FRAMING_KEYS), (item.GetSpeed() or {}).get("Percentage"),
                             item.GetProperty("RetimeProcess"), graph.GetNumNodes() if graph else None,
                             group.GetName() if group else None, item.GetClipEnabled())
                else:
                    isolation = item.GetVoiceIsolationState() or {}
                    state = (tuple(sorted(item.GetFades().items())), bool(isolation.get("isEnabled")), isolation.get("amount"))
                rows.append((item.GetName(), round(item.GetStart(True), 4), round(item.GetEnd(True), 4),
                             media.GetUniqueId() if media else None, round(item.GetLeftOffset(True), 4), state))
            out[f"{kind} {index}"] = rows
    return out


def track_names(timeline):
    return {(kind, index): timeline.GetTrackName(kind, index) for kind in ("video", "audio", "subtitle")
            for index in range(1, timeline.GetTrackCount(kind) + 1)}


def set_track_names(timeline, names):
    for (kind, index), name in names.items():
        if index <= timeline.GetTrackCount(kind) and timeline.GetTrackName(kind, index) != name and not timeline.SetTrackName(kind, index, name):
            raise RuntimeError(f"could not name {kind} track {index} {name!r}")


def transitions(timeline):
    start = timeline.GetStartFrame()
    return sorted((track, round(item.GetStart(True) - start, 4), round(item.GetEnd(True) - item.GetStart(True), 4))
                  for track in range(1, timeline.GetTrackCount("audio") + 1)
                  for item in timeline.GetItemListInTrack("audio", track) or [] if item.GetType() == "transition")


def captions_on(timeline):
    start = timeline.GetStartFrame()
    return [(" ".join(item.GetName().split()), int(item.GetStart()) - start, int(item.GetEnd()) - start)
            for index in range(1, timeline.GetTrackCount("subtitle") + 1)
            for item in timeline.GetItemListInTrack("subtitle", index) or []]


def put_audio_back(timeline, before):
    """Each audio item's fades and voice isolation as they were (the import sets every fade to 0)."""
    for track, rows in before.items():
        if not track.startswith("audio"):
            continue
        placed = sorted((i for i in timeline.GetItemListInTrack("audio", int(track.split()[1])) or [] if i.GetType() != "transition"),
                        key=lambda i: i.GetStart(True))
        if len(placed) != len(rows):
            raise RuntimeError(f"{track}: {len(placed)} items after the import, {len(rows)} before")
        for item, row in zip(placed, rows):
            fades, isolated, amount = row[5]
            if dict(fades) != item.GetFades() and not item.SetFades(dict(fades)):
                raise RuntimeError(f"{track}: SetFades refused {dict(fades)}")
            if isolated and not item.SetVoiceIsolationState({"isEnabled": True, "amount": amount}):
                raise RuntimeError(f"{track}: voice isolation could not be set back")


def put_video_back(project, timeline, before):
    """Each video item's colour group and enabled state as they were: the import drops a disabled clip's group."""
    groups = {g.GetName(): g for g in project.GetColorGroupsList() or []}
    for track, rows in before.items():
        if not track.startswith("video"):
            continue
        placed = [i for i in timeline.GetItemListInTrack("video", int(track.split()[1])) or [] if i.GetType() != "transition"]
        for item, row in zip(placed, rows):
            group, enabled = row[5][4], row[5][5]
            if item.GetClipEnabled() != enabled:
                item.SetClipEnabled(enabled)
            now = item.GetColorGroup()
            if group and (now is None or now.GetName() != group):
                item.AssignToColorGroup(groups[group])


def rewrite(resolve, project, timeline, work, crossfades=None, captions=None, look_track=None):
    """Rewrite TIMELINE through its file and put the result in its place, under its name. crossfades: [{track, start,
    length}] in frames from the timeline's first, one per transition already on that track. captions: the whole caption
    track as captions.py writes it ({fps, captions}), styled by LOOK_TRACK. Returns (the new timeline, report)."""
    pool, name, start = project.GetMediaPool(), timeline.GetName(), timeline.GetStartFrame()
    fps = float(timeline.GetSettings()["timelineFrameRate"])
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    entries = export(resolve, timeline, work / "exported.drt")
    sequence_name = own_sequence(entries, name)
    if crossfades is not None:
        entries[sequence_name] = set_crossfades(entries[sequence_name].decode(), crossfades, start).encode()
    rewritten = work / "rewritten.drt"
    write_drt(entries, rewritten)
    if captions is not None:
        if float(captions["fps"]) != fps:
            raise RuntimeError(f"Captions built at {captions['fps']} fps, the timeline runs at {fps}")
        captioned = work / "with-captions.drt"
        caption_track.write_caption_track(str(rewritten), str(look_track), captions["captions"], fps, start, str(captioned))
        rewritten = captioned
    before, names = items(timeline), track_names(timeline)
    settings = {k: str((timeline.GetSettings() or {}).get(k)) for k in SETTING_KEYS}
    captions_before, transitions_before = captions_on(timeline), transitions(timeline)
    ids = {project.GetTimelineByIndex(i).GetUniqueId() for i in range(1, project.GetTimelineCount() + 1)}
    if not timeline.SetName(f"{name} (before file pass)"):
        raise RuntimeError("Could not rename the timeline before the file pass")
    try:
        imported = pool.ImportTimelineFromFile(str(rewritten), {"importSourceClips": False})
        if not imported or not imported.SetName(name):
            raise RuntimeError(f"Import of the rewritten timeline failed or could not be named {name!r}")
        set_track_names(imported, names)
        put_audio_back(imported, before)
        put_video_back(project, imported, before)
        after = items(imported)
        faults = [f"{track} changed: {[(b, a) for b, a in zip(before[track], after.get(track, [])) if b != a][:2]}"
                  for track in before if before[track] != after.get(track)]
        if {k: str((imported.GetSettings() or {}).get(k)) for k in SETTING_KEYS} != settings:
            faults.append("timeline settings changed")
        if project.GetTimelineCount() != len(ids) + 1:
            faults.append("the import added more than one timeline")
        report = {"timeline": name, "file": str(rewritten)}
        got = transitions(imported)
        if crossfades is not None:
            wanted = sorted((x["track"], x["start"], x["length"]) for x in crossfades)
            off = [(w, g) for w, g in zip(wanted, got) if w[0] != g[0] or abs(w[1] - g[1]) > 1e-3 or abs(w[2] - g[2]) > 1e-3]
            if len(wanted) != len(got) or off:
                faults.append(f"crossfades read back differently: {off[:3]}")
            report["crossfades"] = len(wanted)
        elif got != transitions_before:
            faults.append("crossfades changed")
        if captions is not None:
            expected = [(" ".join(c["text"].split()),) + tuple(f - start for f in caption_track.caption_frames(c, fps, start)[:2]) for c in captions["captions"]]
            if captions_on(imported) != expected:
                faults.append(f"captions read back differently: {[(e, g) for e, g in zip(expected, captions_on(imported)) if e != g][:3]}")
            report["captions"] = len(expected)
        elif captions_on(imported) != captions_before:
            faults.append("captions changed")
        if faults:
            raise RuntimeError("; ".join(faults))
    except Exception:
        added = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetUniqueId() not in ids]
        if added:
            pool.DeleteTimelines(added)
        timeline.SetName(name)
        raise
    if not pool.DeleteTimelines([timeline]):
        raise RuntimeError("The rewritten timeline is in place but the original could not be deleted")
    project.SetCurrentTimeline(imported)
    return imported, report

"""What only Resolve's timeline file reaches, set in one export and one import: segment angles, crossfade geometry, and
captions with each word's time.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2. It folds October's three round trips
(multicam.set_angles, sound.py's crossfades, add_captions.put_captions) into one.

On 21.2 no script call sets a multicam item's angle, gives a crossfade a sub-frame start or length (`AddTransition` takes
whole frames, a one-frame one is not centred, and the transition item cannot be moved or trimmed: tested 17 Nov), or
writes a caption or its word times. The timeline's .drt holds all three. So: export the timeline, rewrite those parts
of its file, import the file as a new timeline, put back what the import drops (every audio fade, voice isolation,
track names), check that every video and audio item kept its place, length, source and framing, read the rewritten
parts back, and only then delete the original and give the new one its name. On any fault the import is deleted and
the original keeps its name.
"""
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

import multicam

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "subtitles"))
import write_caption_track as caption_track  # noqa: E402

add_captions = multicam.add_captions  # the item, setting and track-name snapshots
TRANSITION = re.compile(r"<Sm2TiTransition\b.*?</Sm2TiTransition>", re.S)


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


def audio_tracks(sequence):
    vec = re.search(r"<AudioTrackVec>.*?</AudioTrackVec>", sequence, re.S)[0]
    return vec, multicam.TRACK.findall(vec)


def set_crossfades(sequence, crossfades, start):
    """Each {track, start_s, length_s} given: the transitions of that track, in order, take exactly these."""
    vec, tracks = audio_tracks(sequence)
    new_vec = vec
    for index, track in enumerate(tracks, 1):
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


def snapshot(timeline, angles_change, names=None):
    """Every video and audio item but the crossfades (checked on their own), the settings, and the track names (those
    of NAMES' keys: the caption pass adds a subtitle track)."""
    items = {k: [row for row in rows if row[7] != "transition"] for k, rows in add_captions.items_snapshot(timeline).items()}
    if angles_change:  # a multicam item's name carries its angle
        items = {k: [row[1:] for row in rows] for k, rows in items.items()}
    track_names = add_captions.track_names(timeline)
    return {"items": items, "settings": add_captions.settings_snapshot(timeline),
            "names": {key: track_names.get(key) for key in (names or track_names)}}


def transitions_read(timeline):
    start = timeline.GetStartFrame()
    return sorted((track, item.GetStart(True) - start, item.GetEnd(True) - item.GetStart(True))
                  for track in range(1, timeline.GetTrackCount("audio") + 1)
                  for item in timeline.GetItemListInTrack("audio", track) or [] if item.GetType() == "transition")


def rewrite(resolve, project, timeline, work, angles=None, crossfades=None, captions=None, look_track=None, new_name=None):
    """Rewrite TIMELINE through its file. angles: {record frame: "Camera N"} for the multicam items on V2. crossfades:
    [{track, start, length}] in timeline frames from its first frame, one per transition already on that track.
    captions: the whole caption track, as captions.py writes it ({fps, captions}), styled by LOOK_TRACK. The result
    replaces TIMELINE under its name, or is a new timeline NEW_NAME beside it. Returns (timeline, report)."""
    pool, name, start = project.GetMediaPool(), timeline.GetName(), timeline.GetStartFrame()
    fps = float(timeline.GetSettings()["timelineFrameRate"])
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    entries = multicam.exported_entries(resolve, timeline, work / "exported.drt")
    sequence_name = multicam.outer_sequence(entries, name)
    sequence = entries[sequence_name].decode()
    if angles:
        clips = multicam.video_clips(sequence, 2)
        records = {multicam.record_of(clip, start): clip for clip in clips}
        missing = sorted(set(angles) - set(records))
        if missing:
            raise RuntimeError(f"No multicam item on V2 at records {missing[:5]}")
        for record, angle in angles.items():
            sequence = sequence.replace(records[record], multicam.with_angle(records[record], angle), 1)
    if crossfades is not None:
        sequence = set_crossfades(sequence, crossfades, start)
    entries[sequence_name] = sequence.encode()
    rewritten = work / "rewritten.drt"
    multicam.write_drt(entries, rewritten)
    if captions is not None:
        if float(captions["fps"]) != fps:
            raise RuntimeError(f"Captions built at {captions['fps']} fps, the timeline runs at {fps}")
        captioned = work / "with-captions.drt"
        caption_track.write_caption_track(str(rewritten), str(look_track), captions["captions"], fps, start, str(captioned))
        rewritten = captioned
    before = snapshot(timeline, bool(angles))
    audio_states = {int(track.split()[1]): [row[7] for row in rows]
                    for track, rows in add_captions.items_snapshot(timeline).items() if track.startswith("audio")}
    captions_before = add_captions.captions_snapshot(timeline)
    transitions_before = transitions_read(timeline)
    ids = {project.GetTimelineByIndex(i).GetUniqueId() for i in range(1, project.GetTimelineCount() + 1)}
    final = new_name or name
    if new_name is None and not timeline.SetName(f"{name} (before file pass)"):
        raise RuntimeError("Could not rename the timeline before the file pass")
    imported = None
    try:
        imported = pool.ImportTimelineFromFile(str(rewritten), {"importSourceClips": False})
        if not imported or (imported.GetName() != final and not imported.SetName(final)):
            raise RuntimeError(f"Import of the rewritten timeline failed or could not be named {final!r}")
        add_captions.set_track_names(imported, before["names"])
        add_captions.restore_audio_states(imported, audio_states)
        after = snapshot(imported, bool(angles), before["names"])
        faults = [f"{part} changed" for part in ("items", "settings", "names") if before[part] != after[part]]
        if faults and before["items"] != after["items"]:
            diff = [(track, b, a) for track in before["items"] for b, a in zip(before["items"][track], after["items"].get(track, [])) if b != a]
            faults.append(f"first item differences: {diff[:3]}")
        if project.GetTimelineCount() != len(ids) + 1:
            faults.append("the import added more than one timeline")
        report = {"timeline": final, "file": str(rewritten)}
        if angles:
            got = multicam.item_angles(multicam.exported_entries(resolve, imported, work / "readback.drt"), 2, start, final)
            wrong = [r for r in angles if got.get(r) != angles[r]]
            if wrong:
                faults.append(f"angles read back wrong at records {wrong[:5]}")
            report["angles"] = len(angles)
        got_transitions = transitions_read(imported)
        if crossfades is not None:
            wanted = sorted((x["track"], x["start"], x["length"]) for x in crossfades)
            off = [(w, g) for w, g in zip(wanted, got_transitions)
                   if w[0] != g[0] or abs(w[1] - g[1]) > 1e-4 or abs(w[2] - g[2]) > 1e-4]
            if len(wanted) != len(got_transitions) or off:
                faults.append(f"crossfades read back differently: {off[:3]}")
            report["crossfades"] = len(wanted)
        elif got_transitions != transitions_before:
            faults.append("crossfades changed")
        if captions is not None:
            expected = [(c["text"],) + tuple(f - start for f in caption_track.caption_frames(c, fps, start)[:2])
                        for c in captions["captions"]]
            got = add_captions.captions_snapshot(imported)
            if got != expected:
                faults.append(f"captions read back differently: {[(e, g) for e, g in zip(expected, got) if e != g][:3]}")
            report["captions"] = len(got)
        elif add_captions.captions_snapshot(imported) != captions_before:
            faults.append("captions changed")
        if faults:
            raise RuntimeError("; ".join(faults))
    except Exception:
        added = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetUniqueId() not in ids]
        if added:
            pool.DeleteTimelines(added)
        if new_name is None:
            timeline.SetName(name)
        raise
    if new_name is None and not pool.DeleteTimelines([timeline]):
        raise RuntimeError("The rewritten timeline is in place but the original could not be deleted")
    project.SetCurrentTimeline(imported)
    return imported, report

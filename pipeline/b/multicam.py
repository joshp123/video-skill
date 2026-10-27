"""The cameras as one Resolve multicam clip: make it, read its angles, and set each segment's angle through the .drt.

Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream I), from stream E's proven route (E-report.md).

Resolve's API can neither set a multicam item's angle nor reach inside a multicam; a timeline's .drt file can:
- the multicam's own sequence is the one whose tracks carry an `AngleId` ("Camera N"); each angle track holds one clip,
  its camera file (`MediaFilePath`), starting at the angle's offset in multicam frames (`Start`);
- each multicam item on the timeline holds its active angle in its `FieldsBlob` as 0x1a, length, "Camera N".
The API reads the angle back: an item's name is "<multicam> - <the angle's clip name>".
"""
import importlib.util
import os
import re
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('add_captions', Path(__file__).resolve().parents[1] / 'resolve/add_captions.py')
add_captions = importlib.util.module_from_spec(spec)  # the item, setting and track-name snapshots its round trip checks with
spec.loader.exec_module(add_captions)

ANGLE_IN_ITEM = re.compile(rb'\x1a\x08(Camera \d)')
CLIP = re.compile(r'<Sm2TiVideoClip .*?</Sm2TiVideoClip>', re.S)
TRACK = re.compile(r'<Sm2TiTrack\b.*?</Sm2TiTrack>', re.S)
CACHE = Path(__file__).resolve().parents[2] / '.cache/pipeline-b/multicam'


def make(resolve, pool, camera_media, name):
    """One multicam of the camera clips, synced by their own sound. The lav stays out: as an angle it is black."""
    made = pool.CreateMulticamClip(list(camera_media), {
        'name': name, 'startTimecode': '00:00:00:00', 'frameRate': float(camera_media[0].GetClipProperty('FPS')),
        'angleSyncMode': resolve.MULTICAM_ANGLE_SYNC_AUDIO, 'multicamAudioMode': resolve.MULTICAM_AUDIO_SOURCE,
        'angleNameMode': resolve.MULTICAM_ANGLE_NAME_CLIP, 'useFullClipExtents': True, 'createBinForSourceClips': False})
    if not made:
        raise RuntimeError(f'CreateMulticamClip failed for {name!r}')
    return made[0]


def drt_entries(path):
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def write_drt(entries, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


def exported_entries(resolve, timeline, path):
    fresh = path.with_name('writing-' + path.name)
    if not timeline.Export(str(fresh), resolve.EXPORT_DRT, resolve.EXPORT_NONE):
        raise RuntimeError(f'Export of {timeline.GetName()!r} failed')
    os.replace(fresh, path)
    return drt_entries(path)


def track_angle(track_xml):
    """A multicam track's angle: its FieldsBlob holds "AngleId" then "Camera N", both UTF-16."""
    blob = bytes.fromhex(re.search(r'<FieldsBlob>([0-9a-f]*)</FieldsBlob>', track_xml)[1])
    found = re.search('AngleId'.encode('utf-16-be') + rb'.*?(' + 'Camera '.encode('utf-16-be') + rb'\x00\d)', blob, re.S)
    return found[1].decode('utf-16-be') if found else None


def is_multicam_sequence(sequence_xml):
    return any(track_angle(track) for track in TRACK.findall(sequence_xml))


def angles(entries):
    """{angle: {file, offset_frames}} for every angle with a clip inside the .drt's multicam."""
    found = {}
    for name, data in entries.items():
        if not name.startswith('SeqContainer/'):
            continue
        for track in TRACK.findall(data.decode()):
            angle, clips = track_angle(track), CLIP.findall(track)
            if angle and clips:
                if angle in found or len(clips) != 1:
                    raise ValueError(f'{angle}: expected one clip in one multicam')
                found[angle] = {'file': re.search(r'<MediaFilePath>(.*?)</MediaFilePath>', clips[0])[1],
                                'offset_frames': int(re.search(r'<Start>(\d+)</Start>', clips[0])[1])}
    return found


def outer_sequence(entries, timeline_name=None):
    """The .drt's own timeline sequence: the one the media pool entry of the exported timeline points at (the file
    also holds the sequence of every multicam and nested timeline it uses)."""
    folder = next(data.decode() for name, data in entries.items() if name.endswith('MpFolder.xml'))
    timeline_clips = re.findall(r'<Sm2MpTimelineClip .*?</Sm2MpTimelineClip>', folder, re.S)
    if len(timeline_clips) > 1:
        timeline_clips = [c for c in timeline_clips if re.search(r'<Name>(.*?)</Name>', c)[1] == timeline_name]
    [timeline_clip] = timeline_clips
    exported = re.search(r'<Sm2Sequence DbId="([0-9a-f-]+)"', timeline_clip)[1]
    [name] = [n for n, data in entries.items() if n.startswith('SeqContainer/') and f'<Sequence>{exported}</Sequence>' in data.decode()]
    return name


def video_clips(sequence_xml, track):
    """The clip elements on video track TRACK (1-based) of a timeline sequence."""
    tracks = TRACK.findall(re.search(r'<VideoTrackVec>.*?</VideoTrackVec>', sequence_xml, re.S)[0])
    return CLIP.findall(tracks[track - 1]) if track <= len(tracks) else []


def record_of(clip_xml, timeline_start):
    return int(re.search(r'<Start>(\d+)</Start>', clip_xml)[1]) - timeline_start


def item_angle(clip_xml):
    found = ANGLE_IN_ITEM.search(bytes.fromhex(re.search(r'<FieldsBlob>([0-9a-f]*)</FieldsBlob>', clip_xml)[1]))
    return found[1].decode() if found else None


def with_angle(clip_xml, angle):
    blob_hex = re.search(r'<FieldsBlob>([0-9a-f]*)</FieldsBlob>', clip_xml)[1]
    new, count = ANGLE_IN_ITEM.subn(b'\x1a\x08' + angle.encode(), bytes.fromhex(blob_hex))
    if count != 1 or len(angle) != 8:
        raise ValueError(f'Cannot set angle {angle!r}')
    return clip_xml.replace(blob_hex, new.hex(), 1)


def item_angles(entries, track, timeline_start, timeline_name=None):
    """{record frame: angle} of every multicam item on video TRACK of the .drt's timeline."""
    return {record_of(clip, timeline_start): item_angle(clip)
            for clip in video_clips(entries[outer_sequence(entries, timeline_name)].decode(), track)}


def read_angles(resolve, project, multicam_item):
    """The multicam's angles, read from the .drt of a one-frame scratch timeline that is deleted again."""
    pool = project.GetMediaPool()
    current = project.GetCurrentTimeline()
    scratch = pool.CreateEmptyTimeline(f'{multicam_item.GetName()} angles (scratch)')
    try:
        if not pool.AppendToTimeline([{'mediaPoolItem': multicam_item, 'startFrame': 0, 'endFrame': 1, 'mediaType': 1}]):
            raise RuntimeError('Could not place the multicam to read its angles')
        CACHE.mkdir(parents=True, exist_ok=True)
        return angles(exported_entries(resolve, scratch, CACHE / 'angles.drt'))
    finally:
        pool.DeleteTimelines([scratch])
        if current:
            project.SetCurrentTimeline(current)


def set_angles(resolve, project, timeline, track, angle_at_record, work_folder):
    """Give each multicam item on video TRACK the angle angle_at_record[its record frame] through a .drt round trip.
    The timeline is replaced by its import under the same name, once the import matches the original item by item
    (place, length, source start, framing, speed, grade node count), in its settings and track names, and every angle
    reads back from a fresh export. Returns the new timeline."""
    pool, name, start = project.GetMediaPool(), timeline.GetName(), timeline.GetStartFrame()
    work_folder.mkdir(parents=True, exist_ok=True)
    entries = exported_entries(resolve, timeline, work_folder / 'exported.drt')
    sequence_name = outer_sequence(entries)
    sequence = entries[sequence_name].decode()
    clips = video_clips(sequence, track)
    if sorted(record_of(clip, start) for clip in clips) != sorted(angle_at_record):
        raise RuntimeError(f'V{track} items do not sit where the segments do')
    for clip in clips:
        sequence = sequence.replace(clip, with_angle(clip, angle_at_record[record_of(clip, start)]), 1)
    entries[sequence_name] = sequence.encode()
    rewritten = work_folder / 'angles.drt'
    write_drt(entries, rewritten)
    def snapshot(t):
        items = add_captions.items_snapshot(t)
        return {'items': {k: [row[1:] for row in rows] for k, rows in items.items()},  # a multicam item's name carries its angle
                'captions': add_captions.captions_snapshot(t), 'settings': add_captions.settings_snapshot(t),
                'track names': add_captions.track_names(t)}
    before = snapshot(timeline)
    audio_states = {int(track.split()[1]): [row[7] for row in rows]
                    for track, rows in add_captions.items_snapshot(timeline).items() if track.startswith('audio')}
    ids = {project.GetTimelineByIndex(i).GetUniqueId() for i in range(1, project.GetTimelineCount() + 1)}
    if not timeline.SetName(f'{name} (before angles)'):
        raise RuntimeError('Rename failed before setting angles')
    try:
        imported = pool.ImportTimelineFromFile(str(rewritten), {'importSourceClips': False})
        if not imported or not imported.SetName(name):
            raise RuntimeError('Import of the angled timeline failed')
        add_captions.set_track_names(imported, before['track names'])
        add_captions.restore_audio_states(imported, audio_states)  # the import drops every audio fade (add_captions.py)
        after = snapshot(imported)
        faults = [f'{part} changed in the angle round trip' for part in before if before[part] != after[part]]
        got = item_angles(exported_entries(resolve, imported, work_folder / 'readback.drt'), track, start)
        if got != angle_at_record:
            faults.append(f'angles read back wrong at records {[r for r in angle_at_record if got.get(r) != angle_at_record[r]][:5]}')
        if project.GetTimelineCount() != len(ids) + 1:
            faults.append('the import added unexpected timelines')
        if faults:
            raise RuntimeError('; '.join(faults))
    except Exception:
        added = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetUniqueId() not in ids]
        if added:
            pool.DeleteTimelines(added)
        timeline.SetName(name)
        raise
    if not pool.DeleteTimelines([timeline]):
        raise RuntimeError('The angled timeline is in place but the original could not be deleted')
    project.SetCurrentTimeline(imported)
    return imported


def make_from_files(resolve, project, files, name):
    """The multicam NAME of the camera FILES (in the media pool already) in the open project, and its angles."""
    pool = project.GetMediaPool()
    folders, media = [pool.GetRootFolder()], {}
    while folders:
        folder = folders.pop()
        folders.extend(folder.GetSubFolderList() or [])
        media.update({item.GetClipProperty('File Path'): item for item in folder.GetClipList() or []})
    missing = [str(path) for path in files if str(path) not in media]
    if missing:
        raise ValueError(f'Not in the media pool: {missing}')
    made = make(resolve, pool, [media[str(path)] for path in files], name)
    return {'multicam': made.GetName(), 'angles': read_angles(resolve, project, made)}


if __name__ == '__main__':
    import argparse
    import json
    import sys
    parser = argparse.ArgumentParser(description='Make the cameras\' multicam in the open project and print its angles '
                                                 '(each angle\'s camera file and offset in multicam frames) for inventory.md.')
    parser.add_argument('name')
    parser.add_argument('camera_files', nargs='+', type=Path)
    args = parser.parse_args()
    import DaVinciResolveScript
    status = 0
    try:
        resolve = DaVinciResolveScript.scriptapp('Resolve')
        project = resolve.GetProjectManager().GetCurrentProject()
        result = make_from_files(resolve, project, [path.resolve() for path in args.camera_files], args.name)
        if not resolve.GetProjectManager().SaveProject():
            raise RuntimeError('SaveProject failed')
        print(json.dumps(result, indent=1))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

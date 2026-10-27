"""Build a new Resolve timeline from an edit list, in one command, and compare it with the list read back.

Written by AI on 2026-10-25 by GPT-6.1 Sol. Rewritten on 2026-10-26 by Claude Opus 5.5 (stream B of the hill-climb):
one command for the whole build, every field read back, a true exit code. Rewritten again on 2026-10-26 by Claude Opus
5.5 (stream I of the hill-climb) for the layout of layout-design.md: the cameras as one multicam on V2, titles as
title items on V4, the dialogue on one track with crossfades, named tracks.

place.py EDIT_LIST --timeline NAME [--look-track FILE]

In this order, in the open project, on a timeline NAME that must not exist yet (pipeline/edit-format.md has the rows):
1. V1 and V3, the `panels`: plain clips with their framing, colour group, grade and speed;
2. V2, the `segments`: the list's `multicam` cut into items, each at its camera's source frame plus that angle's offset
   inside the multicam, with its framing and speed (no grade: the cut timeline is for editing; finish.py grades the
   flattened duplicate); then each item's angle is set through the timeline's .drt (multicam.py);
3. V4, the `titles`: the look's Fusion templates as title items with their inputs (graphic.py);
4. A1 and A2, the `audio` rows and `sound` block, laid by sound.py: the dialogue with its crossfades, the room tone;
5. ST1, the `captions`: captions.py makes them whole frames into build/captions.json beside the list, and
   add_captions.py puts them on the subtitle track with the look's caption track (or --look-track FILE);
6. the tracks named (TRACK_NAMES), save, read the timeline back (readback.py) and compare it with the list.

The comparison covers every field the list gives except `why` and a grade: a panel's file, place, frames, source,
framing (unset keys are Resolve's defaults), group, speed and retime; a segment's camera file, place, frames, source
frame of that camera, framing, speed and retime (no colour group); a title's template and every input its row gives, pill ranges
included; every audio clip and crossfade as sound.py lays them; every caption and word; the track names. Numbers agree
within 1e-6. A panel's grade cannot be read back (readback.py says why): SetCDL must return True, and grades are
listed under reading_gaps. Exit 0 only when there is no difference.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

import captions as caption_frames
import graphic
import multicam
import readback
import sound

PIPELINE = Path(__file__).resolve().parents[1]
LOOKS = PIPELINE.parent / 'looks'
spec = importlib.util.spec_from_file_location('add_captions', PIPELINE / 'resolve/add_captions.py')
add_captions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(add_captions)

DEFAULT_FRAMING = {'ZoomX': 1.0, 'ZoomY': 1.0, 'Pan': 0.0, 'Tilt': 0.0,
                   'CropLeft': 0.0, 'CropRight': 0.0, 'CropTop': 0.0, 'CropBottom': 0.0}
RETIME_CONSTANTS = {'nearest': 'RETIME_NEAREST', 'optical': 'RETIME_OPTICAL_FLOW',
                    'frame blend': 'RETIME_FRAME_BLEND', 'project': 'RETIME_USE_PROJECT'}
BACKGROUND_TRACK, CAMERAS_TRACK, APP_TRACK, TITLES_TRACK = 1, 2, 3, 4
TRACK_NAMES = {('video', BACKGROUND_TRACK): 'Background', ('video', CAMERAS_TRACK): 'Cameras', ('video', APP_TRACK): 'App',
               ('video', TITLES_TRACK): 'Titles', ('audio', sound.DIALOGUE_TRACK): 'Dialogue',
               ('audio', sound.ROOM_TONE_TRACK): 'Room tone', ('subtitle', 1): 'Captions'}


def differences(expected, actual, path=''):
    if isinstance(expected, dict) and isinstance(actual, dict):
        return [difference for key in expected
                for difference in differences(expected[key], actual.get(key), f'{path}/{key}')]
    if isinstance(expected, list) and isinstance(actual, list):
        found = [difference for i, (left, right) in enumerate(zip(expected, actual))
                 for difference in differences(left, right, f'{path}/{i}')]
        if len(expected) != len(actual):
            found.append({'path': path, 'expected': f'{len(expected)} rows', 'actual': f'{len(actual)} rows'})
        return found
    numbers = all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (expected, actual))
    if numbers and abs(expected - actual) <= 1e-6:
        return []
    return [] if expected == actual else [{'path': path, 'expected': expected, 'actual': actual}]


def picture(row, frames):
    speed = row.get('speed_percent', 100)
    wanted = {'record': row['record'], 'frames': frames, 'source_in': row['source_in'], 'speed_percent': speed,
              'framing': {**DEFAULT_FRAMING, **row.get('framing', {})}}
    if speed != 100:
        wanted['retime'] = row['retime']
    return wanted


def expected_video(data, folder, finished=False):
    """What the video tracks must read back, track by track in record order. On a cut timeline a segment is a multicam
    item naming its camera's file, with no colour group; on its finish timeline (finish.py) it is a plain clip of that
    file in the camera's colour group."""
    panels = [{'track': row['track'], 'file': str((folder / row['file']).resolve()), 'group': row.get('group'),
               **picture(row, row['source_out'] - row['source_in'])} for row in data.get('panels', [])]
    cameras = data.get('cameras', {})
    segments = []
    for row in data.get('segments', []):
        camera, path = cameras[row['camera']], str((folder / cameras[row['camera']]['file']).resolve())
        where = {'file': path, 'group': camera['group']} if finished else {'camera_file': path, 'group': None}
        segments.append({'track': CAMERAS_TRACK, **where, **picture(row, row['frames'])})
    titles = [{'track': TITLES_TRACK, 'record': row['record'], 'frames': row['frames'],
               'template': graphic.fusion_tool_name(row['template']), 'inputs': row['inputs']} for row in data.get('titles', [])]
    return sorted(panels + segments + titles, key=lambda row: (row['track'], row['record']))


def expected_audio(data, folder):
    if not data.get('audio'):
        return {'clips': [], 'crossfades': []}
    lav, clips, crossfades = sound.planned_clips(data, folder)
    rows = []
    for clip in clips:
        row = {'track': clip['track'], 'file': str(lav), 'record_s': clip['tl_in'], 'source_in_s': clip['src_in'],
               'source_out_s': clip['src_in'] + clip['length'], 'fade_in_s': clip['fade_in'], 'fade_out_s': clip['fade_out']}
        if 'voice_isolation' in clip['piece']:
            row['voice_isolation'] = clip['piece']['voice_isolation']
        rows.append(row)
    track_of = lambda x: sound.DIALOGUE_TRACK if x['outgoing'].startswith('piece') else sound.ROOM_TONE_TRACK
    return {'clips': sorted(rows, key=lambda row: (row['track'], row['record_s'])),
            'crossfades': sorted(({'track': track_of(x), 'start_s': x['at'] - x['length'] / 2, 'length_s': x['length']}
                                  for x in crossfades), key=lambda x: (x['track'], x['start_s']))}


def expected_captions(caption_file):
    if caption_file is None:
        return []
    return [{'text': c['text'], 'start': c['start'], 'end': c['end'], 'words': c['words']}
            for c in json.loads(caption_file.read_text())['captions']]


def media_by_path(pool):
    folders, media = [pool.GetRootFolder()], {}
    while folders:
        media_folder = folders.pop()
        folders.extend(media_folder.GetSubFolderList() or [])
        media.update({item.GetClipProperty('File Path'): item for item in media_folder.GetClipList() or []})
    return media


def media_named(pool, name):
    folders, found = [pool.GetRootFolder()], []
    while folders:
        media_folder = folders.pop()
        folders.extend(media_folder.GetSubFolderList() or [])
        found += [item for item in media_folder.GetClipList() or [] if item.GetName() == name]
    if len(found) != 1:
        raise ValueError(f'{len(found)} media pool clips are named {name!r}; the list must name one multicam')
    return found[0]


def append(resolve, project, timeline, media, row, track, first_source_frame, frames, groups):
    """One video item at row['record'] on TRACK with the row's framing, group, grade and speed."""
    pool = project.GetMediaPool()
    while timeline.GetTrackCount('video') < track:
        timeline.AddTrack('video')
    clip = (pool.AppendToTimeline([{'mediaPoolItem': media, 'startFrame': first_source_frame,
                                    'endFrame': first_source_frame + frames, 'mediaType': 1, 'trackIndex': track,
                                    'recordFrame': timeline.GetStartFrame() + row['record']}]) or [None])[0]
    where = f"V{track} at {row['record']}"
    if clip is None or int(clip.GetDuration()) != frames or int(clip.GetStart() - timeline.GetStartFrame()) != row['record']:
        raise RuntimeError(f'Placement failed: {where}')
    apply_look(resolve, project, clip, row, frames, groups, where)
    return clip


def apply_look(resolve, project, clip, row, frames, groups, where):
    """A placed item's framing, colour group, CDL grade and speed, as its row gives them."""
    if row.get('framing') and not clip.SetProperties(row['framing']):
        raise RuntimeError(f'SetProperties failed: {where}')
    if row.get('group'):
        if row['group'] not in groups:
            groups[row['group']] = project.AddColorGroup(row['group'])
        if not groups[row['group']] or not clip.AssignToColorGroup(groups[row['group']]):
            raise RuntimeError(f"Colour group assignment failed: {row['group']}")
    if row.get('grade'):
        grade = row['grade']
        cdl = {'NodeIndex': '1', **{key.title(): ' '.join(map(str, grade[key])) for key in ('slope', 'offset', 'power')},
               'Saturation': str(grade['saturation'])}
        if not clip.SetCDL(cdl):
            raise RuntimeError(f'SetCDL failed: {where}')
    speed = row.get('speed_percent', 100)
    if speed != 100:
        retime = getattr(resolve, RETIME_CONSTANTS[row['retime']])
        if (not clip.SetSpeed({'Percentage': speed, 'RippleTimeline': False})
                or not clip.SetProperties({'RetimeProcess': retime}) or int(clip.GetDuration()) != frames):
            raise RuntimeError(f'SetSpeed failed or changed the length: {where}')


def place_picture(resolve, project, timeline, data, folder):
    """V1 and V3 panels and the V2 segments; returns the segments' {record: angle}."""
    pool = project.GetMediaPool()
    media = media_by_path(pool)
    groups = {group.GetName(): group for group in project.GetColorGroupsList() or []}
    for row in data.get('panels', []):
        path = str((folder / row['file']).resolve())
        if path not in media:
            media[path] = (pool.ImportMedia([path]) or [None])[0]
        if media[path] is None:
            raise RuntimeError(f'Could not import {path}')
        append(resolve, project, timeline, media[path], row, row['track'], row['source_in'], row['source_out'] - row['source_in'], groups)
    if not data.get('segments'):
        return {}
    cameras = media_named(pool, data['multicam'])
    angle_of_file = {details['file']: (angle, details['offset_frames'])
                     for angle, details in multicam.read_angles(resolve, project, cameras).items()}
    project.SetCurrentTimeline(timeline)
    angle_at_record = {}
    for row in data['segments']:
        path = str((folder / data['cameras'][row['camera']]['file']).resolve())
        if path not in angle_of_file:
            raise ValueError(f"Camera {row['camera']!r} ({path}) is not an angle of {data['multicam']!r}")
        angle, offset = angle_of_file[path]
        append(resolve, project, timeline, cameras, row, CAMERAS_TRACK, row['source_in'] + offset, row['frames'], groups)
        angle_at_record[row['record']] = angle
    return angle_at_record


def name_tracks(timeline):
    for (kind, index), name in TRACK_NAMES.items():
        if index <= timeline.GetTrackCount(kind) and timeline.GetTrackName(kind, index) != name and not timeline.SetTrackName(kind, index, name):
            raise RuntimeError(f'Could not name {kind} track {index} {name!r}')


def expected_tracks(data):
    return {f'{kind} {index}': name for (kind, index), name in TRACK_NAMES.items() if kind != 'subtitle' or data.get('captions')}


def run(resolve, filename, name, look_track=None):
    data = json.loads(filename.read_text())
    folder = filename.parent
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    if data.get('resolve_project', project.GetName()) != project.GetName():
        raise ValueError('Open project differs from the edit list')
    if project.IsRenderingInProgress():
        raise RuntimeError('Resolve is rendering; place after the render completes')
    if readback.timeline_named(project, name):
        raise ValueError(f'Timeline {name!r} already exists')
    settings = project.GetSettings()
    if float(data['fps']) != float(settings['timelineFrameRate']):
        raise ValueError('Project frame rate differs from the edit list')
    timeline = project.GetMediaPool().CreateEmptyTimeline(name)
    if timeline is None:
        raise RuntimeError('CreateEmptyTimeline failed')
    project.SetCurrentTimeline(timeline)
    inherited = ['colorScienceMode', 'isAutoColorManage', 'rcmPresetMode', 'colorSpaceTimeline',
                 'colorSpaceOutput', 'inputDRT', 'outputDRT', 'disableFusionToneMapping', 'timelineInputResMismatchBehavior']
    wanted = {'useCustomSettings': '1', **{key: settings[key] for key in inherited}, 'useInverseDRT': '1'}
    for prefix in ('timelineResolution', 'timelineOutputResolution'):
        wanted.update({prefix+'Width': str(data['format']['width']), prefix+'Height': str(data['format']['height'])})
    for key, value in wanted.items():
        if not timeline.SetSettings({key: str(value)}) or str(timeline.GetSetting(key)) != str(value):
            raise RuntimeError(f'Could not set {key}={value}')
    angle_at_record = place_picture(resolve, project, timeline, data, folder)
    while timeline.GetTrackCount('video') < TITLES_TRACK:
        timeline.AddTrack('video')
    while timeline.GetTrackCount('audio') < sound.ROOM_TONE_TRACK:
        timeline.AddTrack('audio', 'stereo')
    name_tracks(timeline)
    if angle_at_record:
        timeline = multicam.set_angles(resolve, project, timeline, CAMERAS_TRACK, angle_at_record,
                                       folder / 'build' / 'place' / name.replace('/', '_'))
    result = {'timeline': name, 'panels': len(data.get('panels', [])), 'segments': len(angle_at_record)}
    if data.get('titles'):
        result['titles'] = len(graphic.place_titles(resolve, project, timeline, TITLES_TRACK, data['titles'],
                                                    graphic.HERE / 'templates' / data['look'], folder))
    if data.get('audio'):
        report = sound.run(resolve, filename, name)
        result['sound'] = {'clips': len(report['clips']), 'crossfades': len(report['crossfades']),
                           'fade_mismatches': report['fade_mismatches'], 'report': report['folder']}
    if data.get('captions'):
        caption_file = folder / 'build' / 'captions.json'
        result['captions_py'] = caption_frames.build(filename, caption_file)
        look_track = Path(look_track) if look_track else LOOKS / data['look'] / 'resolve' / 'caption-track.drt'
        result['captions'] = add_captions.put_captions(resolve, name, json.loads(caption_file.read_text()), look_track,
                                                       folder / 'build' / 'caption-tracks')
    name_tracks(readback.timeline_named(project, name))
    if not manager.SaveProject():
        raise RuntimeError('SaveProject failed')
    result.update(compare(resolve, project, name, data, folder))
    return result


def compare(resolve, project, name, data, folder, finished=False):
    """Read timeline NAME back and list every difference from the list (finished: as finish.py makes it)."""
    got = readback.read(resolve, project, name)
    expected = {'resolve_project': project.GetName(), 'fps': float(data['fps']), 'format': data['format'],
                'tracks': expected_tracks(data), 'video': expected_video(data, folder, finished),
                'audio': expected_audio(data, folder),
                'captions': expected_captions(folder / 'build' / 'captions.json' if data.get('captions') else None)}
    if 'duration_frames' in data:
        expected['duration_frames'] = data['duration_frames']
    return {'differences': differences(expected, got), 'reading_gaps': got['reading_gaps']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('edit_list', type=Path)
    parser.add_argument('--timeline', required=True)
    parser.add_argument('--look-track', type=Path)
    args = parser.parse_args()
    import DaVinciResolveScript
    try:
        result = run(DaVinciResolveScript.scriptapp('Resolve'), args.edit_list.resolve(), args.timeline, args.look_track)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        status = int(bool(result['differences']))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

"""Build a video's first cut, once, from its plan: one timeline in its final layout, graded, blurred and ready to cache.

Written by AI on 2026-11-19 by Claude Opus 5.5, from place.py (GPT-6.1 Sol, 25 Oct; Claude Opus 5.5, 26 Oct and 17 Nov)
and finish.py (Claude Opus 5.5, 26 Oct), for Josh's layout: the main camera on the lower camera track, the second camera
on the track above only where the film shows it.

build.py PLAN.json --timeline NAME

1. assemble.py turns the plan into edit-list.json beside it (the words found, every sound edge placed in a measured
   pause, everything in timeline frames). The edit list is this build's input only: after the build the timeline is
   the only copy of the cut, and nothing keeps the list in step with it.
2. On a new timeline NAME in the plan's project (Resolve started windowless if need be):
   V1 the look's background (panels on track 1); V2 the main camera (the plan's `reference` camera) for the whole film,
   under the second camera's shots too, so a shot switched back to it needs only the upper clip removed; V3 the second
   camera, only where the film shows it; V4 the app panels (track 3); V5 the titles; A1 the dialogue and A2 the room
   tone (sound.py, every edge to the sample); the captions on the subtitle track.
3. One pass through the timeline's file (timeline_file.py) for what no call sets: each crossfade's sub-frame geometry
   and the captions with every word's time. It comes before the grade, the blur and the cache, because the import is a
   new timeline and would lose the render cache.
4. Every camera clip in its camera's colour group with its CDL; every clip of a camera with "blur": true given the
   look's background blur (copied from the carrier timeline "look background blur"), its CDL again, and the blur node
   flagged for Resolve's render cache; the project's render cache set to "user", so Resolve fills it in the background.
5. The timeline read back (readback.py) and compared with the edit list: every difference is listed.

Prints assemble's report (what needs a look: edges with no pause, joins the join check flags, doubtful word times),
the differences and the seconds per stage. Nothing here stops for an editorial reason; the report is for the model.
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import captions as caption_frames
import graphic
import readback
import session
import sound
import timeline_file

HERE = Path(__file__).resolve().parent
LOOKS = HERE.parents[1] / 'looks'
BACKGROUND, MAIN, SECOND, APP, TITLES = 1, 2, 3, 4, 5
TRACK_NAMES = {('video', BACKGROUND): 'Background', ('video', MAIN): 'Main camera', ('video', SECOND): 'Second camera',
               ('video', APP): 'App', ('video', TITLES): 'Titles', ('audio', sound.DIALOGUE_TRACK): 'Dialogue',
               ('audio', sound.ROOM_TONE_TRACK): 'Room tone', ('subtitle', 1): 'Captions'}
DEFAULT_FRAMING = {'ZoomX': 1.0, 'ZoomY': 1.0, 'Pan': 0.0, 'Tilt': 0.0, 'CropLeft': 0.0, 'CropRight': 0.0, 'CropTop': 0.0, 'CropBottom': 0.0}
RETIME_CONSTANTS = {'nearest': 'RETIME_NEAREST', 'optical': 'RETIME_OPTICAL_FLOW', 'frame blend': 'RETIME_FRAME_BLEND',
                    'project': 'RETIME_USE_PROJECT'}
BLUR_TIMELINE = 'look background blur'


def main_and_second(cameras):
    main = next(key for key, camera in cameras.items() if camera.get('reference'))
    others = [key for key in cameras if key != main]
    if len(others) > 1:
        raise ValueError('build.py lays two cameras at most: the reference camera and one other')
    return main, (others[0] if others else None)


def frame_on(cameras, from_camera, to_camera, frame, fps):
    """The frame of TO_CAMERA's file showing the moment FROM_CAMERA's file shows at FRAME (picture_offset_s: front-camera
    time = this camera's time + offset)."""
    return round(frame + (cameras[from_camera].get('picture_offset_s', 0) - cameras[to_camera].get('picture_offset_s', 0)) * fps)


def camera_rows(data):
    """(main rows, second rows): the main camera under every segment, consecutive rows that continue each other merged
    into one clip, and the second camera's segments as they are. A segment on the second camera gets the main camera's
    framing of the nearest main segment beneath it."""
    cameras, fps = data['cameras'], float(data['fps'])
    main, second = main_and_second(cameras)
    segments = sorted(data['segments'], key=lambda s: s['record'])
    main_framings = [(s['record'], s.get('framing') or cameras[main].get('framing', {})) for s in segments if s['camera'] == main]
    rows, upper = [], []
    for s in segments:
        if s['camera'] == main:
            row = dict(s)
        else:
            upper.append(s)
            framing = min(main_framings, key=lambda m: abs(m[0] - s['record']))[1] if main_framings else cameras[main].get('framing', {})
            row = {'camera': main, 'record': s['record'], 'frames': s['frames'], 'framing': framing,
                   'source_in': frame_on(cameras, s['camera'], main, s['source_in'], fps)}
        if s.get('off'):
            row['off'] = True
        last = rows[-1] if rows else None
        if (last and last.get('speed_percent', 100) == row.get('speed_percent', 100) == 100 and last['framing'] == row['framing']
                and last.get('off') == row.get('off')
                and last['record'] + last['frames'] == row['record'] and last['source_in'] + last['frames'] == row['source_in']):
            last['frames'] += row['frames']
        else:
            rows.append(row)
    return rows, upper


def place(resolve, project, timeline, media, row, track, file):
    """One video clip of FILE at row['record'] on TRACK, with the row's framing and speed."""
    frames = row['frames'] if 'frames' in row else row['source_out'] - row['source_in']
    item = (project.GetMediaPool().AppendToTimeline([{
        'mediaPoolItem': media[file], 'startFrame': row['source_in'], 'endFrame': row['source_in'] + frames, 'mediaType': 1,
        'trackIndex': track, 'recordFrame': timeline.GetStartFrame() + row['record']}]) or [None])[0]
    where = f"V{track} at {row['record']}"
    if item is not None and int(item.GetDuration()) > frames:  # a still is laid at its default length whatever endFrame says
        item.SetRightOffset(item.GetRightOffset() + int(item.GetDuration()) - frames)
    if item is None or int(item.GetDuration()) != frames or int(item.GetStart() - timeline.GetStartFrame()) != row['record']:
        raise RuntimeError(f'Placement failed: {where}')
    if row.get('framing') and not item.SetProperties(row['framing']):
        raise RuntimeError(f'SetProperties failed: {where}')
    speed = row.get('speed_percent', 100)
    if speed != 100 and (not item.SetSpeed({'Percentage': speed, 'RippleTimeline': False})
                         or not item.SetProperties({'RetimeProcess': getattr(resolve, RETIME_CONSTANTS[row['retime']])})
                         or int(item.GetDuration()) != frames):
        raise RuntimeError(f'SetSpeed failed or changed the length: {where}')
    return item


def grade(project, item, camera, groups):
    """The camera's colour group and its CDL on node 1."""
    if camera['group'] not in groups:
        groups[camera['group']] = project.AddColorGroup(camera['group'])
    if not item.AssignToColorGroup(groups[camera['group']]):
        raise RuntimeError(f"Colour group {camera['group']!r} could not be assigned")
    g = camera['grade']
    cdl = {'NodeIndex': '1', **{key.title(): ' '.join(map(str, g[key])) for key in ('slope', 'offset', 'power')}, 'Saturation': str(g['saturation'])}
    if not item.SetCDL(cdl):
        raise RuntimeError('SetCDL failed')


def blur_carrier(project, look):
    """The clip on the carrier timeline whose node 2 is the look's background blur, imported once per project."""
    carrier = session.timeline_named(project, BLUR_TIMELINE)
    if carrier is None:
        spec = json.loads((LOOKS / look / 'look.json').read_text(encoding='utf-8'))['colour']['backgroundBlur']
        carrier = project.GetMediaPool().ImportTimelineFromFile(str(LOOKS / look / spec['carrier']), {'importSourceClips': False})
        if carrier is None or not carrier.SetName(BLUR_TIMELINE):
            raise RuntimeError('Could not import the background blur carrier')
    source = (carrier.GetItemListInTrack('video', 1) or [None])[0]
    if source is None or 'OFX: CineFocus' not in source.GetNodeGraph().GetToolsInNode(2):
        raise RuntimeError(f'The carrier timeline {BLUR_TIMELINE!r} holds no CineFocus node 2')
    return source


def blur(resolve, project, timeline, clips, camera, look):
    """The look's background blur on CLIPS (AI CineFocus over an inverted AI Magic Mask, the one Josh approved on
    where-was-i; the mask is copied, not tracked, because the only scripted tracking shows a progress strip on his
    desktop), node 1 given the camera's CDL again, and the blur node flagged for the render cache."""
    source = blur_carrier(project, look)
    project.SetCurrentTimeline(timeline)
    if not source.CopyGrades(clips):
        raise RuntimeError('CopyGrades of the background blur failed')
    groups = {g.GetName(): g for g in project.GetColorGroupsList() or []}
    for clip in clips:
        graph = clip.GetNodeGraph()
        if graph.GetLUT(1):
            graph.SetLUT(1, '')
        grade(project, clip, camera, groups)
        if not graph.SetNodeCacheMode(2, resolve.CACHE_ENABLED):
            raise RuntimeError('Could not flag the blur node for the render cache')


def name_tracks(timeline):
    for (kind, index), name in TRACK_NAMES.items():
        if index <= timeline.GetTrackCount(kind) and timeline.GetTrackName(kind, index) != name:
            timeline.SetTrackName(kind, index, name)


def differences(expected, actual, path=''):
    if isinstance(expected, dict) and isinstance(actual, dict):
        return [d for key in expected for d in differences(expected[key], actual.get(key), f'{path}/{key}')]
    if isinstance(expected, list) and isinstance(actual, list):
        found = [d for i, (a, b) in enumerate(zip(expected, actual)) for d in differences(a, b, f'{path}/{i}')]
        return found + ([{'path': path, 'expected': f'{len(expected)} rows', 'actual': f'{len(actual)} rows'}] if len(expected) != len(actual) else [])
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (expected, actual)) and abs(expected - actual) <= 1e-3:
        return []
    return [] if expected == actual else [{'path': path, 'expected': expected, 'actual': actual}]


def compare(got, data, folder, video_rows, caption_file):
    """Every field the edit list gives, against the timeline read back."""
    def video(row, track, file):
        frames = row['frames'] if 'frames' in row else row['source_out'] - row['source_in']
        return {'track': track, 'record': row['record'], 'frames': frames, 'file': file, 'source_in': row['source_in'],
                'framing': {**DEFAULT_FRAMING, **row.get('framing', {})}}
    expected_video = sorted((video(row, track, file) for row, track, file in video_rows), key=lambda r: (r['track'], r['record']))
    expected_video += [{'track': TITLES, 'record': t['record'], 'frames': t['frames'], 'template': graphic.fusion_tool_name(t['template']),
                        'inputs': t['inputs']} for t in sorted(data.get('titles', []), key=lambda t: t['record'])]
    got_video = [{key: row.get(key) for key in expected} for row, expected in zip(got['video'], expected_video)]
    lav, clips, crossfades = sound.planned_clips(data, folder)
    expected_audio = sorted(({'track': c['track'], 'record_s': c['tl_in'], 'source_in_s': c['src_in'], 'source_out_s': c['src_in'] + c['length'],
                              'fade_in_s': c['fade_in'], 'fade_out_s': c['fade_out']} for c in clips), key=lambda r: (r['track'], r['record_s']))
    got_audio = [{key: row[key] for key in expected} for row, expected in zip(got['audio']['clips'], expected_audio)]
    expected_captions = [{k: c[k] for k in ('text', 'start', 'end', 'words')} for c in json.loads(caption_file.read_text(encoding='utf-8'))['captions']] if caption_file else []
    return (differences(len(expected_video), len(got['video']), '/video count') + differences(expected_video, got_video, '/video') + differences(expected_audio, got_audio, '/audio')
            + differences(len(crossfades), len(got['audio']['crossfades']), '/crossfades')
            + differences(expected_captions, got['captions'], '/captions'))


def build(plan_path, name):
    folder, began, seconds = plan_path.parent, time.monotonic(), {}
    edit_list = folder / 'edit-list.json'
    done = subprocess.run(['/usr/bin/python3', '-B', str(HERE / 'assemble.py'), str(plan_path), '--out', str(edit_list), '--force'],
                          capture_output=True, text=True, encoding='utf-8', cwd=HERE, env={**os.environ, 'PYTHONUTF8': '1'})
    report = json.loads(done.stdout or '{}')
    if 'error' in report or not edit_list.exists():
        raise RuntimeError(f"assemble.py: {report.get('error') or done.stderr[-800:]}")
    (folder / 'build').mkdir(exist_ok=True)
    (folder / 'build' / 'assemble.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    seconds['assemble'] = time.monotonic() - began
    data = json.loads(edit_list.read_text(encoding='utf-8'))
    resolve, project = session.connect(data['resolve_project'])
    if session.timeline_named(project, name):
        raise ValueError(f'Timeline {name!r} already exists')
    timeline = project.GetMediaPool().CreateEmptyTimeline(name)
    if timeline is None:
        raise RuntimeError('CreateEmptyTimeline failed')
    project.SetCurrentTimeline(timeline)
    try:
        result = lay(resolve, project, timeline, data, folder, name, seconds)
    except Exception:
        made = session.timeline_named(project, name)
        if made:
            project.GetMediaPool().DeleteTimelines([made])
        raise
    result['assemble'] = {key: report.get(key) for key in ('edges', 'joins', 'captions', 'doubtful_words', 'unchosen_words',
                                                           'caption_width', 'graphic_spans', 'edges_near_cuts', 'needs_the_model')}
    result['seconds'] = {key: round(value, 1) for key, value in seconds.items()}
    return result


def lay(resolve, project, timeline, data, folder, name, seconds):
    t = time.monotonic()
    settings = project.GetSettings()
    inherited = ['colorScienceMode', 'isAutoColorManage', 'rcmPresetMode', 'colorSpaceTimeline', 'colorSpaceOutput', 'inputDRT',
                 'outputDRT', 'disableFusionToneMapping', 'timelineInputResMismatchBehavior']
    wanted = {'useCustomSettings': '1', **{key: settings[key] for key in inherited if key in settings}, 'useInverseDRT': '1'}
    for prefix in ('timelineResolution', 'timelineOutputResolution'):
        wanted.update({prefix + 'Width': str(data['format']['width']), prefix + 'Height': str(data['format']['height'])})
    for key, value in wanted.items():
        if not timeline.SetSettings({key: str(value)}) or str(timeline.GetSettings().get(key)) != str(value):
            raise RuntimeError(f'Could not set {key}={value}')
    while timeline.GetTrackCount('video') < TITLES:
        timeline.AddTrack('video')
    while timeline.GetTrackCount('audio') < sound.ROOM_TONE_TRACK:
        timeline.AddTrack('audio', 'stereo')
    pool = project.GetMediaPool()
    media = readback_media(pool)
    cameras = data['cameras']
    main, second = main_and_second(cameras)
    path = lambda file: str((folder / file).resolve())
    main_rows, upper_rows = camera_rows(data)
    video_rows = ([(row, BACKGROUND if row['track'] == 1 else APP, path(row['file'])) for row in data.get('panels', [])]
                  + [(row, MAIN, path(cameras[main]['file'])) for row in main_rows]
                  + [(row, SECOND, path(cameras[second]['file'])) for row in upper_rows])
    placed = {}
    for row, track, file in video_rows:
        if file not in media:
            media[file] = import_media(pool, file)
        item = place(resolve, project, timeline, media, row, track, file)
        if row.get('off'):
            item.SetClipEnabled(False)
        if row.get('group'):  # a panel's colour group (the look's background); screen material takes none
            groups = {g.GetName(): g for g in project.GetColorGroupsList() or []}
            if row['group'] not in groups:
                groups[row['group']] = project.AddColorGroup(row['group'])
            item.AssignToColorGroup(groups[row['group']])
        placed.setdefault(track, []).append(item)
    seconds['picture'] = time.monotonic() - t
    t = time.monotonic()
    if data.get('titles'):
        graphic.place_titles(resolve, project, timeline, TITLES, data['titles'], HERE / 'templates' / data['look'], folder)
    seconds['titles'] = time.monotonic() - t
    t = time.monotonic()
    laid = sound.lay(resolve, project, timeline, data, folder)
    seconds['sound'] = time.monotonic() - t
    t = time.monotonic()
    caption_file = None
    spec = None
    if data.get('captions'):
        caption_file = folder / 'build' / 'captions.json'
        caption_frames.build(folder / 'edit-list.json', caption_file)
        spec = json.loads(caption_file.read_text(encoding='utf-8'))
    timeline, file_pass = timeline_file.rewrite(resolve, project, timeline, folder / 'build' / 'file-pass', crossfades=laid['crossfades'],
                                                captions=spec, look_track=LOOKS / data['look'] / 'resolve' / 'caption-track.drt')
    seconds['file_pass'] = time.monotonic() - t
    t = time.monotonic()
    groups = {g.GetName(): g for g in project.GetColorGroupsList() or []}
    for track, key in ((MAIN, main), (SECOND, second)):
        clips = timeline.GetItemListInTrack('video', track) or []
        if key and cameras[key].get('blur'):
            blur(resolve, project, timeline, clips, cameras[key], data['look'])
        else:
            for clip in clips:
                grade(project, clip, cameras[key], groups)
    name_tracks(timeline)
    project.SetSetting('perfRenderCacheMode', 'user')
    if project.GetSetting('perfRenderCacheMode') != 'user':
        raise RuntimeError("Could not set the project's render cache to user")
    session.save(resolve)
    seconds['grade'] = time.monotonic() - t
    t = time.monotonic()
    got = readback.read(resolve, project, name)
    found = compare(got, data, folder, video_rows, caption_file)
    seconds['readback'] = time.monotonic() - t
    resolve.OpenPage('edit')  # Resolve fills the render cache in the background while a page is open and it is idle
    return {'timeline': name, 'clips': {f'V{k}': len(v) for k, v in sorted(placed.items())}, 'sound': laid['clips'],
            'crossfades': len(laid['crossfades']), 'file_pass': file_pass, 'differences': found}


def import_media(pool, path):
    """The media pool item of the file at PATH, imported if it is not there yet. A picture whose name ends in a digit is
    imported from a copy named otherwise, because Resolve reads it as one frame of an image sequence."""
    found = readback_media(pool)
    if path in found:
        return found[path]
    source = Path(path)
    if source.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tif', '.tiff') and source.stem[-1:].isdigit():
        copy = session.CACHE / 'pipeline-b' / 'stills' / f'{source.stem} still{source.suffix}'
        copy.parent.mkdir(parents=True, exist_ok=True)
        if not copy.exists() or copy.stat().st_mtime < source.stat().st_mtime:
            copy.write_bytes(source.read_bytes())
        if str(copy) in found:
            return found[str(copy)]
        path = str(copy)
    item = (pool.ImportMedia([path]) or [None])[0]
    if item is None:
        item = readback_media(pool).get(path)  # ImportMedia can return None for a file it did import
    if item is None:
        raise RuntimeError(f'Could not import {path}')
    return item


def readback_media(pool):
    folders, media = [pool.GetRootFolder()], {}
    while folders:
        f = folders.pop()
        folders.extend(f.GetSubFolderList() or [])
        media.update({item.GetClipProperty('File Path'): item for item in f.GetClipList() or []})
    return media


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--timeline', required=True)
    args = parser.parse_args()
    session.main(lambda: build(args.plan.resolve(), args.timeline))

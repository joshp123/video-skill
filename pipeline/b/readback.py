"""Read a Resolve timeline back: every video item, every audio item, every caption, in the plan's terms.

Written by AI on 2026-10-25 by GPT-6.1 Sol. Rewritten on 2026-10-26 by Claude Opus 5.5 (stream B of the hill-climb);
the multicam removed and describe() added on 2026-11-19 (Claude Opus 5.5), when the timeline became the only copy of
the cut.

readback.py PLAN.json --timeline NAME [--describe]

- video: every item on every video track, in track and record order: a clip names its `file`, a title its `template`
  and inputs; `source_in` in source frames; framing, speed and retime, colour group, first node's CDL (`GetCDL`), the
  tools in each node.
- audio: `clips`, every clip on every audio track, sub-frame, in seconds on the timeline's clock, with its fades;
  `crossfades`, every audio transition's track, start, length and type.
- captions: from the timeline's own .drt export: text, start, end and each word's start and end, in seconds.
--describe prints the timeline in the edit list's shape instead (describe()), which report.py reads.
"""
import argparse
import json
import sys
from pathlib import Path

import graphic
import session
import timeline_file
import write_caption_track  # on sys.path through timeline_file

FRAMING = timeline_file.FRAMING_KEYS
RETIME_NAMES = {0: 'project', 1: 'nearest', 2: 'frame blend', 3: 'optical'}
CACHE = session.CACHE / 'pipeline-b/readback'
MAIN, SECOND, APP, TITLES = 2, 3, 4, 5  # the tracks build.py lays; V1 is the look's background


def read(resolve, project, name):
    timeline = session.timeline_named(project, name)
    if timeline is None:
        raise ValueError(f'No timeline named {name!r}')
    folder = CACHE / name.replace('/', '_')
    folder.mkdir(parents=True, exist_ok=True)
    drt = folder / 'timeline.drt'
    timeline_file.export(resolve, timeline, drt)
    fps, start = float(timeline.GetSetting('timelineFrameRate')), timeline.GetStartFrame()
    result = {'resolve_project': project.GetName(), 'fps': fps,
              'format': {'width': int(timeline.GetSetting('timelineResolutionWidth')),
                         'height': int(timeline.GetSetting('timelineResolutionHeight'))},
              'duration_frames': int(timeline.GetEndFrame() - start),
              'tracks': {f'{kind} {index}': timeline.GetTrackName(kind, index) for kind in ('video', 'audio', 'subtitle')
                         for index in range(1, timeline.GetTrackCount(kind) + 1)},
              'video': [], 'audio': {'clips': [], 'crossfades': []}, 'captions': []}
    for track in range(1, timeline.GetTrackCount('video') + 1):
        for item in timeline.GetItemListInTrack('video', track) or []:
            record, frames = int(item.GetStart() - start), int(item.GetDuration())
            media = item.GetMediaPoolItem()
            if media is None and item.GetFusionCompCount():
                result['video'].append({'track': track, 'record': record, 'frames': frames, **graphic.read_title(item)})
                continue
            speed = float((item.GetSpeed() or {}).get('Percentage', 100))
            source_in = round(item.GetLeftOffset() * speed / 100)
            row = {'track': track, 'record': record, 'frames': frames, 'file': media.GetClipProperty('File Path') if media else '',
                   'source_in': source_in, 'source_out': source_in + frames, 'speed_percent': speed,
                   'framing': {key: item.GetProperty(key) for key in FRAMING}, 'enabled': item.GetClipEnabled()}
            if speed != 100:
                row['retime'] = RETIME_NAMES.get(item.GetProperty('RetimeProcess'), item.GetProperty('RetimeProcess'))
            group = item.GetColorGroup()
            row['group'] = group.GetName() if group else None
            graph = item.GetNodeGraph()
            row['node_tools'] = [graph.GetToolsInNode(i) for i in range(1, graph.GetNumNodes() + 1)] if graph else []
            cdl = item.GetCDL(1)  # readable since 21.2 (smoke tests, 17 Nov)
            if cdl:
                row['grade'] = {key.lower(): [float(v) for v in cdl[key].split()] for key in ('Slope', 'Offset', 'Power')}
                row['grade']['saturation'] = float(cdl['Saturation'])
            result['video'].append(row)
    for track in range(1, timeline.GetTrackCount('audio') + 1):
        for item in timeline.GetItemListInTrack('audio', track) or []:
            if item.GetType() == 'transition':
                result['audio']['crossfades'].append({'track': track, 'start_s': (item.GetStart(True) - start) / fps,
                                                      'length_s': (item.GetEnd(True) - item.GetStart(True)) / fps, 'type': item.GetName()})
                continue
            media, fades = item.GetMediaPoolItem(), item.GetFades()
            source_in_s = item.GetLeftOffset(True) / fps
            row = {'track': track, 'file': media.GetClipProperty('File Path') if media else '',
                   'record_s': (item.GetStart(True) - start) / fps, 'source_in_s': source_in_s,
                   'source_out_s': source_in_s + (item.GetEnd(True) - item.GetStart(True)) / fps,
                   'fade_in_s': fades['FadeIn'] / fps, 'fade_out_s': fades['FadeOut'] / fps}
            isolation = item.GetVoiceIsolationState() or {}
            if isolation.get('isEnabled'):
                row['voice_isolation'] = isolation.get('amount')
            result['audio']['clips'].append(row)
    for caption in write_caption_track.read_captions(drt):
        result['captions'].append({
            'text': caption['text'], 'start': (caption['start'] - start) / fps, 'end': (caption['end'] - start) / fps,
            'words': [{'text': word.strip(), 'start': (a / 2 - start) / fps, 'end': (b / 2 - start) / fps}
                      for word, a, b in zip(caption['words'], caption['word_starts'], caption['word_ends'])]})
    return result


def describe(resolve, project, name, plan_path):
    """Timeline NAME in the edit list's shape, with the plan's fixed facts (cameras, sound, look): what report.py reads.
    A camera segment is whatever shows: the second camera's clip where V3 has one, else the main camera."""
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    folder = Path(plan_path).resolve().parent
    got = read(resolve, project, name)
    camera_of = {str((folder / c['file']).resolve()): key for key, c in plan['cameras'].items()}
    shown = []  # (record, frames, row) of every camera frame range that is seen
    upper = sorted((r for r in got['video'] if r['track'] == SECOND and r.get('enabled', True)), key=lambda r: r['record'])
    for row in sorted((r for r in got['video'] if r['track'] == MAIN), key=lambda r: r['record']):
        cursor, end = row['record'], row['record'] + row['frames']
        for over in upper:
            a, b = max(cursor, over['record']), min(end, over['record'] + over['frames'])
            if b <= a:
                continue
            if a > cursor:
                shown.append((cursor, a - cursor, row))
            cursor = b
        if cursor < end:
            shown.append((cursor, end - cursor, row))
    shown += [(r['record'], r['frames'], r) for r in upper]
    segments = []
    for record, frames, row in sorted(shown, key=lambda s: s[0]):
        segments.append({'camera': camera_of[row['file']], 'record': record, 'frames': frames,
                         'source_in': row['source_in'] + record - row['record'], 'framing': row['framing']})
    panels = [{'file': r['file'], 'track': 1 if r['track'] == 1 else 3, 'record': r['record'], 'source_in': r['source_in'],
               'source_out': r['source_out'], 'framing': r['framing']} for r in got['video']
              if r['track'] in (1, APP) and 'file' in r]
    titles = [{'template': r['template'], 'inputs': r['inputs'], 'record': r['record'], 'frames': r['frames']}
              for r in got['video'] if 'template' in r]
    audio = [{'file': c['file'], 'record_s': c['record_s'], 'source_in_s': c['source_in_s'], 'source_out_s': c['source_out_s']}
             for c in got['audio']['clips'] if c['track'] == 1]
    cameras = {key: dict(c, file=str((folder / c['file']).resolve())) for key, c in plan['cameras'].items()}
    sound = dict(plan['sound'], lav=str((folder / plan['sound']['lav']).resolve()))
    return {'resolve_project': got['resolve_project'], 'fps': got['fps'], 'format': got['format'], 'look': plan['look'],
            'duration_frames': got['duration_frames'], 'cameras': cameras, 'sound': sound, 'segments': segments,
            'panels': panels, 'titles': titles, 'audio': audio, 'captions': got['captions']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--timeline', required=True)
    parser.add_argument('--describe', action='store_true')
    args = parser.parse_args()
    project_name = json.loads(args.plan.read_text(encoding='utf-8'))['resolve_project']

    def run():
        resolve, project = session.connect(project_name)
        if args.describe:
            return describe(resolve, project, args.timeline, args.plan)
        return read(resolve, project, args.timeline)
    session.main(run)

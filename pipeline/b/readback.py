"""Read a Resolve timeline back in the edit list's terms: every video item, every audio item, every caption.

Written by AI on 2026-10-25 by GPT-6.1 Sol. Rewritten on 2026-10-26 by Claude Opus 5.5 (stream B of the hill-climb) so
that what place.py writes reads back: speed and retime, audio fades and sub-frame edges, and each
caption word's frames.

readback.py NAME [--folder DIR]

- video: every item on every video track, in track and record order. A clip names its `file`; a nested timeline (a
  template graphic) names its `timeline`. `source_in` is in source frames; a retimed clip (`speed_percent` not 100)
  keeps the list's meaning, `source_out` = `source_in` + its frames on the timeline.
- grade: not readable. No API call reads a CDL, and Resolve's EDL export with CDL carries one video track, a different
  one from call to call on the same timeline (V1, V2 or V3, 26 Oct), so it cannot be trusted. Named in `reading_gaps`.
- audio: `clips`, every clip on every audio track, in seconds on the timeline's clock (sub-frame), with its fades in
  seconds; `crossfades`, every audio transition, its track, start and length in seconds and its type.
- captions: from the timeline's own .drt export: text, start, end and each word's start and end, in seconds.
The .drt export goes to DIR (default .cache/pipeline-b/readback/<timeline>/).
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'subtitles'))
import write_caption_track
import graphic
import multicam

FRAMING = ('ZoomX', 'ZoomY', 'Pan', 'Tilt', 'CropLeft', 'CropRight', 'CropTop', 'CropBottom')
RETIME_NAMES = {0: 'project', 1: 'nearest', 2: 'frame blend', 3: 'optical'}
CACHE = Path(__file__).resolve().parents[2] / '.cache/pipeline-b/readback'


def timeline_named(project, name):
    return next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetName() == name), None)


def read(resolve, project, name, folder=None):
    timeline = timeline_named(project, name)
    if timeline is None:
        raise ValueError(f'No timeline named {name!r}')
    folder = Path(folder or CACHE / name.replace('/', '_'))
    folder.mkdir(parents=True, exist_ok=True)
    drt, fresh = folder / 'timeline.drt', folder / 'writing-timeline.drt'
    if not timeline.Export(str(fresh), resolve.EXPORT_DRT, resolve.EXPORT_NONE) or not fresh.exists():
        raise RuntimeError('DRT export failed')
    os.replace(fresh, drt)
    entries = multicam.drt_entries(drt)
    angles = multicam.angles(entries)
    fps = float(timeline.GetSetting('timelineFrameRate'))
    start = timeline.GetStartFrame()
    result = {'resolve_project': project.GetName(), 'fps': fps,
              'format': {'width': int(timeline.GetSetting('timelineResolutionWidth')),
                         'height': int(timeline.GetSetting('timelineResolutionHeight'))},
              'duration_frames': int(timeline.GetEndFrame() - start),
              'tracks': {f'{kind} {index}': timeline.GetTrackName(kind, index) for kind in ('video', 'audio', 'subtitle')
                         for index in range(1, timeline.GetTrackCount(kind) + 1)},
              'video': [], 'audio': {'clips': [], 'crossfades': []}, 'captions': [],
              'reading_gaps': ['CDL grades are not readable (no API call; the EDL export is unreliable); node tools are read instead.']}
    for track in range(1, timeline.GetTrackCount('video') + 1):
        item_angles = multicam.item_angles(entries, track, start, name)
        for item in timeline.GetItemListInTrack('video', track) or []:
            record, frames = int(item.GetStart() - start), int(item.GetDuration())
            media = item.GetMediaPoolItem()
            if media is None and item.GetFusionCompCount():
                result['video'].append({'track': track, 'record': record, 'frames': frames, **graphic.read_title(item)})
                continue
            speed = float((item.GetSpeed() or {}).get('Percentage', 100))
            source_in = round(item.GetLeftOffset() * speed / 100)
            row = {'track': track, 'record': record, 'frames': frames}
            if media and media.GetClipProperty('Type') == 'Multicam':
                angle = angles[item_angles[record]]
                row.update(angle=item_angles[record], camera_file=angle['file'])
                source_in -= angle['offset_frames']
            else:
                row['file'] = media.GetClipProperty('File Path') if media else ''
            row.update(source_in=source_in, source_out=source_in + frames, speed_percent=speed,
                       framing={key: item.GetProperty(key) for key in FRAMING})
            if speed != 100:
                row['retime'] = RETIME_NAMES.get(item.GetProperty('RetimeProcess'), item.GetProperty('RetimeProcess'))
            group = item.GetColorGroup()
            row['group'] = group.GetName() if group else None
            graph = item.GetNodeGraph()
            row['node_tools'] = [graph.GetToolsInNode(i) for i in range(1, graph.GetNumNodes() + 1)] if graph else []
            result['video'].append(row)
    for track in range(1, timeline.GetTrackCount('audio') + 1):
        for item in timeline.GetItemListInTrack('audio', track) or []:
            if item.GetType() == 'transition':
                result['audio']['crossfades'].append({'track': track, 'start_s': (item.GetStart(True) - start) / fps,
                                                      'length_s': (item.GetEnd(True) - item.GetStart(True)) / fps, 'type': item.GetName()})
                continue
            media = item.GetMediaPoolItem()
            fades = item.GetFades()
            record_s = (item.GetStart(True) - start) / fps
            source_in_s = item.GetLeftOffset(True) / fps
            row = {'track': track, 'file': media.GetClipProperty('File Path') if media else '',
                   'record_s': record_s, 'source_in_s': source_in_s,
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('name')
    parser.add_argument('--folder', type=Path)
    args = parser.parse_args()
    import DaVinciResolveScript
    status = 0
    try:
        resolve = DaVinciResolveScript.scriptapp('Resolve')
        print(json.dumps(read(resolve, resolve.GetProjectManager().GetCurrentProject(), args.name, args.folder), indent=1))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

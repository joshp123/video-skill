"""Make a cut timeline's finish timeline: the duplicate that is graded, rendered and delivered.

Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream I), for the two stages of layout-design.md.

finish.py EDIT_LIST --timeline CUT_NAME

The cut timeline is for editing: the cameras are one multicam on V2, ungraded. Its finish timeline, "CUT_NAME finish",
is remade from it by this script before every render. An older one of that name is kept, renamed "CUT_NAME finish
<date time>", since the colourist's Color page work after lock lives on it; copy its grades across with
pipeline/resolve/copy_grades.py when that work is to carry over, and tidy.py keeps it with its cut.
1. the cut timeline duplicated (DuplicateTimeline keeps every track, title, crossfade and caption);
2. every multicam item on V2 flattened to a plain clip of its active angle (FlattenMulticam, copy grade);
3. each of those clips, by its record frame, given the colour group and CDL grade of the camera it shows (the list's
   `cameras`, by file: the timeline's angle decides, so an angle switched in the viewer gets its own camera's grade), and its segment's framing and retime process again (flattening resets framing to Resolve's
   defaults, E-report, and the retime process to the project's, 26 Oct; it keeps the speed);
4. the tracks named, saved, read back (readback.py) and compared with the list as place.py compares the cut timeline,
   with each segment as a plain clip of its camera's file in that camera's group. A grade cannot be read back: SetCDL
   must return True.
Exit 0 only when there is no difference.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys

import place
import readback


def finish_name(cut_name):
    return f'{cut_name} finish'


def run(resolve, filename, cut_name):
    data = json.loads(filename.read_text())
    folder = filename.parent
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    if data.get('resolve_project', project.GetName()) != project.GetName():
        raise ValueError('Open project differs from the edit list')
    cut = readback.timeline_named(project, cut_name)
    if cut is None:
        raise ValueError(f'No timeline {cut_name!r}')
    pool, name = project.GetMediaPool(), finish_name(cut_name)
    older = readback.timeline_named(project, name)
    kept_as = None
    if older:
        kept_as = f"{name} {datetime.datetime.now():%Y-%m-%d %H.%M.%S}"
        if not older.SetName(kept_as):
            raise RuntimeError(f'Could not rename the older {name!r} to keep it')
    finished = cut.DuplicateTimeline(name)
    if finished is None:
        raise RuntimeError('DuplicateTimeline failed')
    project.SetCurrentTimeline(finished)
    start = finished.GetStartFrame()
    segments = {row['record']: row for row in data.get('segments', [])}
    for item in finished.GetItemListInTrack('video', place.CAMERAS_TRACK) or []:
        record = int(item.GetStart() - start)
        if record not in segments:
            raise RuntimeError(f'V{place.CAMERAS_TRACK} holds an item at {record} that no segment lists')
        if not item.FlattenMulticam(resolve.FLATTEN_MULTICAM_COPY_GRADE):
            raise RuntimeError(f'FlattenMulticam failed at {record}')
    groups = {group.GetName(): group for group in project.GetColorGroupsList() or []}
    flattened = {int(item.GetStart() - start): item for item in finished.GetItemListInTrack('video', place.CAMERAS_TRACK) or []}
    if sorted(flattened) != sorted(segments):
        raise RuntimeError('Flattening moved or lost an item on the cameras track')
    camera_of_file = {str((folder / camera['file']).resolve()): camera for camera in data['cameras'].values()}
    for record, row in segments.items():
        path = flattened[record].GetMediaPoolItem().GetClipProperty('File Path')
        if path not in camera_of_file:
            raise RuntimeError(f'The segment at {record} shows {path}, which is none of the list\'s cameras')
        camera = camera_of_file[path]  # the angle on the timeline, which a switch in the viewer may have changed
        look = {'framing': row.get('framing'), 'group': camera['group'], 'grade': camera['grade'],
                **{key: row[key] for key in ('speed_percent', 'retime') if key in row}}
        place.apply_look(resolve, project, flattened[record], look, row['frames'], groups, f'segment at {record}')
    place.name_tracks(finished)
    if not manager.SaveProject():
        raise RuntimeError('SaveProject failed')
    return {'timeline': name, 'older_kept_as': kept_as, 'segments_flattened': len(segments),
            **place.compare(resolve, project, name, data, folder, finished=True)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('edit_list', type=Path)
    parser.add_argument('--timeline', required=True)
    args = parser.parse_args()
    import DaVinciResolveScript
    try:
        result = run(DaVinciResolveScript.scriptapp('Resolve'), args.edit_list.resolve(), args.timeline)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        status = int(bool(result['differences']))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

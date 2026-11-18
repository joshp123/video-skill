"""Make a cut timeline's finish timeline: the duplicate that is graded, rendered and delivered.

Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream I), for the two stages of layout-design.md.

finish.py EDIT_LIST --timeline CUT_NAME

The cut timeline is for editing: the cameras are one multicam on V2, ungraded. Its finish timeline, "CUT_NAME finish",
is remade from it by this script before every render. An older one of that name is kept, renamed "CUT_NAME finish
<date time>", since the colourist's Color page work after lock lives on it; copy its grades across with
TimelineItem.CopyGrades when that work is to carry over (the copy_grades.py script that did it was removed on 17 Nov;
git has it), and tidy.py keeps it with its cut.
1. the cut timeline duplicated (DuplicateTimeline keeps every track, title, crossfade and caption);
2. every multicam item on V2 flattened to a plain clip of its active angle (FlattenMulticam, copy grade);
3. each of those clips, by its record frame, given the colour group and CDL grade of the camera it shows (the list's
   `cameras`, by file: the timeline's angle decides, so an angle switched in the viewer gets its own camera's grade), and its segment's framing and retime process again (flattening resets framing to Resolve's
   defaults, E-report, and the retime process to the project's, 26 Oct; it keeps the speed);
4. the tracks named, saved, read back (readback.py) and compared with the list as place.py compares the cut timeline,
   with each segment as a plain clip of its camera's file in that camera's group. A grade cannot be read back: SetCDL
   must return True;
5. every clip of a camera with `"blur": true` in the list given the look's background blur (look.json
   `colour.backgroundBlur`): the node stack of the one clip in the look's carrier timeline file, Resolve's AI CineFocus
   over an inverted AI Magic Mask (the blur Josh approved on where-was-i, 19 Oct), copied on (CopyGrades), node 1 given
   the camera's grade again. The copied mask is not tracked on the clip: TimelineItem.CreateMagicMask, the only
   scripted tracking, shows a progress strip on the desktop Josh is using (18 Nov), and without tracking the far rim of
   his glasses, where it crosses the bookcase, breaks up on some frames. A render with the blur takes about 0.38 s a
   blurred frame against 0.02 (render.py --blur off skips it for checks).
Exit 0 only when there is no difference.
"""
import argparse
import datetime
import json
from pathlib import Path
import time

import place
import readback
import session

BLUR_TIMELINE = 'look background blur'  # the carrier, imported once per project, kept by tidy.py as an old timeline

def finish_name(cut_name):
    return f'{cut_name} finish'


def run(filename, cut_name):
    data = json.loads(filename.read_text())
    folder = filename.parent
    began = time.monotonic()
    resolve, project = session.connect(data['resolve_project'])
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
    try:
        return grade(resolve, project, data, folder, finished, name, kept_as, began)
    except Exception:
        project.GetMediaPool().DeleteTimelines([finished])
        if older:
            older.SetName(name)
        raise


def grade(resolve, project, data, folder, finished, name, kept_as, began):
    """Flatten, group, grade and frame the duplicate; run() deletes it on any failure."""
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
    session.save(resolve)
    compared = place.compare(resolve, project, name, data, folder, finished=True)
    blurred = background_blur(project, data, folder, flattened, camera_of_file, finished)
    if blurred:
        session.save(resolve)
    return {'timeline': name, 'older_kept_as': kept_as, 'segments_flattened': len(segments), **compared,
            'background_blur': blurred, 'seconds': round(time.monotonic() - began, 1)}


def background_blur(project, data, folder, flattened, camera_of_file, finished):
    """The look's background blur on every clip of a camera marked "blur": the carrier clip's node stack copied on,
    node 1 given the camera's grade again. Returns {camera: clips blurred}."""
    marked = {key for key, camera in data['cameras'].items() if camera.get('blur')}
    if not marked:
        return {}
    look = json.loads((place.LOOKS / data['look'] / 'look.json').read_text(encoding='utf-8'))
    carrier_file = place.LOOKS / data['look'] / look['colour']['backgroundBlur']['carrier']
    carrier = readback.timeline_named(project, BLUR_TIMELINE)
    if carrier is None:
        carrier = project.GetMediaPool().ImportTimelineFromFile(str(carrier_file), {'importSourceClips': False})
        if carrier is None or not carrier.SetName(BLUR_TIMELINE):
            raise RuntimeError(f'Could not import the background blur carrier {carrier_file}')
    source = (carrier.GetItemListInTrack('video', 1) or [None])[0]
    if source is None or 'OFX: CineFocus' not in source.GetNodeGraph().GetToolsInNode(2):
        raise RuntimeError(f'The carrier timeline {BLUR_TIMELINE!r} holds no CineFocus node 2')
    project.SetCurrentTimeline(finished)
    done = {}
    for key in sorted(marked):
        camera = data['cameras'][key]
        clips = [item for item in flattened.values() if camera_of_file.get(item.GetMediaPoolItem().GetClipProperty('File Path')) is camera]
        if not clips:
            continue
        if not source.CopyGrades(clips):
            raise RuntimeError(f'CopyGrades of the background blur onto the {key} clips failed')
        grade = camera['grade']
        cdl = {'NodeIndex': '1', **{part.title(): ' '.join(map(str, grade[part])) for part in ('slope', 'offset', 'power')},
               'Saturation': str(grade['saturation'])}
        for clip in clips:
            graph = clip.GetNodeGraph()
            if graph.GetLUT(1):
                graph.SetLUT(1, '')
            if not clip.SetCDL(cdl):
                raise RuntimeError(f'SetCDL failed after the blur on a {key} clip at {clip.GetStart() - finished.GetStartFrame()}')
        done[key] = len(clips)
    return done


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('edit_list', type=Path)
    parser.add_argument('--timeline', required=True)
    args = parser.parse_args()
    session.main(lambda: run(args.edit_list.resolve(), args.timeline))

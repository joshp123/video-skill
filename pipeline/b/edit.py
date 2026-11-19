"""Change a cut in place on its one timeline, the way an editor would: the few edits Resolve's API makes awkward, each in
one call, every track kept in step. Nothing is rebuilt and nothing outside the timeline is written.

Written by AI on 2026-11-19 by Claude Opus 5.5, from the direct-call proofs of 18 Nov (rebuild-tooling.md, "Josh's
layout") and the Mac mini tests of 19 Nov.

From a shell, in pipeline/b:      /usr/bin/python3 -B edit.py PLAN.json --timeline NAME COMMAND ...
From the Resolve MCP (run_script_unsafe; `resolve` and `project` are given):
    import sys; sys.path.insert(0, "/Users/josh/code/video-skill/pipeline/b"); import edit
    result = edit.cut(resolve, project, "NAME", at=1234, frames=10)

Frames are the timeline's, from 0. PLAN.json gives only the fixed facts (cameras, look, sound); the timeline holds
the cut. Every command returns `changes`: every item on every track that was added, removed or changed, read before and
after, and `notes`: anything the model must look at or decide.

  cut AT FRAMES            take FRAMES out of the film from AT, on every track: camera clips and sound are cut in two
                           (the second part starts FRAMES later in its source), graphics and captions that run across
                           are shortened, everything after moves up. A crossfade the trims remove is put back.
  insert AT FRAMES         open FRAMES of empty film at AT on every track: camera clips and sound running across are
                           cut in two and the second part moved on, graphics running across are lengthened, room tone
                           fills the new gap. The gap shows the background until something is put in it.
  split AT [--tracks ...]  cut the clips under AT in two, no time changes (default: the camera tracks).
  camera START END CAMERA [--framing JSON]
                           show CAMERA from START to END (END excluded): the second camera is a clip on V3 over the main
                           camera on V2, graded, blurred and framed like its neighbours; the main camera shows where V3
                           is empty.
  title AT JSON            set inputs of the title under frame AT, e.g. '{"Title": "[[New]] words"}'.
  still FILE START FRAMES  a picture over everything from START for FRAMES.
  captions JSON            retype or re-time captions, [{"index": i, "text"?: ..., "words"?: [{text, start, end}]}]
                           (seconds on the timeline), through the timeline's file. Costs the render cache: see notes.
  tidy                     delete every other timeline but the blur carrier, and media nothing uses.
"""
import argparse
import json
import time
from pathlib import Path

import captions as caption_frames
import graphic
import readback
import session
import sound
import timeline_file

LOOKS = Path(__file__).resolve().parents[2] / 'looks'
BACKGROUND, MAIN, SECOND, APP, TITLES = 1, 2, 3, 4, 5
CAMERA_TRACKS = (MAIN, SECOND)
CROSSFADE_FRAMES = 2  # the shortest crossfade AddTransition centres on an edit (one frame sits before the edit; 19 Nov)
BLUR_TIMELINE = 'look background blur'


# --- reading the timeline ---------------------------------------------------------------------------------------------

def timeline_of(project, name):
    timeline = session.timeline_named(project, name)
    if timeline is None:
        raise ValueError(f'No timeline {name!r}')
    project.SetCurrentTimeline(timeline)
    return timeline


def clips(timeline, kind, track):
    return [i for i in timeline.GetItemListInTrack(kind, track) or [] if i.GetType() != 'transition']


def tracks(timeline):
    return [(kind, index) for kind in ('video', 'audio', 'subtitle') for index in range(1, timeline.GetTrackCount(kind) + 1)]


def where(timeline, item):
    start = timeline.GetStartFrame()
    return round(item.GetStart(True) - start, 4), round(item.GetEnd(True) - start, 4)


def snapshot(timeline):
    """Every item on every track: (kind, track, name, start, end, source start), transitions included."""
    rows = []
    for kind, index in tracks(timeline):
        for item in timeline.GetItemListInTrack(kind, index) or []:
            a, b = where(timeline, item)
            transition = item.GetType() == 'transition'
            rows.append((kind, index, item.GetName(), a, b, None if transition or kind == 'subtitle' else round(item.GetLeftOffset(True), 4)))
    return rows


def changes(before, after):
    gone = [r for r in before if r not in after]
    new = [r for r in after if r not in before]
    label = lambda r: f'{r[0][0].upper()}{r[1]} {r[2]!r} {r[3]}-{r[4]}' + ('' if r[5] is None else f' from source {r[5]}')
    return {'unchanged': len(before) - len(gone), 'removed': [label(r) for r in gone], 'added': [label(r) for r in new]}


def done(timeline, before, began, **extra):
    return {'timeline': timeline.GetName(), **extra, 'changes': changes(before, snapshot(timeline)),
            'seconds': round(time.monotonic() - began, 3)}


# --- primitives ---------------------------------------------------------------------------------------------------------

def trim_tail(item, frames):
    """Take FRAMES off the item's end (negative: add them)."""
    if not item.SetRightOffset(item.GetRightOffset(True) + frames, True):
        raise RuntimeError(f'Could not trim the end of {item.GetName()!r}')


def trim_head(timeline, item, frames):
    """Take FRAMES off the item's start, its start moving later with it."""
    start = item.GetStart(True)
    if not item.SetLeftOffset(item.GetLeftOffset(True) + frames, True):
        raise RuntimeError(f'Could not trim the start of {item.GetName()!r}')
    if abs(item.GetStart(True) - (start + frames)) > 1e-3 and not item.SetPosition({'startFrame': start + frames}, True, True):
        raise RuntimeError(f'Could not move {item.GetName()!r} after trimming its start')


def move(timeline, kind, track, items, frames):
    """Move ITEMS (on one track, transitions left out) by FRAMES; MoveItems takes one track at a time."""
    if items and not timeline.MoveItems(items, {'startFrame': min(i.GetStart(True) for i in items) + frames}, False, True):
        raise RuntimeError(f'MoveItems refused {len(items)} items on {kind} {track}')


def copy_of(project, timeline, item, kind, track, record, source, length):
    """A new clip of ITEM's media: SOURCE (frames of its file) for LENGTH frames at RECORD (frames from the timeline's
    first), with ITEM's framing, grade, blur, colour group and render-cache flags, or its fades and voice isolation."""
    pool, start = project.GetMediaPool(), timeline.GetStartFrame()
    if kind == 'audio':
        fps = float(timeline.GetSetting('timelineFrameRate'))
        new = sound.place_piece(pool, timeline, item.GetMediaPoolItem(), {'what': item.GetName(), 'track': track, 'tl_in': record / fps,
                                                                        'src_in': source / fps, 'length': length / fps}, fps)
        isolation = item.GetVoiceIsolationState() or {}
        if isolation.get('isEnabled'):
            new.SetVoiceIsolationState({'isEnabled': True, 'amount': isolation.get('amount')})
        return new
    new = (pool.AppendToTimeline([{'mediaPoolItem': item.GetMediaPoolItem(), 'startFrame': round(source), 'endFrame': round(source + length),
                                   'mediaType': 1, 'trackIndex': track, 'recordFrame': start + round(record)}]) or [None])[0]
    if new is None or int(new.GetDuration()) != round(length):
        raise RuntimeError(f'Could not place a copy of {item.GetName()!r} on V{track} at {record}')
    if not item.CopyAttributes([new], {'allVideoAttributes': True}):
        raise RuntimeError(f'CopyAttributes failed onto the copy of {item.GetName()!r}')
    group = item.GetColorGroup()
    if group:
        new.AssignToColorGroup(group)
    if not item.CopyGrades([new]):
        raise RuntimeError(f'CopyGrades failed onto the copy of {item.GetName()!r}')
    graph, copied = item.GetNodeGraph(), new.GetNodeGraph()
    for node in range(1, (graph.GetNumNodes() if graph else 0) + 1):
        mode = graph.GetNodeCacheMode(node)
        if mode > 0 and copied.GetNodeCacheMode(node) != mode:
            copied.SetNodeCacheMode(node, mode)
    return new


def joins_of(timeline):
    """{(track, edit frame): length} of every audio crossfade, by its centre."""
    start = timeline.GetStartFrame()
    return {(t, round((i.GetStart(True) + i.GetEnd(True)) / 2 - start, 3)): round(i.GetEnd(True) - i.GetStart(True), 3)
            for t in range(1, timeline.GetTrackCount('audio') + 1)
            for i in timeline.GetItemListInTrack('audio', t) or [] if i.GetType() == 'transition'}


def put_back_crossfades(timeline, wanted):
    """A crossfade at every (track, edit frame) of WANTED that has none: Resolve's API makes them two frames long, centred
    (a sub-frame length needs the timeline's file). Returns the notes."""
    notes, have, start = [], joins_of(timeline), timeline.GetStartFrame()
    for (track, at), length in sorted(wanted.items()):
        if any(t == track and abs(a - at) < 1e-2 for t, a in have):
            continue
        outgoing = [i for i in clips(timeline, 'audio', track) if abs(i.GetEnd(True) - start - at) < 1e-2]
        if len(outgoing) != 1 or not outgoing[0].AddTransition({'type': sound.CROSSFADE, 'category': 'audio', 'position': 'end',
                                                                'alignment': 'center', 'duration': CROSSFADE_FRAMES}):
            raise RuntimeError(f'Could not put the crossfade back at A{track} frame {at}')
        if abs(length - CROSSFADE_FRAMES) > 1e-3:
            notes.append(f'A{track} join at frame {at}: crossfade put back {CROSSFADE_FRAMES} frames long, where it was {length}; '
                         'the join check in the report scores it')
    return notes


# --- the commands -------------------------------------------------------------------------------------------------------

def cut(resolve, project, name, at, frames, plan_path):
    """Take FRAMES out of the film from frame AT, on every track."""
    return change_time(resolve, project, name, at, -frames, plan_path)


def insert(resolve, project, name, at, frames, plan_path):
    """Open FRAMES of empty film at frame AT on every track, with room tone under it."""
    return change_time(resolve, project, name, at, frames, plan_path)


def change_time(resolve, project, name, at, delta, plan_path):
    """Take -DELTA frames out from AT (DELTA < 0), or open DELTA frames at AT (DELTA > 0), on every track at once.
    Camera clips and sound running across are cut in two, the second part starting later in its source for a cut, or
    moved on for an insert. Titles running across are laid again at their new length (Resolve's API cannot lengthen
    one, nor shorten one past its first five seconds). Pictures on V1 and V4 running across are trimmed or lengthened.
    Captions are moved; if one runs across AT, the caption track is written again through the timeline's file, which
    costs the render cache. A crossfade the trims removed is put back."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    before, notes, copies, titles = snapshot(timeline), [], [], []
    end = at - delta if delta < 0 else at  # frames AT..END go
    new_time = lambda t: t if t <= at else (max(at, t + delta) if delta < 0 else t + delta)
    joins = {(t, round(new_time(a), 3)): l for (t, a), l in joins_of(timeline).items() if not (delta < 0 and at <= a < end)}
    caption_items = timeline.GetItemListInTrack('subtitle', 1) or []
    across = [c for c in caption_items if where(timeline, c)[0] < at < where(timeline, c)[1]]
    rewrite_captions = readback.read(resolve, project, name)['captions'] if across else None
    for kind, track in tracks(timeline):
        if kind == 'subtitle' and rewrite_captions is not None:
            continue
        later = []
        for item in (clips(timeline, kind, track) if kind != 'subtitle' else timeline.GetItemListInTrack(kind, track) or []):
            a, b = where(timeline, item)
            splits = (kind == 'audio' or (kind == 'video' and track in CAMERA_TRACKS)) and item.GetMediaPoolItem()
            if b <= at or (delta > 0 and b <= at):
                continue
            if a >= end:
                later.append(item)
            elif a < at and (b > end if delta < 0 else True):
                if splits:
                    if kind == 'audio' and delta < 0:
                        joins[(track, float(at))] = CROSSFADE_FRAMES  # the two parts of the sound meet at AT
                    gone = 0 if delta > 0 else -delta
                    fades = item.GetFades() if kind == 'audio' else None
                    copies.append((item, kind, track, item.GetLeftOffset(True) + at - a + gone, b - at - gone, fades))
                    trim_tail(item, b - at)
                elif kind == 'video' and track == TITLES:
                    titles.append((item, a, b - a + delta))
                elif not item.SetRightOffset(item.GetRightOffset() - delta):
                    notes.append(f'{kind} {track} {item.GetName()!r} at {a} could not be made {abs(delta)} frames '
                                 f'{"longer" if delta > 0 else "shorter"}: look')
            elif a < at:
                trim_tail(item, b - at)
            elif b <= end:
                timeline.DeleteClips([item], False)
            else:
                trim_head(timeline, item, end - a)
                later.append(item)
        move(timeline, kind, track, later, delta)
    for item, kind, track, source, length, fades in copies:
        new = copy_of(project, timeline, item, kind, track, at + max(delta, 0), source, length)
        if fades:
            item.SetFades({'FadeIn': fades['FadeIn'], 'FadeOut': 0})
            new.SetFades({'FadeIn': 0, 'FadeOut': fades['FadeOut']})
    for item, start, length in titles:
        relay_title(resolve, project, timeline, item, start, length, plan['look'])
    if delta > 0:
        notes += room_tone(project, timeline, plan_path, at, delta)
    notes += put_back_crossfades(timeline, joins)
    if rewrite_captions is not None:
        for c in rewrite_captions:
            fps = float(timeline.GetSetting('timelineFrameRate'))
            shift = lambda s: new_time(s * fps) / fps
            c.update(start=shift(c['start']), end=shift(c['end']), words=[dict(w, start=shift(w['start']), end=shift(w['end'])) for w in c['words']])
        timeline = write_captions(resolve, project, timeline, rewrite_captions, plan['look'])
        notes.append(f'caption {across[0].GetName()!r} ran across frame {at}, so the caption track was written again through '
                     "the timeline's file: the timeline is its import and has no render cache until Resolve fills it again")
    session.save(resolve)
    return done(timeline, before, began, notes=notes)


def relay_title(resolve, project, timeline, item, start, frames, look):
    """Lay title ITEM again at START for FRAMES, with the same template and inputs."""
    read = graphic.read_title(item)
    templates = Path(__file__).resolve().parent / 'templates' / look
    template = next(p.stem for p in templates.glob('*.setting') if graphic.fusion_tool_name(p.stem) == read['template'])
    timeline.DeleteClips([item], False)
    graphic.place_titles(resolve, project, timeline, TITLES, [{'template': template, 'inputs': read['inputs'], 'record': start, 'frames': frames}],
                         templates, Path.cwd(), empty_track=False)


def room_tone(project, timeline, plan_path, at, frames):
    """Room tone on A2 under the new gap, from the plan's room-tone window, with its usual fades."""
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    folder, s = Path(plan_path).resolve().parent, plan['sound']
    fps = float(timeline.GetSetting('timelineFrameRate'))
    window = s['room_tone_s'][1] - s['room_tone_s'][0]
    if frames / fps > window:
        return [f'the gap is longer than the room-tone window ({window} s): fill it yourself']
    lav = str((folder / s['lav']).resolve())
    media = next(m for m in readback_media(project) if m.GetClipProperty('File Path') == lav)
    new = sound.place_piece(project.GetMediaPool(), timeline, media, {'what': 'room tone', 'track': sound.ROOM_TONE_TRACK,
                                                                       'tl_in': at / fps, 'src_in': s['room_tone_s'][0], 'length': frames / fps}, fps)
    new.SetFades({'FadeIn': 0.25, 'FadeOut': 0.25})
    return []


def readback_media(project):
    folders, found = [project.GetMediaPool().GetRootFolder()], []
    while folders:
        f = folders.pop()
        folders.extend(f.GetSubFolderList() or [])
        found += f.GetClipList() or []
    return found


def split(resolve, project, name, at, track_list=CAMERA_TRACKS):
    """Cut the clips under frame AT in two on the video TRACK_LIST, with no change in time."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    before = snapshot(timeline)
    for track in track_list:
        for item in clips(timeline, 'video', track):
            a, b = where(timeline, item)
            if a < at < b:
                source_after = item.GetLeftOffset(True) + at - a
                trim_tail(item, b - at)
                copy_of(project, timeline, item, 'video', track, at, source_after, b - at)
    session.save(resolve)
    return done(timeline, before, began)


def camera(resolve, project, name, start, end, to, plan_path, framing=None):
    """Show camera TO from frame START to END: the second camera as a V3 clip over V2, the main camera by clearing V3."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    before = snapshot(timeline)
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    cameras, folder = plan['cameras'], Path(plan_path).resolve().parent
    main = next(k for k, c in cameras.items() if c.get('reference'))
    if to not in cameras:
        raise ValueError(f'No camera {to!r} in the plan: {sorted(cameras)}')
    fps = float(timeline.GetSetting('timelineFrameRate'))
    neighbours = clips(timeline, 'video', SECOND)
    for item in neighbours:  # clear V3 from START to END
        a, b = where(timeline, item)
        if b <= start or a >= end:
            continue
        if a < start and b > end:
            source_after = item.GetLeftOffset() + end - a
            trim_tail(item, b - start)
            copy_of(project, timeline, item, 'video', SECOND, end, source_after, b - end)
        elif a < start:
            trim_tail(item, b - start)
        elif b > end:
            trim_head(timeline, item, end - a)
        else:
            timeline.DeleteClips([item], False)
    notes = []
    if to == main:
        if framing:
            split(resolve, project, name, start, (MAIN,))
            split(resolve, project, name, end, (MAIN,))
            for item in clips(timeline, 'video', MAIN):
                if where(timeline, item)[0] == start:
                    item.SetProperties(framing)
    else:
        under = [i for i in clips(timeline, 'video', MAIN) if where(timeline, i)[0] <= start < where(timeline, i)[1]]
        if not under:
            raise RuntimeError(f'No main camera clip under frame {start} to take the moment from')
        main_frame = under[0].GetLeftOffset() + start - where(timeline, under[0])[0]
        source = round(main_frame + (cameras[main].get('picture_offset_s', 0) - cameras[to].get('picture_offset_s', 0)) * fps)
        others = clips(timeline, 'video', SECOND)
        file = str((folder / cameras[to]['file']).resolve())
        media = next(m for m in readback_media(project) if m.GetClipProperty('File Path') == file)
        new = (project.GetMediaPool().AppendToTimeline([{'mediaPoolItem': media, 'startFrame': source, 'endFrame': source + end - start,
                                                         'mediaType': 1, 'trackIndex': SECOND, 'recordFrame': timeline.GetStartFrame() + start}]) or [None])[0]
        if new is None or int(new.GetDuration()) != end - start:
            raise RuntimeError(f'Could not place {to} on V{SECOND} at {start}')
        model = min(others, key=lambda i: abs(where(timeline, i)[0] - start), default=None)
        if model is not None:
            if not model.CopyAttributes([new], {'allVideoAttributes': True}) or not model.CopyGrades([new]):
                raise RuntimeError('Could not copy the neighbouring shot\'s framing and grade')
            new.AssignToColorGroup(model.GetColorGroup())
            graph = new.GetNodeGraph()
            for node in range(1, graph.GetNumNodes() + 1):
                if model.GetNodeGraph().GetNodeCacheMode(node) > 0:
                    graph.SetNodeCacheMode(node, resolve.CACHE_ENABLED)
            notes.append(f'framing and grade copied from the {to} shot at frame {where(timeline, model)[0]}')
        else:
            import build
            camera_spec = cameras[to]
            new.SetProperties(camera_spec.get('framing') or {})
            if camera_spec.get('blur'):
                build.blur(resolve, project, timeline, [new], camera_spec, plan['look'])
            else:
                build.grade(project, new, camera_spec, {g.GetName(): g for g in project.GetColorGroupsList() or []})
            notes.append(f'no other {to} shot on the timeline: framing, grade and blur from the plan')
        if framing and not new.SetProperties(framing):
            raise RuntimeError('Could not set the framing')
    session.save(resolve)
    return done(timeline, before, began, notes=notes)


def title(resolve, project, name, at, inputs):
    """Set INPUTS on the title (V5) under frame AT."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    before = snapshot(timeline)
    found = [i for i in clips(timeline, 'video', TITLES) if where(timeline, i)[0] <= at < where(timeline, i)[1]]
    if len(found) != 1:
        raise ValueError(f'{len(found)} titles under frame {at}')
    comp = found[0].GetFusionCompByIndex(1)
    macro = graphic.macro_of(comp)
    for key, value in inputs.items():
        tool = comp.FindTool(key)
        if tool and tool.GetAttrs()['TOOLS_RegID'] == 'StyledTextCLS':
            graphic.set_styled_text(tool, value)
        elif not macro.SetInput(key, graphic.input_value(value, Path.cwd(), graphic.STAGING / 'photos')):
            raise RuntimeError(f'Could not set the title\'s {key!r}')
    session.save(resolve)
    return done(timeline, before, began, inputs=graphic.read_title(found[0])['inputs'])


def still(resolve, project, name, file, start, frames):
    """FILE (a picture) over everything from frame START for FRAMES, on a new top track."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    before = snapshot(timeline)
    pool = project.GetMediaPool()
    path = str(Path(file).resolve())
    media = next((m for m in readback_media(project) if m.GetClipProperty('File Path') == path), None) or (pool.ImportMedia([path]) or [None])[0]
    if media is None:
        raise RuntimeError(f'Could not import {path}')
    timeline.AddTrack('video')
    track = timeline.GetTrackCount('video')
    new = (pool.AppendToTimeline([{'mediaPoolItem': media, 'startFrame': 0, 'endFrame': frames, 'mediaType': 1, 'trackIndex': track,
                                   'recordFrame': timeline.GetStartFrame() + start}]) or [None])[0]
    if new is None:
        raise RuntimeError('Could not place the still')
    if int(new.GetDuration()) != frames:  # AppendToTimeline lays a still at its default length whatever endFrame says
        trim_tail(new, int(new.GetDuration()) - frames)
    timeline.SetTrackName('video', track, 'Still')
    session.save(resolve)
    return done(timeline, before, began, track=track)


def captions(resolve, project, name, edits, plan_path):
    """Retype or re-time captions by index, through the timeline's file: the whole caption track is written again."""
    began = time.monotonic()
    timeline = timeline_of(project, name)
    before = snapshot(timeline)
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    folder = Path(plan_path).resolve().parent
    current = readback.read(resolve, project, name)['captions']
    for edit in edits:
        caption = current[edit['index']]
        if 'words' in edit:
            caption['words'] = edit['words']
        if 'text' in edit:
            new_words = edit['text'].split()
            if 'words' not in edit and len(new_words) != len(caption['words']):
                raise ValueError(f"caption {edit['index']}: {len(new_words)} words for {len(caption['words'])} timed ones: give 'words'")
            caption['text'] = edit['text']
            caption['words'] = [dict(w, text=t) for w, t in zip(caption['words'], new_words)]
    timeline = write_captions(resolve, project, timeline, current, plan['look'])
    session.save(resolve)
    resolve.OpenPage('edit')
    return done(timeline, before, began, notes=['the timeline was replaced by its import, which has no render cache: Resolve '
                                                'fills it again in the background (about the time of one live render)'])


def write_captions(resolve, project, timeline, captions, look):
    """The whole caption track written again through the timeline's file, from CAPTIONS (seconds on the timeline)."""
    fps = float(timeline.GetSetting('timelineFrameRate'))
    spec = {'fps': fps, 'captions': []}
    for c in captions:
        start, end, frames, _ = caption_frames.frames_for_template(c, fps)
        spec['captions'].append({'text': c['text'], 'rows': c['text'].split('\n'), 'start': start / fps, 'end': end / fps,
                                 'words': [{'text': w['text'], 'start': a / fps, 'end': b / fps} for w, (a, b) in zip(c['words'], frames)]})
    work = session.CACHE / 'pipeline-b' / 'captions' / timeline.GetName().replace('/', '_')
    timeline, _ = timeline_file.rewrite(resolve, project, timeline, work, captions=spec, look_track=LOOKS / look / 'resolve' / 'caption-track.drt')
    resolve.OpenPage('edit')
    return timeline


def tidy(resolve, project, keep):
    """Delete every timeline but KEEP and the blur carrier, and every media pool item no remaining timeline uses (the
    cameras and the lav stay in their Source bin)."""
    began = time.monotonic()
    pool = project.GetMediaPool()
    timelines = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]
    gone = [t for t in timelines if t.GetName() not in (keep, BLUR_TIMELINE)]
    if gone and not pool.DeleteTimelines(gone):
        raise RuntimeError('DeleteTimelines failed')
    kept = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]
    used = {item.GetMediaPoolItem().GetUniqueId() for t in kept for kind, index in tracks(t)
            for item in t.GetItemListInTrack(kind, index) or [] if item.GetMediaPoolItem()}
    used |= {t.GetMediaPoolItem().GetUniqueId() for t in kept}
    unused = []
    folders = [pool.GetRootFolder()]
    while folders:
        f = folders.pop()
        folders.extend(f.GetSubFolderList() or [])
        if f.GetName() != 'Source':
            unused += [m for m in f.GetClipList() or [] if m.GetUniqueId() not in used]
    if unused and not pool.DeleteClips(unused):
        raise RuntimeError('DeleteClips failed')
    for job in project.GetRenderJobList() or []:
        project.DeleteRenderJob(job['JobId'])
    session.save(resolve)
    return {'timelines_deleted': sorted(t.GetName() for t in gone), 'media_deleted': len(unused),
            'timelines': [t.GetName() for t in kept], 'seconds': round(time.monotonic() - began, 2)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--timeline', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    for command, fields in (('cut', ('at', 'frames')), ('insert', ('at', 'frames')), ('split', ('at',))):
        p = sub.add_parser(command)
        for field in fields:
            p.add_argument(field, type=int)
    sub.choices['split'].add_argument('--tracks', type=int, nargs='+', default=list(CAMERA_TRACKS))
    p = sub.add_parser('camera')
    p.add_argument('start', type=int); p.add_argument('end', type=int); p.add_argument('to'); p.add_argument('--framing', type=json.loads)
    p = sub.add_parser('title')
    p.add_argument('at', type=int); p.add_argument('inputs', type=json.loads)
    p = sub.add_parser('still')
    p.add_argument('file', type=Path); p.add_argument('start', type=int); p.add_argument('frames', type=int)
    p = sub.add_parser('captions')
    p.add_argument('edits', type=json.loads)
    sub.add_parser('tidy')
    args = parser.parse_args()
    project_name = json.loads(args.plan.read_text(encoding='utf-8'))['resolve_project']

    def run():
        resolve, project = session.connect(project_name)
        c, t = args.command, args.timeline
        if c == 'cut':
            return cut(resolve, project, t, args.at, args.frames, args.plan)
        if c == 'insert':
            return insert(resolve, project, t, args.at, args.frames, args.plan)
        if c == 'split':
            return split(resolve, project, t, args.at, args.tracks)
        if c == 'camera':
            return camera(resolve, project, t, args.start, args.end, args.to, args.plan, args.framing)
        if c == 'title':
            return title(resolve, project, t, args.at, args.inputs)
        if c == 'still':
            return still(resolve, project, t, args.file, args.start, args.frames)
        if c == 'captions':
            return captions(resolve, project, t, args.edits, args.plan)
        return tidy(resolve, project, t)
    session.main(run)

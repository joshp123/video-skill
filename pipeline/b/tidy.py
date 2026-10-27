"""Tidy a Resolve project so a human who opens it sees the current cut, its sources and its graphics, nothing else.

Written by AI on 2026-10-26 by Claude Opus 5.5 (stream F of the hill-climb). Finish timelines go with their cut, and
the Graphics bin is made only when something goes in it, since 2026-10-26 (Claude Opus 5.5, stream I). A --readme that
does not exist yet (a video's first cut) names nothing, since 2026-10-27 (Claude Opus 5.5, hill-climb stream L).

tidy.py PROJECT|--current [--readme versions/README.md] [--keep NAME ...] [--protect-prefix PREFIX ...]
        [--delete-pattern GLOB ...] [--graphic-pattern GLOB ...] [--dry-run]

It decides nothing; the rule is its arguments and the README:
- Current: the highest M of every "cut N build M", every timeline the README names as `timeline "NAME"` (what was
  sent to Josh), and every --keep NAME; with each of them its finish timelines ("NAME finish", and older ones finish.py
  kept as "NAME finish <date time>"), which hold the grade.
- Protected: any timeline or media item whose name starts with a --protect-prefix is never deleted or moved (another
  agent may be working on it); its timelines count as current when deciding what media is used.
- Deleted: every other "cut N build M" (superseded) and its finish timelines, every timeline matching a --delete-pattern (checks and tests by
  default), every graphic timeline (one nested in another timeline, or matching a --graphic-pattern, "graphic *"
  by default) that no kept timeline uses, and every media
  item that no kept timeline uses, except clips in the Source bin.
- Old: every other timeline (another role's drafts), kept for the record.
Bins after: Source (clips already there, plus non-timeline media the current cuts use directly, the cameras' multicam
included), Timelines (the current cuts and their finish timelines), Graphics (only for an older cut that nests graphic
timelines: those and the media inside them), Old (old timelines and the media only they use). Empty bins are deleted. Prints a JSON plan with --dry-run, the plan and the project
read back after without it, and saves the project. Run it through scratch/bin/resolve-py.
"""
import argparse
from fnmatch import fnmatch
import json
import os
from pathlib import Path
import re
import sys

DEFAULT_DELETE_PATTERNS = ('* check *', '* test *', 'hc-*')
DEFAULT_GRAPHIC_PATTERNS = ('graphic *', '* graphic *')
LAYOUT_BINS = ('Source', 'Graphics', 'Timelines', 'Old')
BUILD_NAME = re.compile(r'^cut (\d+) build (\d+)$')
FINISH_NAME = re.compile(r'^(.*) finish( \d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})?$')
README_TIMELINE = re.compile(r'timeline "([^"]+)"')


def all_timelines(project):
    return [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]


def bins_with_clips(folder):
    yield folder, folder.GetClipList() or []
    for sub in folder.GetSubFolderList() or []:
        yield from bins_with_clips(sub)


def media_used_by(timeline):
    return {item.GetMediaPoolItem().GetUniqueId()
            for kind in ('video', 'audio', 'subtitle')
            for track in range(1, timeline.GetTrackCount(kind) + 1)
            for item in timeline.GetItemListInTrack(kind, track) or []
            if item.GetMediaPoolItem()}


def closure_of_used_timelines(roots, timeline_by_media_id, used_media_by_timeline):
    reached, waiting = set(), list(roots)
    while waiting:
        name = waiting.pop()
        if name in reached:
            continue
        reached.add(name)
        waiting += [timeline_by_media_id[media_id] for media_id in used_media_by_timeline[name]
                    if media_id in timeline_by_media_id]
    return reached


def plan(project, keep_names, protect_prefixes, delete_patterns, graphic_patterns):
    timelines = {timeline.GetName(): timeline for timeline in all_timelines(project)}
    timeline_by_media_id = {timeline.GetMediaPoolItem().GetUniqueId(): name for name, timeline in timelines.items()}
    used_media_by_timeline = {name: media_used_by(timeline) for name, timeline in timelines.items()}
    nested_names = {timeline_by_media_id[media_id] for used in used_media_by_timeline.values()
                    for media_id in used if media_id in timeline_by_media_id}
    protected = lambda name: name.startswith(tuple(protect_prefixes))

    highest_build = {}
    for name in timelines:
        match = BUILD_NAME.match(name)
        if match:
            cut, build = int(match[1]), int(match[2])
            highest_build[cut] = max(highest_build.get(cut, build), build)
    missing = [name for name in keep_names if name not in timelines]
    if missing:
        raise ValueError(f'Kept timelines not in the project: {missing}')
    current_cuts = {f'cut {cut} build {build}' for cut, build in highest_build.items()} | set(keep_names)
    finish_of = {name: FINISH_NAME.match(name)[1] for name in timelines
                 if FINISH_NAME.match(name) and FINISH_NAME.match(name)[1] in timelines}
    current_cuts |= {name for name, cut in finish_of.items() if cut in current_cuts}

    deleted_by_rule, old_candidates = set(), set()
    for name in timelines:
        if name in current_cuts or protected(name) or name in nested_names:
            continue
        if any(fnmatch(name, pattern) for pattern in graphic_patterns):
            continue
        if BUILD_NAME.match(name) or name in finish_of or any(fnmatch(name, pattern) for pattern in delete_patterns):
            deleted_by_rule.add(name)
        else:
            old_candidates.add(name)
    protected_timelines = {name for name in timelines if protected(name)}
    current = closure_of_used_timelines(current_cuts | protected_timelines, timeline_by_media_id, used_media_by_timeline)
    retained = closure_of_used_timelines(current | old_candidates, timeline_by_media_id, used_media_by_timeline)
    old = retained - current
    deleted_timelines = sorted(set(timelines) - retained)
    assert not deleted_by_rule - set(deleted_timelines), 'a timeline matched a delete rule but is nested in a kept one'

    media_used_directly_by_current_cuts = set().union(*(used_media_by_timeline[name] for name in current_cuts))
    media_used_by_current = set().union(*(used_media_by_timeline[name] for name in current))
    media_used_by_retained = set().union(*(used_media_by_timeline[name] for name in retained))

    moves = {bin_name: [] for bin_name in LAYOUT_BINS}
    deleted_media, protected_media = [], []
    for folder, clips in bins_with_clips(project.GetMediaPool().GetRootFolder()):
        for clip in clips:
            media_id, clip_name = clip.GetUniqueId(), clip.GetName()
            if clip_name.startswith(tuple(protect_prefixes)) or (media_id in timeline_by_media_id
                                                                  and protected(timeline_by_media_id[media_id])):
                protected_media.append({'name': clip_name, 'bin': folder.GetName()})
                continue
            if media_id in timeline_by_media_id:
                name = timeline_by_media_id[media_id]
                target = ('Timelines' if name in current_cuts else 'Graphics' if name in current
                          else 'Old' if name in old else None)
            elif folder.GetName() == 'Source' or media_id in media_used_directly_by_current_cuts:
                target = 'Source'
            elif media_id in media_used_by_current:
                target = 'Graphics'
            elif media_id in media_used_by_retained:
                target = 'Old'
            else:
                deleted_media.append({'name': clip_name, 'bin': folder.GetName(), 'clip': clip})
                continue
            if target and target != folder.GetName():
                moves[target].append({'name': clip_name, 'from': folder.GetName(), 'clip': clip})
    return {'current_cuts': sorted(current_cuts), 'graphics': sorted(current - current_cuts - protected_timelines),
            'protected_timelines': sorted(protected_timelines), 'old': sorted(old),
            'delete_timelines': [timelines[name] for name in deleted_timelines],
            'delete_media': deleted_media, 'moves': moves, 'protected_media': protected_media}


def printable(the_plan):
    return {'current_cuts': the_plan['current_cuts'], 'graphics': the_plan['graphics'],
            'protected_timelines': the_plan['protected_timelines'], 'old': the_plan['old'],
            'delete_timelines': sorted(timeline.GetName() for timeline in the_plan['delete_timelines']),
            'delete_media': [f"{row['bin']}/{row['name']}" for row in the_plan['delete_media']],
            'moves': {target: [f"{row['from']}/{row['name']}" for row in rows]
                      for target, rows in the_plan['moves'].items()},
            'protected_media': [f"{row['bin']}/{row['name']}" for row in the_plan['protected_media']]}


def carry_out(manager, project, the_plan):
    pool = project.GetMediaPool()
    root = pool.GetRootFolder()
    if the_plan['delete_timelines'] and not pool.DeleteTimelines(the_plan['delete_timelines']):
        raise RuntimeError('DeleteTimelines failed')
    if the_plan['delete_media'] and not pool.DeleteClips([row['clip'] for row in the_plan['delete_media']]):
        raise RuntimeError('DeleteClips failed')
    bins = {folder.GetName(): folder for folder in root.GetSubFolderList() or []}
    for bin_name, rows in the_plan['moves'].items():
        if not rows:
            continue
        if bin_name not in bins:
            bins[bin_name] = pool.AddSubFolder(root, bin_name)
            if not bins[bin_name]:
                raise RuntimeError(f'Could not make bin {bin_name}')
        if not pool.MoveClips([row['clip'] for row in rows], bins[bin_name]):
            raise RuntimeError(f'MoveClips to {bin_name} failed')
    empty_leftover_bins = [folder for folder in (root.GetSubFolderList() or [])
                           if not folder.GetClipList() and not folder.GetSubFolderList()]
    if empty_leftover_bins and not pool.DeleteFolders(empty_leftover_bins):
        raise RuntimeError('DeleteFolders failed')
    if not manager.SaveProject():
        raise RuntimeError('SaveProject failed')


def read_back(project):
    return {'timelines': sorted(timeline.GetName() for timeline in all_timelines(project)),
            'bins': {folder.GetName(): sorted(clip.GetName() for clip in clips)
                     for folder, clips in bins_with_clips(project.GetMediaPool().GetRootFolder())}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('project', nargs='?')
    parser.add_argument('--current', action='store_true', help='tidy the project open in Resolve')
    parser.add_argument('--readme', type=Path, help="the video's versions/README.md; timelines it names are kept")
    parser.add_argument('--keep', action='append', default=[], metavar='NAME')
    parser.add_argument('--protect-prefix', action='append', default=[], metavar='PREFIX')
    parser.add_argument('--delete-pattern', action='append', metavar='GLOB')
    parser.add_argument('--graphic-pattern', action='append', metavar='GLOB')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if bool(args.project) == args.current:
        parser.error('give a PROJECT name or --current')
    import DaVinciResolveScript
    status = 0
    try:
        manager = DaVinciResolveScript.scriptapp('Resolve').GetProjectManager()
        project = manager.GetCurrentProject()
        if args.project and project.GetName() != args.project:
            project = manager.LoadProject(args.project)
            if not project:
                raise ValueError(f'No project named {args.project!r}')
        keep = args.keep + (README_TIMELINE.findall(args.readme.read_text()) if args.readme and args.readme.exists() else [])
        the_plan = plan(project, keep, args.protect_prefix, args.delete_pattern or DEFAULT_DELETE_PATTERNS,
                        args.graphic_pattern or DEFAULT_GRAPHIC_PATTERNS)
        result = {'project': project.GetName(), 'dry_run': args.dry_run, 'plan': printable(the_plan)}
        if not args.dry_run:
            carry_out(manager, project, the_plan)
            result['after'] = read_back(project)
        print(json.dumps(result, indent=1, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        status = 1
    sys.stdout.flush()
    os._exit(status)

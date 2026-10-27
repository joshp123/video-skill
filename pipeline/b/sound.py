"""Lay the edit list's sound (its `audio` rows and `sound` block) on --timeline NAME in the open project.
Written by AI on 2026-10-25 by GPT-6.1 Sol. Reads the edit list directly since 2026-10-26 (Claude Opus 5.5, stream B
of the hill-climb). One dialogue track with Resolve's own crossfades since 2026-10-26 (Claude Opus 5.5, stream I of the
hill-climb, from stream H's proven route).

sound.py EDIT_LIST --timeline NAME

The list's `sound` block names the lav, the room-tone window (`room_tone_s`), the loop crossfade and the end fade;
each `audio` row is a piece of that lav: source_in_s, source_out_s, record_s, fade_in_ms, fade_out_ms, optional
crossfade_ms, pre_roll_s, patches (room tone over a stretch of the piece), voice_isolation (0..100) and
dialogue_leveler (bool). Every piece goes on A1, in list order. A row's `crossfade_ms` makes the join into the next
row a "Cross Fade 0 dB" of that length centred on the cut; the next piece must start exactly where the row ends. Room
tone fills every other gap on A2, under the pieces' fades.

What this script does on its own, all mechanical: a room-tone fill too short for its two fades plus the one frame
Resolve keeps between them is grown equally at both ends (Resolve otherwise shortens the fades itself); a gap longer
than the room-tone window is laid as equal loops on A2, butted, with a crossfade of the list's length at each join.
Requires empty audio tracks. Replacement patches and gain patches are refused: neither is proven on one track.

Sub-frame edges and crossfades go in through a .drt round trip (the clips placed at whole frames, the crossfades added
with the API, then every edge rewritten in the file), checked edge by edge, fade by fade and crossfade by crossfade,
with the picture, captions and settings unchanged, before the original is deleted. Reports:
.cache/pipeline-b/sound/roundtrip-*/. Exit 0 when every edge, fade and crossfade reads back as laid, 2 when a fade
differs, 1 on any other fault.
"""
import argparse, importlib.util, json, math, os, re, struct, sys, tempfile, zipfile
from pathlib import Path
PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE / 'subtitles'))
from write_caption_track import read_varint, write_varint, sequence_xml
spec = importlib.util.spec_from_file_location('caption_checks', PIPELINE/'resolve/add_captions.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

def frames_text(value):
    whole = int(value // 1)
    fraction = value - whole
    return f"{whole}|{struct.pack('<d', fraction).hex()}" if fraction else str(whole)

def frames_value(text):
    if "|" in text:
        whole, hexed = text.split("|")
        return int(whole) + struct.unpack("<d", bytes.fromhex(hexed))[0]
    return float(text)

def set_blob_start(blob_hex, whole):
    raw = bytes.fromhex(blob_hex)
    assert raw[:4] == b"\x00\x00\x00\x02" and raw[8] == 0x80, blob_hex
    payload = raw[9:]
    i = payload.index(b"\xa8\x01")                      # field 21, varint: the record's whole start frame
    old, end = read_varint(payload, i + 2)
    new = payload[:i + 2] + write_varint(whole) + payload[end:]
    assert new[0] == 0x0a
    inner_old_len = payload[1]
    delta = len(new) - len(payload)
    new = bytearray(new)
    new[1] = inner_old_len + delta
    assert new[2] == 0x0a
    new[3] = new[3] + delta
    body = bytes(new)
    return (struct.pack(">I", 2) + struct.pack(">I", len(body) + 1) + b"\x80" + body).hex(), old

def lav_sample_rate(path):
    with open(path, 'rb') as wav:
        wav.seek(12)
        while True:
            chunk, size = struct.unpack('<4sI', wav.read(8))
            if chunk == b'fmt ': return struct.unpack('<HHI', wav.read(8))[2]
            wav.seek(size + size % 2, 1)

def sound_plan(edit_list, folder):
    """The edit list's sound, in the terms layout() lays it: one lav, its pieces and the room tone."""
    sound = edit_list['sound']
    lav = (Path(folder) / sound['lav']).resolve()
    for row in edit_list.get('audio', []):
        if (Path(folder) / row.get('file', sound['lav'])).resolve() != lav:
            raise ValueError(f"audio piece at {row['record_s']} s is not from the sound block's lav {lav}")
    plan = dict(lav=lav, fps=float(edit_list['fps']), duration_s=edit_list['duration_frames'] / float(edit_list['fps']),
                audio=edit_list.get('audio', []),
                **{key: sound[key] for key in ('room_tone_s', 'room_tone_crossfade_ms', 'room_tone_end_fade_ms')})
    if 'room_tone_gaps' in sound: plan['room_tone_gaps'] = sound['room_tone_gaps']
    return plan

def grown_to_fit_fades(start, end, fade_in, fade_out, frame, duration):
    """Resolve keeps a clip's two fades at least one frame shorter than the clip (measured 26 Oct on build 34:
    1.5, 2.25 and 6.25-frame clips kept 0.5, 1.25 and 5.25 frames of fade); a shorter clip grows equally at both ends."""
    missing = fade_in + fade_out + frame - (end - start)
    if missing <= 0: return start, end
    start, end = start - missing / 2, end + missing / 2
    if start < 0: start, end = 0, end - start
    if end > duration: start, end = max(0, start - (end - duration)), duration
    return start, end

DIALOGUE_TRACK, ROOM_TONE_TRACK = 1, 2


def layout(data, rate):
    """(clips, crossfades): every audio clip as {what, track, tl_in, src_in, length, fade_in, fade_out, piece}, and every
    crossfade as {at, length, outgoing, incoming}, in seconds on the timeline, snapped to the lav's samples."""
    clips, crossfades, gaps = [], [], []
    snap = lambda value: round(value * rate) / rate
    frame = 1 / data['fps']
    def add(label, track, start, end, source, fade_in, fade_out, piece=None):
        start, end, source = map(snap, (start, end, source))
        if end <= start: return
        if start < 0 or end > snap(data['duration_s']): raise ValueError(f'{label}: outside duration')
        fade_in, fade_out = min(fade_in, end-start), min(fade_out, end-start)
        clips.append(dict(what=label, track=track, tl_in=start, src_in=source, length=end-start,
                          fade_in=fade_in, fade_out=fade_out, piece=piece or {}))
    ends = []
    for index, piece in enumerate(data['audio']):
        source = snap(piece['source_in_s'] - piece.get('pre_roll_s', 0))
        start = snap(piece['record_s'] - piece.get('pre_roll_s', 0))
        end = start + snap(piece['source_out_s']) - source
        fade_in, fade_out = (min(snap(piece[key]/1000), (end-start)/2) for key in ('fade_in_ms', 'fade_out_ms'))
        if ends and start < ends[-1][1] - .5 / rate:
            raise ValueError(f'piece {index} at {piece["record_s"]} s overlaps piece {index-1}: say a crossfade_ms on that row and butt the two')
        ends.append((start, end))
        cursor, incoming = start, fade_in
        for patch in sorted(piece.get('patches', []), key=lambda p:p['source_in_s']):
            if 'gain_db' in patch: raise ValueError('gain_db patch ramps need a native proof; not implemented')
            if 'replacement_source_in_s' in patch: raise ValueError('replacement patches are not proven on one dialogue track; not implemented')
            a, b = max(start, start+patch['source_in_s']-source), min(end, start+patch['source_out_s']-source)
            if b <= a: continue
            ramp = snap(patch['fade_ms']/1000)
            add(f'piece {index}', DIALOGUE_TRACK, cursor, a, source+cursor-start, incoming, ramp, piece)
            cursor, incoming = b, ramp
        add(f'piece {index}', DIALOGUE_TRACK, cursor, end, source+cursor-start, incoming, fade_out, piece)
    for index, piece in enumerate(data['audio']):
        if 'crossfade_ms' not in piece: continue
        if index + 1 == len(ends): raise ValueError(f'piece {index} has a crossfade_ms but no piece after it')
        if abs(ends[index + 1][0] - ends[index][1]) > .5 / rate:
            raise ValueError(f'piece {index}: crossfade_ms needs the next piece to start where it ends ({ends[index][1]:.5f} s), not at {ends[index + 1][0]:.5f} s')
        crossfades.append(dict(at=ends[index][1], length=snap(piece['crossfade_ms']/1000), outgoing=f'piece {index}', incoming=f'piece {index + 1}'))
    crossfaded = {round(c['at'] * rate) for c in crossfades}
    cursor, previous_fade = 0, 0
    for c in sorted(clips,key=lambda c:c['tl_in']):
        a,b = c['tl_in'],c['tl_in']+c['length']
        if a >= cursor and not (a == cursor and round(a * rate) in crossfaded):
            gaps.append((max(0,cursor-previous_fade),a+c['fade_in'],previous_fade,c['fade_in']))
        if b > cursor: cursor, previous_fade = b,c['fade_out']
    gaps.append((cursor-previous_fade,data['duration_s'],previous_fade,data['room_tone_end_fade_ms']/1000))
    tone0, tone1 = data['room_tone_s']
    window = tone1 - tone0
    crossfade = snap(data['room_tone_crossfade_ms'] / 1000)
    longest_loop = window - crossfade
    if longest_loop <= 0: raise ValueError('Room-tone crossfade must be shorter than its window')
    for number, (a, b, fade_in, fade_out) in enumerate(data.get('room_tone_gaps', gaps)):
        a, b = grown_to_fit_fades(a, b, fade_in, fade_out, frame, data['duration_s'])
        if b - a <= window:
            add(f'tone {number}', ROOM_TONE_TRACK, a, b, tone0 + min(a % longest_loop, window - (b - a)), fade_in, fade_out)
            continue
        loops = math.ceil((b - a) / longest_loop - 1e-9)
        loop_length = snap((b - a) / loops)
        if loop_length < crossfade + frame:
            raise ValueError(f'tone {number}: the room-tone window is too short for its crossfade')
        for loop in range(loops):
            start = a + loop * loop_length
            end = b if loop == loops - 1 else start + loop_length
            add(f'tone {number}', ROOM_TONE_TRACK, start, end, tone0 + crossfade / 2,
                fade_in if loop == 0 else 0, fade_out if loop == loops - 1 else 0)
            if loop: crossfades.append(dict(at=snap(start), length=crossfade, outgoing=f'tone {number}', incoming=f'tone {number}'))
    return clips, crossfades

def planned_clips(edit_list, folder):
    """(lav, clips, crossfades): everything the list puts on the audio tracks, as layout() lays it."""
    plan = sound_plan(edit_list, folder)
    return (plan['lav'], *layout(plan, lav_sample_rate(plan['lav'])))

def set_transition_blob_start(blob_hex, whole):
    """A transition's FieldsBlob holds its whole start frame in field 21, like a clip's, with one length level fewer."""
    raw = bytes.fromhex(blob_hex)
    assert raw[:4] == b'\x00\x00\x00\x02' and raw[8] == 0x80 and raw[9] == 0x0a, blob_hex
    payload = raw[9:]
    i = payload.index(b'\xa8\x01')
    old, end = read_varint(payload, i + 2)
    new = bytearray(payload[:i + 2] + write_varint(whole) + payload[end:])
    new[1] += len(new) - len(payload)
    return (struct.pack('>I', 2) + struct.pack('>I', len(new) + 1) + b'\x80' + bytes(new)).hex()

def element_start(element):
    return frames_value(re.search(r'<Start>(.*?)</Start>', element)[1])

def audio_clips_and_crossfades(timeline, track):
    items = sorted(timeline.GetItemListInTrack('audio', track) or [], key=lambda i: i.GetStart(True))
    return [i for i in items if i.GetType() != 'transition'], [i for i in items if i.GetType() == 'transition']

def run(resolve, filename, name):
    data = json.loads(filename.read_text())
    project = resolve.GetProjectManager().GetCurrentProject()
    if data.get('resolve_project',project.GetName()) != project.GetName(): raise ValueError('Wrong open project')
    source = checks.timeline_named(project,name)
    if not source: raise ValueError(f'No timeline {name!r}')
    if any(source.GetItemListInTrack('audio',t) for t in range(1,source.GetTrackCount('audio')+1)):
        raise ValueError('Audio tracks must be empty; use the picture-only timeline')
    lav, wanted, crossfades = planned_clips(data, filename.parent)
    pool, fps, start = project.GetMediaPool(), float(source.GetSetting('timelineFrameRate')), source.GetStartFrame()
    folders, media = [pool.GetRootFolder()], None
    path = str(lav)
    while folders:
        folder = folders.pop(); folders.extend(folder.GetSubFolderList() or [])
        media = next((m for m in folder.GetClipList() or [] if m.GetClipProperty('File Path') == path),media)
    if not media: media = (pool.ImportMedia([path]) or [None])[0]
    if not media: raise ValueError('Lav import failed')
    project.SetCurrentTimeline(source)
    while source.GetTrackCount('audio') < ROOM_TONE_TRACK:
        if not source.AddTrack('audio','stereo'): raise RuntimeError('AddTrack failed')
    whole = lambda seconds: round(seconds * fps)
    for c in wanted:  # whole frames first, so clips that butt in the list butt here and take a transition
        record, end = whole(c['tl_in']), whole(c['tl_in'] + c['length'])
        first = whole(c['src_in'])
        if not pool.AppendToTimeline([dict(mediaPoolItem=media,mediaType=2,trackIndex=c['track'],startFrame=first,
            endFrame=first+max(1,end-record),recordFrame=start+record)]):
            raise RuntimeError(f'Placement failed: {c}')
    for x in crossfades:
        track = DIALOGUE_TRACK if x['outgoing'].startswith('piece') else ROOM_TONE_TRACK
        outgoing = [i for i in audio_clips_and_crossfades(source, track)[0] if i.GetEnd() - start == whole(x['at'])]
        if len(outgoing) != 1 or not outgoing[0].AddTransition(dict(type='Cross Fade 0 dB', category='audio', position='end', alignment='center', duration=2)):
            raise RuntimeError(f"AddTransition failed at {x['at']:.3f} s ({x['outgoing']} into {x['incoming']})")
    cache = PIPELINE.parent/'.cache/pipeline-b/sound'; cache.mkdir(parents=True,exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='roundtrip-',dir=cache))
    exported, rewritten = folder/'exported.drt', folder/'exact.drt'
    if not source.Export(str(exported),resolve.EXPORT_DRT,resolve.EXPORT_NONE): raise RuntimeError('Export failed')
    with zipfile.ZipFile(exported) as z: entries = {n:z.read(n) for n in z.namelist()}
    seqname, sequence = sequence_xml(exported)
    tracks = re.search(r'<AudioTrackVec>.*?</AudioTrackVec>',sequence,re.S)[0]
    new_tracks = tracks
    for index,element in enumerate(re.findall(r'<Sm2TiTrack\b.*?</Sm2TiTrack>',tracks,re.S),1):
        mine = sorted((c for c in wanted if c['track']==index),key=lambda c:c['tl_in'])
        clips = sorted(re.findall(r'<Sm2TiAudioClip\b.*?</Sm2TiAudioClip>',element,re.S),key=element_start)
        if len(mine)!=len(clips): raise RuntimeError(f'Track {index}: clip count differs')
        changed = element
        for clip,c in zip(clips,mine):
            new = clip
            for key,value in dict(Start=start+c['tl_in']*fps,Duration=c['length']*fps,In=c['src_in']*fps).items():
                new = re.sub(f'<{key}>.*?</{key}>',f'<{key}>{frames_text(value)}</{key}>',new)
            blob = re.search(r'<FieldsBlob>([0-9a-f]+)</FieldsBlob>',new)[1]
            new = new.replace(blob,set_blob_start(blob,math.floor(start+c['tl_in']*fps))[0])
            changed = changed.replace(clip,new)
        mine_x = sorted((x for x in crossfades if (DIALOGUE_TRACK if x['outgoing'].startswith('piece') else ROOM_TONE_TRACK) == index), key=lambda x: x['at'])
        transitions = sorted(re.findall(r'<Sm2TiTransition\b.*?</Sm2TiTransition>',element,re.S),key=element_start)
        if len(mine_x)!=len(transitions): raise RuntimeError(f'Track {index}: crossfade count differs')
        for transition,x in zip(transitions,mine_x):
            first = start + (x['at'] - x['length'] / 2) * fps
            new = re.sub(r'<Start>.*?</Start>', f'<Start>{frames_text(first)}</Start>', transition)
            new = re.sub(r'<Duration>.*?</Duration>', f'<Duration>{frames_text(x["length"] * fps)}</Duration>', new)
            blob = re.search(r'<FieldsBlob>([0-9a-f]+)</FieldsBlob>', new)[1]
            changed = changed.replace(transition, new.replace(blob, set_transition_blob_start(blob, math.floor(first))))
        new_tracks = new_tracks.replace(element,changed)
    entries[seqname] = sequence.replace(tracks,new_tracks).encode()
    with zipfile.ZipFile(rewritten,'w',zipfile.ZIP_DEFLATED) as z:
        for key,value in entries.items(): z.writestr(key,value)
    before = (checks.items_snapshot(source),checks.captions_snapshot(source),checks.settings_snapshot(source),checks.track_names(source))
    ids = {project.GetTimelineByIndex(i).GetUniqueId() for i in range(1,project.GetTimelineCount()+1)}
    if not source.SetName(name+' (before sound)'): raise RuntimeError('Rename failed')
    imported, rows, faults, fade_faults = None, [], [], []
    try:
        imported = pool.ImportTimelineFromFile(str(rewritten),{'importSourceClips':False})
        if not imported or (imported.GetName() != name and not imported.SetName(name)): raise RuntimeError('Import or rename failed')
        checks.set_track_names(imported, before[3])
        read_crossfades = []
        for track in range(1,imported.GetTrackCount('audio')+1):
            got, got_x = audio_clips_and_crossfades(imported, track)
            mine = sorted((c for c in wanted if c['track']==track),key=lambda c:c['tl_in'])
            mine_x = sorted((x for x in crossfades if (DIALOGUE_TRACK if x['outgoing'].startswith('piece') else ROOM_TONE_TRACK) == track), key=lambda x: x['at'])
            if len(got)!=len(mine): faults.append(f'A{track}: count mismatch')
            if len(got_x)!=len(mine_x): faults.append(f'A{track}: crossfade count {len(got_x)}, laid {len(mine_x)}')
            for item,c in zip(got,mine):
                fades = dict(FadeIn=c['fade_in']*fps,FadeOut=c['fade_out']*fps)
                if not item.SetFades(fades): fade_faults.append(f"{c['what']}: SetFades failed {fades}")
                piece = c['piece']
                if 'voice_isolation' in piece and not item.SetVoiceIsolationState(dict(isEnabled=True,amount=piece['voice_isolation'])):
                    faults.append(f"{c['what']}: Voice Isolation failed")
                if piece.get('dialogue_leveler') and not item.SetProperties(dict(AudioDialogueLevelerEnabled=True,
                    AudioDialogueLevelerMode=resolve.DIALOGUE_LEVELER_MODE_OPTIMIZE_MODERATE_LEVELS,
                    AudioDialogueLevelerReduceLoudDialogue=True,AudioDialogueLevelerLiftSoftDialogue=True,AudioDialogueLevelerBackgroundReduction=True)):
                    faults.append(f"{c['what']}: Dialogue Leveler failed")
                errors = [((item.GetStart(True)-start)/fps-c['tl_in'])*1000,
                          ((item.GetEnd(True)-start)/fps-c['tl_in']-c['length'])*1000,(item.GetLeftOffset(True)/fps-c['src_in'])*1000]
                rows.append(dict(**c,errors_ms=errors,fades=item.GetFades(),source_time_api_error_ms=(item.GetSourceStartTime()-c['src_in'])*1000))
                if any(abs(item.GetFades()[k]-v)>1e-7 for k,v in fades.items()): fade_faults.append(f"{c['what']}: fades differ")
                if any(abs(e)>=.0005 for e in errors): faults.append(f"{c['what']}: edge mismatch {errors}")
            for item,x in zip(got_x,mine_x):
                errors = [((item.GetStart(True)-start)/fps-(x['at']-x['length']/2))*1000, ((item.GetEnd(True)-start)/fps-(x['at']+x['length']/2))*1000]
                read_crossfades.append(dict(**x, track=track, errors_ms=errors))
                if any(abs(e)>=.0005 for e in errors): faults.append(f"crossfade at {x['at']:.4f} s: edge mismatch {errors}")
        after = (checks.items_snapshot(imported),checks.captions_snapshot(imported),checks.settings_snapshot(imported),checks.track_names(imported))
        if {k:v for k,v in before[0].items() if k.startswith('video')} != {k:v for k,v in after[0].items() if k.startswith('video')} or before[1:]!=after[1:]:
            faults.append('Picture, caption, settings or track-name snapshot changed')
        if project.GetTimelineCount()!=len(ids)+1: faults.append('Import added unexpected timelines')
        report = dict(timeline=name,clips=rows,crossfades=read_crossfades,mismatches=faults,fade_mismatches=fade_faults,folder=str(folder),picture_caption_settings_checked=True)
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        if faults: raise RuntimeError(f"Readback failed: {'; '.join(faults[:5])}; report {folder/'report.json'}")
    except Exception:
        added = [project.GetTimelineByIndex(i) for i in range(1,project.GetTimelineCount()+1) if project.GetTimelineByIndex(i).GetUniqueId() not in ids]
        if added: pool.DeleteTimelines(added)
        source.SetName(name)
        raise
    if not pool.DeleteTimelines([source]): raise RuntimeError('Original deletion failed')
    project.SetCurrentTimeline(imported)
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edit_list',type=Path); parser.add_argument('--timeline',required=True)
    args = parser.parse_args()
    import DaVinciResolveScript
    try: report = run(DaVinciResolveScript.scriptapp('Resolve'),args.edit_list.resolve(),args.timeline)
    except Exception as error:
        print(json.dumps(dict(error=str(error)))); sys.stdout.flush(); os._exit(1)
    print(json.dumps(report,indent=2))
    sys.stdout.flush(); os._exit(2 if report['fade_mismatches'] else 0)

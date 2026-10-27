#!/usr/bin/env python3
"""Originally written by GPT-6.1 Sol. Build edit.json's mechanical cut.
Written by AI on 2026-10-22 by GPT-6.1 Sol: data-driven timing and running picture.
Updated by AI on 2026-10-22 by GPT-6 Astra: cut-list and timing faults.

Run: python3 pipeline/cut/build_cutlist.py EDIT_FOLDER [--output build/cutlist.json]
All source seconds use the front-camera clock; file offsets are applied by consumers.
Video clips split at word-anchored shots; audio_clips split only at removed source time.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path




def normalize(text):
    return re.sub(r"[^a-z0-9']", "", text.lower().replace('’', "'"))


def matches(words, phrase):
    target = [normalize(token) for token in phrase.split()]
    tokens = [normalize(word['word']) for word in words]
    return [index for index in range(len(tokens)-len(target)+1)
            if tokens[index:index+len(target)] == target]


def cut_inputs(edit):
    """The parts of the edit data a cut depends on; camera grades and mixer-only changes are not among them, so
    changing them does not stale the cut list (faults 90 and 107 of the 22 Oct run). pipeline/graphics/prepare.mjs
    keeps the same list: change both together."""
    media=edit['media']
    inputs={key:edit[key] for key in ('format','spelling','layouts','graphics','lead_in_s') if key in edit}
    inputs['lines']=[{key:line[key] for key in ('id','words','keep','retime','cut_points','max_pause_s','pause_after_s','shots') if key in line}
                     for line in edit['lines']]
    inputs['media']={'transcript':media['transcript'],
        'lav':{key:media['lav'][key] for key in ('file','offset_s','silence_dbfs','pause_dbfs','room_tone_s') if key in media['lav']},
        'cameras':{name:{key:camera[key] for key in ('file','offset_s','camera') if key in camera}
                   for name,camera in media['cameras'].items()},
        'face_touch':media.get('face_touch',{})}
    return inputs


def edit_fingerprint(edit):
    """A hash of the cut inputs, for a short message; the readers compare the inputs themselves (cut_inputs)."""
    return hashlib.sha256(json.dumps(cut_inputs(edit),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def resolve_graphics(edit, source_timeline_words, clips, report, fps, base_frames):
    def anchor(value):
        linewords=[word for word in source_timeline_words if word['line']==value['line']]
        phrase=value.get('at',value.get('word'))
        indices=matches(linewords,phrase);n=value.get('n',0)
        if n>=len(indices):
            report['unresolved_anchors'].append({'anchor':value,'reason':'graphic occurrence absent in kept words'});return None
        first=indices[n];last=first+len(phrase.split())-1
        time=(linewords[last]['timeline_end'] if value.get('edge','start')=='end' else linewords[first]['t'])+value.get('offset_s',0)
        return {'seconds':round(time,6),'frame':round(time*fps)}
    graphics=[]
    duration=base_frames/fps
    picture_cuts=sorted({clip['rec_in_frame'] for clip in clips[1:]})
    for graphic in edit['graphics']:
        resolved=dict(graphic)
        if 'in' in graphic:resolved['in_resolved']=anchor(graphic['in'])
        if 'out' in graphic:resolved['out_resolved']=anchor(graphic['out'])
        for edge in ('in','out'):
            original=resolved.get(edge+'_resolved')
            if not original or not picture_cuts:continue
            nearest=min(picture_cuts,key=lambda frame:abs(frame-original['frame']))
            if 0<abs(nearest-original['frame'])<=8:
                snapped={'seconds':nearest/fps,'frame':nearest}
                resolved[edge+'_resolved']=snapped
                report['graphic_snaps'].append({'graphic':graphic['id'],'edge':edge,
                                                'from':original,'to':snapped})
        resolved['cues']=[{**cue,'resolved':anchor(cue['at']),
                           **({'until_resolved':anchor(cue['until'])} if 'until' in cue else {})}
                          for cue in graphic.get('cues',[])]
        if graphic.get('hold_s') and resolved.get('in_resolved'):
            frame=resolved['in_resolved']['frame']+round(graphic['hold_s']*fps)
            resolved['out_resolved']={'seconds':frame/fps,'frame':frame}
            duration=max(duration,resolved['out_resolved']['frame']/fps)
        graphics.append(resolved)
    return graphics, duration


class Lav:
    def __init__(self, path, offset, silence_dbfs, pause_dbfs):
        global np
        import numpy as np
        self.silence_dbfs = silence_dbfs
        self.pause_dbfs = pause_dbfs
        self.file = wave.open(str(path))
        self.rate, self.channels, self.width = self.file.getframerate(), self.file.getnchannels(), self.file.getsampwidth()
        self.offset = offset
        self.cache = {}

    def level(self, start, length=.03):
        key = (round(start*self.rate), round(length*self.rate))
        if key in self.cache:
            return self.cache[key]
        self.file.setpos(max(0, round((start-self.offset)*self.rate)))
        raw = self.file.readframes(round(length*self.rate))
        if self.width == 3:
            data = np.frombuffer(raw, np.uint8).reshape(-1,3).astype(np.int32)
            data = data[:,0] | data[:,1]<<8 | data[:,2]<<16
            data = np.where(data >= 1<<23, data-(1<<24), data)/(1<<23)
        elif self.width == 2:
            data = np.frombuffer(raw, '<i2').astype(np.float64)/(1<<15)
        else:
            raise ValueError(f'Unsupported PCM width: {self.width}')
        # Use the louder channel so a quiet stereo channel cannot hide speech.
        data = data.reshape(-1,self.channels)
        value = float(20*np.log10(np.max(np.sqrt(np.mean(data*data,axis=0)))+1e-12))
        self.cache[key] = value
        return value

    def boundary(self, edge, neighbour, direction):
        # Lifted from the tested builder: walk from the estimated word edge into
        # actual 30ms silence, bounded by the adjacent (possibly discarded) word.
        if direction == 'in':
            positions = np.arange(edge+.05, neighbour-.06, -.005)
            quiet = [float(t-.03) for t in positions if self.level(float(t-.03)) < self.silence_dbfs]
        else:
            positions = np.arange(edge-.05, neighbour+.06-.03, .005)
            quiet = [float(t+.03) for t in positions if self.level(float(t)) < self.silence_dbfs]
        if quiet:
            return quiet[0], True
        lo, hi = sorted((edge,neighbour))
        lo, hi = max(lo-.06,edge-.2), min(hi+.06,edge+.2)
        positions = np.arange(lo,hi+.001,.005)
        result = min(positions, key=lambda t:self.level(float(t),.01))
        return float(result), False

    def silence(self, edge, want, direction):
        count = 0
        while count+.01 <= want+1e-8:
            at = edge+count if direction == 'after' else edge-count-.01
            if self.level(at,.01) >= min(self.pause_dbfs, self.silence_dbfs):
                break
            count += .01
        return count


def build(folder, output_path=Path("build/cutlist.json"), previous_path=None, dialogue_path=None):
    folder = folder.resolve()
    output_path = folder / output_path
    if output_path.exists():
        raise FileExistsError(f'Refusing to overwrite {output_path}; choose a new --output path')
    previous_path = folder / (previous_path or Path('build/cutlist.json'))
    previous_cut = json.loads(previous_path.read_text()) if previous_path.exists() else None
    edit_path = folder/'edit/edit.json'
    raw_edit = edit_path.read_bytes()
    edit = json.loads(raw_edit)
    fps = edit['format']['fps']
    source_words = [{**word, 'word': token}
                    for word in json.loads((folder/edit['media']['transcript']).read_text())['words']
                    if not word.get('whisper_only') for token in word['word'].split()]
    for index, word in enumerate(source_words):
        word['transcript_index'] = index
    lav_data = edit['media']['lav']
    lav = Lav(folder/lav_data['file'], lav_data['offset_s'], lav_data.get('silence_dbfs', -46), lav_data.get('pause_dbfs', -40))
    camera_frames = {}
    for name, camera in edit['media']['cameras'].items():
        duration = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
            str(folder / camera['file'])], capture_output=True, text=True, check=True).stdout
        # ffprobe may print the duration once per matching stream; the first line is the video's.
        camera_frames[name] = math.floor(float(duration.split()[0]) * fps + 1e-7)
    if 'face_touch' not in edit['media']:
        print('no face-touch scans in media')
    report = {'removed_pauses': [], 'removed_words': [], 'jump_cuts': [], 'face_touches': [],
              'unresolved_anchors': [], 'boundary_warnings': [], 'pause_shortfalls': [], 'retained_by_cut_points': [],
              'graphic_snaps': []}
    planned = []
    line_kept = {}
    line_envelopes = {}
    for line in edit['lines']:
        # Corrections belong to this line; the original transcript stays intact.
        words = [dict(word) for word in source_words]
        groups, kept = [], []
        envelope = []
        spans = []
        for span in line['words']:
            firsts = matches(words,span['from'])
            firsts = [i for i in firsts if abs(words[i]['start']-span['near_s'])<=90]
            if not firsts:
                report['unresolved_anchors'].append({'line':line['id'],'anchor':span,'reason':'start phrase absent near source time'})
                continue
            first = min(firsts,key=lambda i:abs(words[i]['start']-span['near_s']))
            lasts = [i for i in matches(words,span['to']) if i>=first and words[i]['start']<=span['near_s']+90]
            if not lasts:
                report['unresolved_anchors'].append({'line':line['id'],'anchor':span,'reason':'end phrase absent after start'})
                continue
            last = min(lasts,key=lambda i:abs(words[i]['start']-span['near_s']))+len(span['to'].split())-1
            envelope.extend(range(first,last+1))
            spans.append((first,last))
        selected = [words[index] for index in envelope]
        for correction in line.get('retime',[]):
            candidates = matches(selected,correction['word'])
            occurrence = correction.get('n',0)
            if occurrence >= len(candidates):
                report['unresolved_anchors'].append({'line':line['id'],'anchor':correction,'reason':'retime occurrence absent in selected words'})
                continue
            target = selected[candidates[occurrence]]
            target['start'],target['end'] = correction['start_s'],correction['end_s']
        for first,last in spans:
            group = []
            for word in words[first:last+1]:
                if (word['word'].startswith('[') or word['word'].endswith('-')) and word['word'] not in line.get('keep',[]):
                    report['removed_words'].append({'line':line['id'],**word})
                    if group: groups.append(group); group=[]
                    continue
                if group and word['start']-group[-1]['end'] > line.get('max_pause_s',.45):
                    report['removed_pauses'].append({'line':line['id'],'source_in_s':group[-1]['end'],
                        'source_out_s':word['start'],'transcript_gap_s':round(word['start']-group[-1]['end'],6)})
                    groups.append(group);group=[]
                group.append(word); kept.append(word)
            if group: groups.append(group)
        line_kept[line['id']] = kept
        line_envelopes[line['id']] = words[min(envelope):max(envelope)+1] if envelope else []
        trims = {}
        for point in line.get('cut_points',[]):
            phrase = point.get('before',point.get('after'))
            # Like shots, fine trims address retained words, never discarded restarts.
            source_candidates = matches(kept,phrase)
            n = point.get('n',0)
            if n >= len(source_candidates):
                report['unresolved_anchors'].append({'line':line['id'],'anchor':point,'reason':'cut-point occurrence absent in kept words'})
                continue
            target = kept[source_candidates[n]]
            if target not in kept:
                report['unresolved_anchors'].append({'line':line['id'],'anchor':point,'reason':'cut-point targets discarded word'})
                continue
            key = ('in' if 'before' in point else 'out',target['transcript_index'])
            trims[key] = point
        for part, group in enumerate(groups):
            first,last = group[0]['transcript_index'],group[-1]['transcript_index']
            previous = words[first-1]['end'] if first else group[0]['start']-.6
            following = words[last+1]['start'] if last+1<len(words) else group[-1]['end']+.6
            src_in, quiet_in = lav.boundary(group[0]['start'],previous,'in')
            src_out, quiet_out = lav.boundary(group[-1]['end'],following,'out')
            exact_in = trims.get(('in',first)); exact_out = trims.get(('out',last))
            if exact_in:
                src_in = exact_in['in_s']
                for retained in words[:first]:
                    if retained['end']-max(src_in,retained['start'])>=.03 and retained['start']<group[0]['start']:
                        report['retained_by_cut_points'].append({'line':line['id'],'word':retained['word'],
                            'source_start_s':max(src_in,retained['start']),'source_end_s':retained['end'],
                            'reason':'exact in-point precedes requested first word'})
            if exact_out: src_out = exact_out['out_s']
            for key, point in trims.items():
                edge,index=key
                if first<index<=last and edge=='in' or first<=index<last and edge=='out':
                    report['unresolved_anchors'].append({'line':line['id'],'anchor':point,'reason':'fine trim is inside a continuous retained run; requires explicit span split'})
            for edge,value,quiet,exact in [('in',src_in,quiet_in,exact_in),('out',src_out,quiet_out,exact_out)]:
                if not quiet and not exact:
                    report['boundary_warnings'].append({'line':line['id'],'part':part,'edge':edge,'source_s':round(value,6),'reason':'adjacent words have no 30ms silence; quietest boundary used','db':round(lav.level(value,.01),1)})
            planned.append({'line':line['id'],'part':part,'run':group,'audio_in_s':src_in,'audio_out_s':src_out,
                            'exact_in':bool(exact_in),'exact_out':bool(exact_out)})
    # The final word's fricative must finish before the sound ends. A 30ms dip
    # inside a quiet final consonant is not its end: require sustained room tone.
    final=planned[-1]
    final_word=final['run'][-1]
    next_index=final_word['transcript_index']+1
    next_start=words[next_index]['start'] if next_index<len(words) else final_word['end']+1
    if not final['exact_out']:
        candidates=np.arange(final_word['end']-.05,next_start-.08,.005)
        quiet=[float(t) for t in candidates if lav.level(float(t),.08)<lav.silence_dbfs and lav.level(float(t),.03)<lav.silence_dbfs]
        if quiet:
            final['audio_out_s']=quiet[0]+.03
            final['acoustic_end_s']=quiet[0]
        else:
            report['boundary_warnings'].append({'line':final['line'],'part':final['part'],
                'edge':'out','source_s':round(final['audio_out_s'],6),
                'reason':'last word has no sustained 80ms silence; normal edge retained'})
    for segment in planned:
        edge = segment['audio_out_s']
        edge_db = lav.level(edge-.03,.03)
        following_db = lav.level(edge,.03)
        if following_db > edge_db + 10:
            report['boundary_warnings'].append({'line':segment['line'],'part':segment['part'],
                'edge':'out','source_s':round(edge,6),'reason':'30ms after out-point rises more than 10dB',
                'edge_dbfs':round(edge_db,2),'following_dbfs':round(following_db,2)})
    room_start,room_end=lav_data['room_tone_s']
    room_db=float(np.median([lav.level(float(t),.01) for t in np.arange(room_start,room_end-.01,.01)]))
    report['pause_warnings']=[]
    # Keep requested line pauses in actual adjacent source silence. Never extend an exact trim.
    by_id = {line['id']:line for line in edit['lines']}
    pause_shortfalls = {}
    for outgoing,incoming in zip(planned,planned[1:]):
        if outgoing['line']==incoming['line']:continue
        want=by_id[outgoing['line']].get('pause_after_s',.25)
        after=0 if outgoing['exact_out'] else lav.silence(outgoing['audio_out_s'],want,'after')
        before=0 if incoming['exact_in'] else lav.silence(incoming['audio_in_s'],want-after,'before')
        outgoing['audio_out_s']+=after;incoming['audio_in_s']-=before
        for segment,edge,at in ((outgoing,'out',outgoing['audio_out_s']-.01),
                                (incoming,'in',incoming['audio_in_s'])):
            level=lav.level(at,.01)
            if level>room_db+6:
                report['pause_warnings'].append({'line':segment['line'],'part':segment['part'],
                    'edge':edge,'source_s':round(at,6),'dbfs':round(level,2),
                    'room_dbfs':round(room_db,2),'reason':'pause edge more than 6dB above room'})
        if want-after-before>.005:
            shortage = {'after_line':outgoing['line'],'requested_s':want,'available_adjacent_s':round(after+before,6),
                        'reason':'insufficient source silence; exact trims preserved'}
            report['pause_shortfalls'].append(shortage)
            pause_shortfalls[outgoing['line']] = shortage
    clips,audio_clips,timeline_words=[],[],[]
    rec=round(edit.get('lead_in_s',0)*fps)
    for segment_index,segment in enumerate(planned):
        run=segment['run'];line=by_id[segment['line']]
        source_in=math.floor(segment['audio_in_s']*fps+1e-7)
        source_out=math.ceil(segment['audio_out_s']*fps-1e-7)
        frames=source_out-source_in
        if frames<=0:raise ValueError(f"Nonpositive duration in {segment['line']}")
        offset=rec/fps-source_in/fps
        audio={k:v for k,v in segment.items() if k not in ('run',)}
        audio.update(src_in_frame=source_in,src_out_frame=source_out,rec_in_frame=rec,frames=frames,
                     audio_timeline_in_s=segment['audio_in_s']+offset)
        audio_clips.append(audio)
        for warning in report['boundary_warnings']:
            if warning['line']==segment['line'] and warning['part']==segment['part']:
                warning['timeline_s']=round(warning['source_s']+offset,6)
        for word in run:
            timeline_words.append({'line':segment['line'],'word':word['word'],'source_word':word['word'],
               'source_start_s':word['start'],'source_end_s':segment.get('acoustic_end_s',word['end']) if word is run[-1] else word['end'],
               't':max(rec/fps,word['start']+offset),'end':min((rec+frames)/fps,(segment.get('acoustic_end_s',word['end']) if word is run[-1] else word['end'])+offset),
               'transcript_index':word['transcript_index']})
        # Resolve shots within the kept line, then locate any switches in this run.
        shots=[]
        for shot in line['shots']:
            indices=matches(line_kept[line['id']],shot['from']);n=shot.get('n',0)
            if n>=len(indices):
                report['unresolved_anchors'].append({'line':line['id'],'anchor':shot,'reason':'shot occurrence absent in kept words'});continue
            word=line_kept[line['id']][indices[n]]
            shots.append((word['transcript_index'],shot,word))
        active=[shot for index,shot,word in shots if index<=run[0]['transcript_index']]
        if not active:raise ValueError(f"No opening camera for {line['id']}")
        current=active[-1];boundaries=[(0,current)]
        for index,shot,word in shots:
            if run[0]['transcript_index']<index<=run[-1]['transcript_index']:
                boundary=max(1,min(frames-1,round((word['start']-source_in/fps)*fps)))
                boundaries.append((boundary,shot))
        for index,(start,shot) in enumerate(boundaries):
            end=boundaries[index+1][0] if index+1<len(boundaries) else frames
            if end<=start:continue
            camera=shot['camera']
            clips.append({'line':line['id'],'part':segment['part'],'camera':camera,'zoom':shot.get('zoom',1),
               **({'panel_framing':shot['panel_framing']} if 'panel_framing' in shot else {}),
               'why':shot['why'],'src_in_frame':source_in+start,'src_out_frame':source_in+end,
               'rec_in_frame':rec+start,'frames':end-start,
               'camera_src_in_frame':round((source_in+start)/fps*fps-edit['media']['cameras'][camera]['offset_s']*fps),
               'audio_segment':len(audio_clips)-1,
               'picture_offset_frames':shot.get('picture_offset_frames',0) if
                   any(candidate is shot and run[0]['transcript_index']<=token<=run[-1]['transcript_index']
                       for token,candidate,word in shots) else 0})
        rec+=frames
        shortage = pause_shortfalls.get(segment['line'])
        if shortage and segment_index+1<len(planned) and planned[segment_index+1]['line']!=segment['line']:
            incoming = planned[segment_index+1]
            incoming_source_in = math.floor(incoming['audio_in_s']*fps+1e-7)
            pause = source_out/fps-run[-1]['end'] + incoming['run'][0]['start']-incoming_source_in/fps
            gap = max(0,round((shortage['requested_s']-pause)*fps))
            outgoing = clips[-1]
            available = max(0,camera_frames[outgoing['camera']] - outgoing['camera_src_in_frame'] - outgoing['frames'])
            supplied = min(gap,available)
            outgoing['frames']+=supplied;outgoing['src_out_frame']+=supplied
            shortage.update(supplied=supplied==gap,film_frames=gap,picture_frames=supplied)
            rec+=gap
    report['pause_shortfalls']=[item for item in report['pause_shortfalls'] if item.get('film_frames',0)>0]
    # Split edits move only the picture edge. Extend each side on its own source
    # clock, including where the sound edit removes time between two takes.
    for index,clip in enumerate(clips):
        shift=clip['picture_offset_frames']
        clip['sound_join_frame']=clip['rec_in_frame']
        if not shift:continue
        if not index:raise ValueError('The opening shot cannot move before or after the timeline start')
        previous=clips[index-1]
        if previous['frames']+shift<=0 or clip['frames']-shift<=0:
            raise ValueError(f"Picture offset consumes a shot in {clip['line']}")
        previous['frames']+=shift;previous['src_out_frame']+=shift
        clip['rec_in_frame']+=shift;clip['src_in_frame']+=shift;clip['frames']-=shift
        camera_offset=edit['media']['cameras'][clip['camera']]['offset_s']
        clip['camera_src_in_frame']=round(clip['src_in_frame']-camera_offset*fps)
    # Equal-length spelling changes preserve each spoken word's timing.
    for original,replacement in edit.get('spelling',[]):
        index=0; parts=original.split()
        while index<=len(timeline_words)-len(parts):
            group=timeline_words[index:index+len(parts)]
            if len({word['line'] for word in group})==1 and ' '.join(word['word'] for word in group)==original:
                replacements=replacement.split()
                if len(replacements)==len(parts):
                    for word,display in zip(group,replacements):word['word']=display
                    index+=len(parts)
                    continue
                if not replacements:
                    del timeline_words[index:index+len(parts)]
                    continue
                merged={**group[0],'word':replacement,'source_word':' '.join(word['source_word'] for word in group),
                        'source_end_s':group[-1]['source_end_s'],'end':group[-1]['end']}
                timeline_words[index:index+len(parts)]=[merged]
            index+=1
    for word in timeline_words:
        word['start_frame']=math.floor(word['t']*fps+1e-7)
        word['end_frame']=math.ceil(word['end']*fps-1e-7)
    # Cues match original transcript tokens, independent of display spelling.
    source_timeline_words=[]
    for segment,audio in zip(planned,audio_clips):
        offset=audio['rec_in_frame']/fps-audio['src_in_frame']/fps
        for word in segment['run']:
            source_timeline_words.append({**word,'line':segment['line'],
                't':max(audio['rec_in_frame']/fps,word['start']+offset),
                'timeline_end':min((audio['rec_in_frame']+audio['frames'])/fps,(segment.get('acoustic_end_s',word['end']) if word is segment['run'][-1] else word['end'])+offset)})
    if previous_cut and previous_cut['audio_clips']==audio_clips:
        aligned={(w['line'],w['transcript_index'],w['source_word']):w for w in previous_cut['words']}
        for word in timeline_words:
            old=aligned.get((word['line'],word['transcript_index'],word['source_word']),{})
            word.update({key:value for key,value in old.items() if key.startswith('aligned_') or key=='alignment_score'})
        for word in source_timeline_words:
            old=next((w for w in timeline_words if w['line']==word['line'] and
                w['transcript_index']<=word['transcript_index']<w['transcript_index']+len(w['source_word'].split())),None)
            if old and 'aligned_start_s' in old:
                word['t']=old['aligned_start_frame']/fps;word['timeline_end']=old['aligned_end_frame']/fps
    graphics,duration=resolve_graphics(edit,source_timeline_words,clips,report,fps,rec)
    # Associate removed pauses with their actual timeline join.
    for previous,current in zip(audio_clips,audio_clips[1:]):
        if previous['line']!=current['line']:continue
        removed=current['audio_in_s']-previous['audio_out_s']
        if removed<=.001:continue
        at=current['rec_in_frame']/fps
        for pause in report['removed_pauses']:
            if pause['line']==current['line'] and abs(pause['source_out_s']-planned[audio_clips.index(current)]['run'][0]['start'])<.001:
                pause.update(timeline_s=round(at,6),removed_s=round(removed,6))
    def layout_at(frame):
        layout='picture'
        for graphic in graphics:
            if graphic.get('layout') not in edit['layouts']:continue
            start,end=graphic.get('in_resolved'),graphic.get('out_resolved')
            if start and end and start['frame']<=frame<end['frame']:
                layout=graphic['layout']
        return layout
    # Every picture join counts, including reordered source time between lines.
    for previous,current in zip(clips,clips[1:]):
        source_gap=current['src_in_frame']-previous['src_out_frame']
        if (previous['camera']!=current['camera'] or source_gap==0 or
            previous['zoom']!=current['zoom'] or previous.get('panel_framing')!=current.get('panel_framing') or
            'screen' in edit['media']['cameras'][current['camera']].get('camera','').lower()):continue
        frame=current['rec_in_frame']
        before_layout,after_layout=layout_at(frame-1),layout_at(frame)
        layout=edit['layouts'][after_layout]
        if layout.get('graphic') and not layout.get('picture') or before_layout!=after_layout:continue
        report['jump_cuts'].append({'line':current['line'],'previous_line':previous['line'],
            'timeline_s':frame/fps,'frame':frame,'camera':current['camera'],
            'removed_s':source_gap/fps})
    touches={}
    for camera,path in edit['media'].get('face_touch',{}).items():
        with (folder/path).open() as file:
            # Existing scans are already on the front-camera clock.
            touches[camera]=[float(row['seconds']) for row in csv.DictReader(file) if row['touching']=='1']
    for clip in clips:
        hits=[time for time in touches.get(clip['camera'],[]) if clip['src_in_frame']/fps-.2<=time<=clip['src_out_frame']/fps+.2]
        clip['face_touch_source_s']=hits
        if hits:report['face_touches'].append({'line':clip['line'],'camera':clip['camera'],'timeline_s':clip['rec_in_frame']/fps,'source_s':hits})
    # The final camera keeps rolling under the last graphic.
    last = clips[-1]
    extra = round(duration*fps) - (last['rec_in_frame']+last['frames'])
    available = max(0,camera_frames[last['camera']] - last['camera_src_in_frame'] - last['frames'])
    supplied = min(extra,available)
    last['frames']+=supplied;last['src_out_frame']+=supplied
    picture_frames=last['rec_in_frame']+last['frames']
    if supplied<extra:
        report['picture_shortfalls']=[{'after_line':last['line'],'camera':last['camera'],
            'requested_frames':extra,'available_frames':supplied,'reason':'source footage ends before film'}]
    line_order=[line['id'] for line in edit['lines']]
    for shortage in list(report['pause_shortfalls']):
        next_line=line_order[line_order.index(shortage['after_line'])+1]
        outgoing=max(w['end'] for w in timeline_words if w['line']==shortage['after_line'])
        incoming=min(w['t'] for w in timeline_words if w['line']==next_line)
        shortage['timeline_pause_s']=round(incoming-outgoing,6)
    dialogue_report=folder/'build/dialogue-report.json'
    if dialogue_path is None and dialogue_report.exists():
        dialogue_path=Path(json.loads(dialogue_report.read_text())['output'])
    if dialogue_path is not None:
        dialogue_path=folder/dialogue_path
        with wave.open(str(dialogue_path)) as audio:
            samples,rate=audio.getnframes(),audio.getframerate()
        if samples!=round(duration*rate):
            report['dialogue_length_mismatch']={'file':str(dialogue_path),'samples':samples,
                'required_samples':round(duration*rate),
                'next_step':'Rebuild dialogue with build_dialogue.py using this cut list before alignment, graphics or timeline building.'}
    report['anchor_scope'] = 'Shots, fine cut_points and graphics count kept words before display spelling.'
    report['built_as_written'] = not (report['unresolved_anchors'] or report['boundary_warnings'] or
        any(not shortage['supplied'] for shortage in report['pause_shortfalls']) or report.get('picture_shortfalls') or report.get('dialogue_length_mismatch'))
    report['total_length_s']=round(duration,6)
    output={'_about':'Generated by pipeline/cut/build_cutlist.py from edit/edit.json. Written by AI on 2026-10-21 by GPT-6.1 Sol. Do not edit.',
        'edit_sha256':edit_fingerprint(edit),'cut_inputs':cut_inputs(edit),'fps':fps,'format':edit['format'],'media':edit['media'],
        'duration_s':duration,'duration_frames':round(duration*fps),'picture_duration_s':picture_frames/fps,
        'picture_duration_frames':picture_frames,'clips':clips,'audio_clips':audio_clips,'words':timeline_words,
        'graphics':graphics,'layouts':edit['layouts'],'report':report}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open('x') as file:
        file.write(json.dumps(output,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(f"{len(clips)} picture clips, {len(audio_clips)} audio segments, {duration:.2f}s total; picture {picture_frames/fps:.2f}s")
    if report['unresolved_anchors']:raise SystemExit(2)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edit_folder',type=Path)
    parser.add_argument('--output',type=Path,default=Path('build/cutlist.json'))
    parser.add_argument('--previous',type=Path,help='Previous aligned cut list (default: EDIT/build/cutlist.json)')
    parser.add_argument('--dialogue',type=Path,help='Check this dialogue length (default: output in build/dialogue-report.json)')
    args=parser.parse_args()
    build(args.edit_folder,args.output,args.previous,args.dialogue)

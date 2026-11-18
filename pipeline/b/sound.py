"""Lay the edit list's sound (its `audio` rows and `sound` block) on a timeline: the dialogue on A1, room tone on A2.

Written by AI on 2026-10-25 by GPT-6.1 Sol; one dialogue track with Resolve's own crossfades since 2026-10-26 (Claude
Opus 5.5, hill-climb streams B and I). Rewritten on 2026-11-17 by Claude Opus 5.5 for Resolve 21.2: every edge is placed
by the sub-frame calls (SetLeftOffset, SetRightOffset, SetPosition with subframePrecision), not through the timeline
file; only each crossfade's sub-frame start and length still go through the file (timeline_file.py), because no call
sets them.

The list's `sound` block names the lav, the room-tone window (`room_tone_s`), the loop crossfade and the end fade; each
`audio` row is a piece of that lav: source_in_s, source_out_s, record_s, fade_in_ms, fade_out_ms, optional
crossfade_ms, pre_roll_s, patches (room tone over a stretch of the piece), voice_isolation (0..100) and
dialogue_leveler (bool). A row's `crossfade_ms` makes the join into the next row a "Cross Fade +3 dB" (constant power) of that length
centred on the cut; the next piece must start exactly where the row ends. Room tone fills every other gap on A2, under
the pieces' fades. Mechanical only: a room-tone fill too short for its two fades plus one frame is grown equally at
both ends (Resolve shortens the fades otherwise); a gap longer than the room-tone window is laid as equal loops,
crossfaded. Replacement and gain patches are refused: neither is proven on one track.

Resolve's "Align audio edits to frame boundaries" preference must be off: with it on, the sub-frame calls return True
and round to whole frames (smoke tests, 17 Nov). Every edge is read back to 0.5 ms.
"""
import math
import struct
from pathlib import Path

import session

DIALOGUE_TRACK, ROOM_TONE_TRACK = 1, 2
# Constant power, as `joins check --lav` simulates a join and as its model was trained. Resolve's "Cross Fade 0 dB" is a
# linear crossfade (it matched the lav joined with linear ramps to -93 dB or better, 18 Nov), and with it the render's
# join scores rose above the lav check's by up to 0.25: one clean join was flagged in the render only.
CROSSFADE = "Cross Fade +3 dB"


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



def place_piece(pool, timeline, media, clip, fps):
    """One audio clip with exact sub-frame edges. It is appended a frame after its place, whole frames inside its source
    range, so it never overwrites the piece before it; then its head is trimmed to the exact source frame, it is moved
    to its exact record frame, and its tail trimmed to its exact end."""
    start = timeline.GetStartFrame()
    record, source, length = clip["tl_in"] * fps, clip["src_in"] * fps, clip["length"] * fps
    first = math.ceil(source)
    item = (pool.AppendToTimeline([{"mediaPoolItem": media, "mediaType": 2, "trackIndex": clip["track"],
                                    "startFrame": first, "endFrame": first + max(1, math.floor(length)),
                                    "recordFrame": start + math.ceil(record) + 1}]) or [None])[0]
    if item is None:
        raise RuntimeError(f"Could not place {clip['what']} at {clip['tl_in']:.4f} s")
    ok = (item.SetLeftOffset(source, True) and item.SetPosition({"startFrame": start + record}, True, True)
          and item.SetRightOffset(item.GetRightOffset(True) + item.GetEnd(True) - (start + record + length), True))
    errors_ms = [(item.GetStart(True) - start - record) / fps * 1000, (item.GetEnd(True) - start - record - length) / fps * 1000,
                 (item.GetLeftOffset(True) - source) / fps * 1000]
    if not ok or any(abs(e) > 0.5 for e in errors_ms):
        raise RuntimeError(f"{clip['what']}: edges read back {errors_ms} ms off (calls returned {ok}); is "
                           "Resolve's 'Align audio edits to frame boundaries' on?")
    return item


def lay(resolve, project, timeline, data, folder):
    """Every audio clip of the list on TIMELINE (its audio tracks empty), exact to the sample in its edges and fades,
    with each crossfade added at whole frames. Returns {clips, crossfades}: the crossfades as timeline_file.rewrite takes
    them, in frames, for the file pass that gives them their exact start and length."""
    if session.align_audio_to_frames():
        raise RuntimeError("Resolve's 'Align audio edits to frame boundaries' preference is on: turn it off first")
    lav, wanted, crossfades = planned_clips(data, folder)
    pool, start = project.GetMediaPool(), timeline.GetStartFrame()
    fps = float(timeline.GetSettings()["timelineFrameRate"])
    media = None
    folders = [pool.GetRootFolder()]
    while folders and media is None:
        current = folders.pop()
        folders.extend(current.GetSubFolderList() or [])
        media = next((m for m in current.GetClipList() or [] if m.GetClipProperty("File Path") == str(lav)), None)
    media = media or (pool.ImportMedia([str(lav)]) or [None])[0]
    if media is None:
        raise RuntimeError(f"Could not import the lav {lav}")
    if any(timeline.GetItemListInTrack("audio", t) for t in range(1, timeline.GetTrackCount("audio") + 1)):
        raise RuntimeError("The audio tracks must be empty")
    while timeline.GetTrackCount("audio") < ROOM_TONE_TRACK:
        timeline.AddTrack("audio", "stereo")
    placed = []
    for clip in sorted(wanted, key=lambda c: (c["track"], c["tl_in"])):
        item = place_piece(pool, timeline, media, clip, fps)
        fades = {"FadeIn": clip["fade_in"] * fps, "FadeOut": clip["fade_out"] * fps}
        if not item.SetFades(fades) or any(abs(item.GetFades()[k] - v) > 1e-6 for k, v in fades.items()):
            raise RuntimeError(f"{clip['what']}: fades {fades} read back {item.GetFades()}")
        piece = clip["piece"]
        if "voice_isolation" in piece and not item.SetVoiceIsolationState({"isEnabled": True, "amount": piece["voice_isolation"]}):
            raise RuntimeError(f"{clip['what']}: Voice Isolation failed")
        if piece.get("dialogue_leveler") and not item.SetProperties({
                "AudioDialogueLevelerEnabled": True, "AudioDialogueLevelerMode": resolve.DIALOGUE_LEVELER_MODE_OPTIMIZE_MODERATE_LEVELS,
                "AudioDialogueLevelerReduceLoudDialogue": True, "AudioDialogueLevelerLiftSoftDialogue": True,
                "AudioDialogueLevelerBackgroundReduction": True}):
            raise RuntimeError(f"{clip['what']}: Dialogue Leveler failed")
        placed.append((clip, item))
    exact = []
    for x in crossfades:
        track = DIALOGUE_TRACK if x["outgoing"].startswith("piece") else ROOM_TONE_TRACK
        outgoing = [item for clip, item in placed if clip["track"] == track and abs(item.GetEnd(True) - start - x["at"] * fps) < 1e-3]
        if len(outgoing) != 1 or not outgoing[0].AddTransition({"type": CROSSFADE, "category": "audio", "position": "end",
                                                                 "alignment": "center", "duration": 2}):
            raise RuntimeError(f"AddTransition failed at {x['at']:.4f} s ({x['outgoing']} into {x['incoming']})")
        exact.append({"track": track, "start": (x["at"] - x["length"] / 2) * fps, "length": x["length"] * fps})
    return {"clips": len(placed), "crossfades": exact}

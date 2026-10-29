#!/usr/bin/env python3
"""Measure a rendered cut against skill-b/tools/faults.md and list every fault with its frame and evidence.

Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream A, the fault instrument).
The numbers that decide each class are named below and explained in tools/faults.md. This tool measures;
rows marked "look" or "listen" are places a model or Josh must judge, and never fail the gate.

usage: qc.py CUT.mp4 [--edit-list EDIT_LIST] [--out DIR] [--heard-words FILE] [--range FIRST LAST] [--only CHECK ...]
Defaults: the edit list is CUT's video folder's edit-list.json, the report goes to the video folder's build/qc/<cut name>/.
Writes report.json, report.md and evidence/ there. Exits 1 when any row is a fault, 0 when none.
--range FIRST LAST: timeline frames, inclusive, as render_timeline.py --range takes them. CUT is either a render of that
span (render it with the loudness preset loaded, so its level is the delivery's) or of the whole timeline; only rows inside
the span are reported, at timeline frames. --only runs the named checks and nothing else (see CHECKS below), so a role runs
the gate itself on the class it is fixing, in seconds for sound joins, instead of a copy of its tests.
Run it with pipeline/.devenv/profile/bin/python3; it needs ffmpeg, ffprobe and swiftc (Xcode's) on PATH.
Takes the cuts on him from the list, with the pixels as a cross-check, since 2026-10-26 (stream A, after stream I
found a pixel cut firing mid-shot on encoder noise). Reads the picture from the list's `segments` (each a moment of its camera's file) and `panels` since 2026-10-26
(Claude Opus 5.5, stream I of the hill-climb); the colour reference is the camera the list's `cameras` marks
`reference`.
Since 2026-10-27 (Claude Opus 5.5, hill-climb stream L, after run 4's gate passed a build a cold judge failed): lit caption
words against their onsets on the cut's own sound, caption pills and letters against the look's safe line, --range and --only.
Sync offsets from the edit list's picture offsets since 2026-10-29 (Claude Opus 5.5): a camera's `picture_offset_s`, set picture
against picture at ingest, replaces its own microphone, because the Pocket's microphone is the lav's radio feed, which arrives
30 to 60 ms after its picture. A camera without one is still timed by its microphone, and the report says so.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

EDITS = Path(__file__).resolve().parents[2]
VISION_SOURCE = Path(__file__).with_name('qc_vision.swift')

# The numbers that decide each class (tools/faults.md says why each is where it is).
EYES_CLOSED_FRACTION_OF_SHOT_NORMAL = 0.65
FRAMES_EACH_SIDE_OF_A_CUT = 3
OUT_OF_SYNC_SECONDS = 0.06
OUT_OF_SYNC_FAULT_FRAMES = 4
MICROPHONE_OFFSET_WARNING = "offset from this camera's microphone; the Pocket's radio feed can lag the picture by 30 to 60 ms"
SPEECH_DBFS = -30
SILENCE_DBFS = -38
HARD_JOIN_STEP_DB = 6
HARD_JOIN_EXCESS_OVER_LAV_DB = 10
LISTEN_JOIN_EXCESS_OVER_LAV_DB = 6
# A step is in his voice when its louder side is at speech level, or this far above the room tone around the join: a word's
# weak tail cut into room tone after a short fade-out sits under -30 dBFS and is still heard as a chop (run 4, 50.43 s).
JOIN_ABOVE_ROOM_TONE_DB, ROOM_TONE_SEARCH_SECONDS = 12, 0.1
CONTIGUOUS_SOURCE_SECONDS = 0.03
PAUSE_DBFS, WORD_ONSET_RISE_DB, CLEAR_SPEECH_DBFS, FRAGMENT_LONGEST_SECONDS = -33, 10, -25, 0.25
LIT_WORD_PILL_FRACTION = 0.3
WORD_SEARCH_SECONDS = 2.0
CAPTION_ON_FACE_GAP_FRAMES = 2
FACE_JUMP_FRACTION = 0.05
SKIN_RED_GREEN_ABOVE_REFERENCE, SKIN_BLUE_GREEN_FROM_REFERENCE = 0.015, 0.015
LOUDNESS_TARGET_LUFS, LOUDNESS_TOLERANCE_LU, TRUE_PEAK_CEILING_DBTP = -14.0, 1.0, -1.0
PHONE_WIDTH_PX, SMALLEST_READABLE_TEXT_AT_PHONE_WIDTH_PX = 390, 13
PLATFORM_TOP_CONTROLS_PX = 200
FULL_FRAME_TEXT_EVERY_N_FRAMES = 25
CAPTION_BAND_HALF_HEIGHT_PX = 205
CUT_BAND_DIFFERENCE, CUT_BAND_ABOVE_NEIGHBOURS, CUT_WHOLE_FRAME_DIFFERENCE = 12, 8, 10
AUDIO_RATE = 48000
# Lit words against his voice: an onset is a rise of ONSET_RISE_DB or more within ONSET_PEAK_WITHIN_SECONDS out of a dip of at
# least ONSET_DIP_SECONDS, reaching speech; after a pause (PAUSE_BEFORE_ONSET_SECONDS all under PAUSE_DBFS) it can only be a
# word's start. A lit word more than WORD_ONSET_TOLERANCE_FRAMES from its onset is early or late.
TRACE_HOP_SECONDS, TRACE_WINDOW_SECONDS = 0.005, 0.01
ONSET_DIP_SECONDS, ONSET_RISE_DB, ONSET_START_ABOVE_DIP_DB, ONSET_PEAK_WITHIN_SECONDS = 0.03, 10, 3, 0.08
PAUSE_BEFORE_ONSET_SECONDS = 0.1
WORD_ONSET_TOLERANCE_FRAMES = 3
HEARD_WORD_TO_ONSET_FRAMES = 1.5
NO_LIT_WORD_AFTER_PAUSE_FRAMES = 12
# Caption pills and letters against the safe line: read across the middle half of each caption line's height, where the pill and
# the letters always are and the picture behind seldom is white or orange; ink within CAPTION_INK_GAP_PX of the line's ink is the line's.
CAPTION_INK_GAP_PX = 40


def picture_clips(edit_list):
    """Every picture clip as {file, source_in, source_out, record, track, speed_percent}: each segment as a clip of its
    camera's file on V2, each panel as it is."""
    segments = [{'file': edit_list['cameras'][row['camera']]['file'], 'source_in': row['source_in'],
                 'source_out': row['source_in'] + row['frames'], 'record': row['record'], 'track': 2,
                 **{key: row[key] for key in ('speed_percent', 'retime', 'framing') if key in row}}
                for row in edit_list.get('segments', [])]
    return segments + edit_list.get('panels', []) + edit_list.get('clips', [])  # clips: the list before segments


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, **kwargs)


def decode_audio_mono(path, rate=AUDIO_RATE):
    raw = run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-af', 'pan=mono|c0=c0',
               '-ar', str(rate), '-f', 'f32le', '-']).stdout
    return np.frombuffer(raw, np.float32)


def level_dbfs(samples):
    return 20 * math.log10(math.sqrt(float(np.mean(samples.astype(np.float64) ** 2))) + 1e-9) if len(samples) else -120.0


def level_at(audio, start_s, end_s):
    return level_dbfs(audio[max(0, int(start_s * AUDIO_RATE)):max(0, int(end_s * AUDIO_RATE))])


def best_lag(reference, segment):
    """Lag (samples) of segment inside reference with the highest normalised correlation, and that correlation."""
    size = 1 << (len(reference) + len(segment)).bit_length()
    correlation = np.fft.irfft(np.fft.rfft(reference, size) * np.conj(np.fft.rfft(segment, size)), size)[:len(reference) - len(segment) + 1]
    running = np.concatenate([[0.0], np.cumsum(reference.astype(np.float64) ** 2)])
    window_energy = np.maximum(running[len(segment):] - running[:-len(segment)], 0)
    energy = np.sqrt(window_energy) * np.sqrt(np.sum(segment.astype(np.float64) ** 2)) + 1e-12
    normalised = correlation / energy
    lag = int(np.argmax(normalised))
    return lag, float(normalised[lag])


def edit_list_for_span(edit_list, first, last, fps):
    """The edit list as a render of timeline frames first to last sees it: every clip and sound piece trimmed to the span
    and moved so the span's first frame is 0."""
    span = dict(edit_list, duration_frames=last - first + 1)

    def trimmed_clip(clip, length_key):
        speed = clip.get('speed_percent', 100) / 100 if clip.get('speed_percent', 100) >= 100 else 1
        frames_on_timeline = clip['frames'] if length_key == 'frames' else round((clip['source_out'] - clip['source_in']) / speed)
        start, end = max(clip['record'], first), min(clip['record'] + frames_on_timeline, last + 1)
        if end <= start:
            return None
        clip = dict(clip, record=start - first, source_in=clip['source_in'] + (start - clip['record']) * speed)
        if length_key == 'frames':
            clip['frames'] = end - start
        else:
            clip['source_out'] = clip['source_in'] + (end - start) * speed
        return clip

    for key, length_key in (('segments', 'frames'), ('panels', 'source_out'), ('clips', 'source_out')):
        if key in edit_list:
            span[key] = [c for c in (trimmed_clip(clip, length_key) for clip in edit_list[key]) if c]
    first_s, end_s = first / fps, (last + 1) / fps
    pieces = []
    for piece in edit_list.get('audio', []):
        length = piece['source_out_s'] - piece['source_in_s']
        start, end = max(piece['record_s'], first_s), min(piece['record_s'] + length, end_s)
        if end > start:
            pieces.append(dict(piece, record_s=start - first_s, source_in_s=piece['source_in_s'] + start - piece['record_s'],
                               source_out_s=piece['source_in_s'] + end - piece['record_s']))
    span['audio'] = pieces
    return span


class Cut:
    def __init__(self, cut_path, edit_list_path, out_dir, heard_words_file=None, span=None):
        self.path, self.out = cut_path, out_dir
        self.edit_list = json.load(open(edit_list_path))
        self.heard_words_file = heard_words_file
        probe = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                'stream=width,height,r_frame_rate,nb_frames', '-of', 'json', str(cut_path)]).stdout)['streams'][0]
        numerator, denominator = probe['r_frame_rate'].split('/')
        self.fps, self.width, self.height = float(numerator) / float(denominator), probe['width'], probe['height']
        self.frame_count = int(probe['nb_frames'])
        self.span, self.span_offset, self.checks_run = span, 0, []
        if span:
            timeline_frames, span_frames = self.edit_list.get('duration_frames'), span[1] - span[0] + 1
            if abs(self.frame_count - span_frames) <= 1:
                self.edit_list, self.span_offset = edit_list_for_span(self.edit_list, span[0], span[1], self.fps), span[0]
            elif timeline_frames is None or abs(self.frame_count - timeline_frames) > 1:
                raise SystemExit(f'qc: {cut_path.name} has {self.frame_count} frames: neither the span ({span_frames}) nor the timeline ({timeline_frames})')
        self.look = look = json.load(open(EDITS / 'looks' / self.edit_list['look'] / 'look.json'))
        band_centre = round(self.height * (1 - look['subtitles']['resolveTemplate']['centreY']))
        self.band = (band_centre - CAPTION_BAND_HALF_HEIGHT_PX, band_centre + CAPTION_BAND_HALF_HEIGHT_PX)
        self.rows, self.measurements, self.notes = [], {}, []

    def time(self, frame):
        return frame / self.fps

    def add(self, fault_class, verdict, frame, last_frame, number, what, evidence_kind):
        self.rows.append({'class': fault_class, 'verdict': verdict, 'frame': int(frame), 'last_frame': int(last_frame),
                          'time_s': round(self.time(frame), 2), 'number': number, 'what': what, 'evidence_kind': evidence_kind})

    # ---------- measuring passes ----------

    def read_vision(self):
        binary = self.out / 'qc_vision'
        if not binary.exists() or binary.stat().st_mtime < VISION_SOURCE.stat().st_mtime:
            run(['swiftc', '-O', '-suppress-warnings', '-o', str(binary), str(VISION_SOURCE)])
        frames_file = self.out / 'vision.ndjson'
        if not frames_file.exists() or frames_file.stat().st_mtime < max(self.path.stat().st_mtime, binary.stat().st_mtime):
            with open(frames_file, 'w') as sink:
                subprocess.run([str(binary), str(self.path), str(self.band[0]), str(self.band[1]), str(FULL_FRAME_TEXT_EVERY_N_FRAMES)],
                               check=True, stdout=sink, stderr=subprocess.DEVNULL)
        self.vision = [json.loads(line) for line in open(frames_file)]
        caption_lines = []
        for frame in self.vision:
            if not frame.get('band_same_as_previous'):
                caption_lines = frame.get('band_lines', [])
            frame['caption_lines'] = caption_lines

    def read_small_frames(self):
        width, height = 135, 240
        raw = run(['ffmpeg', '-v', 'error', '-i', str(self.path), '-vf', f'scale={width}:{height}:flags=area',
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']).stdout
        self.small = np.frombuffer(raw, np.uint8).reshape(-1, height, width, 3)

    def find_picture_cuts(self):
        rows_per_pixel = self.small.shape[1] / self.height
        outside_caption_band = np.r_[0:int(self.band[0] * rows_per_pixel), int(self.band[1] * rows_per_pixel) + 1:self.small.shape[1]]
        frames = self.small[:, outside_caption_band].astype(np.float32)
        difference = np.abs(np.diff(frames, axis=0)).mean(axis=3)
        bands = np.stack([part.mean(axis=(1, 2)) for part in np.array_split(difference, 8, axis=1)], axis=1)
        whole = difference.mean(axis=(1, 2))
        self.pixel_cuts = []
        for i in range(len(difference)):
            neighbours = np.median(bands[max(0, i - 3):min(len(bands), i + 4)], axis=0)
            if (bands[i].max() > CUT_BAND_DIFFERENCE and (bands[i] - neighbours).max() > CUT_BAND_ABOVE_NEIGHBOURS) or whole[i] > CUT_WHOLE_FRAME_DIFFERENCE:
                self.pixel_cuts.append(i + 1)
        # The cuts on him are the edit list's: each camera clip is a shot, and each shot's first frame after 0 a cut.
        # The pixel cuts only cross-check the list (cross_check_cuts); encoder noise made them fire mid-shot.
        clips = sorted(self.camera_clips(), key=lambda c: c['record'])
        self.shots = [(c['record'], min(c['record'] + self.clip_frames(c), len(self.small))) for c in clips]
        self.cuts = [first for first, _ in self.shots if first > 0]
        self.shot_of_frame = np.full(len(self.small), -1)
        for index, (first, end) in enumerate(self.shots):
            self.shot_of_frame[first:end] = index
        self.continuing_cuts = {after['record'] for before, after in zip(clips, clips[1:])
                                if before['file'] == after['file'] and before.get('framing') == after.get('framing')
                                and before['source_out'] == after['source_in'] and before['record'] + self.clip_frames(before) == after['record']}

    def clip_frames(self, clip):
        """A clip's length on the timeline: a held or slowed clip (speed under 100) keeps its listed length."""
        return round(clip['source_out'] - clip['source_in'])

    def read_audio(self):
        self.cut_audio = decode_audio_mono(self.path)
        self.lav = decode_audio_mono(self.edit_list['sound']['lav'])
        self.frame_level = np.array([level_at(self.cut_audio, self.time(f), self.time(f + 1)) for f in range(self.frame_count)])

    def measure_audio_pieces(self):
        """Where each edit-list sound piece really sits on the cut, measured from the samples against the lav."""
        lav_file = str(Path(self.edit_list['sound']['lav']).resolve())
        self.pieces = []
        for piece in sorted(self.edit_list['audio'], key=lambda p: p['record_s']):
            if str(Path(piece['file']).resolve()) != lav_file:
                continue
            length = piece['source_out_s'] - piece['source_in_s']
            start, end = piece['record_s'] + 0.05, piece['record_s'] + length - 0.05
            segment = self.cut_audio[int(start * AUDIO_RATE):int(end * AUDIO_RATE)]
            search = 0.3
            reference_start = piece['source_in_s'] + 0.05 - search
            reference = self.lav[int(reference_start * AUDIO_RATE):int((piece['source_out_s'] - 0.05 + search) * AUDIO_RATE)]
            lag, match = best_lag(reference, segment)
            offset = reference_start + lag / AUDIO_RATE - start
            gain = np.median([level_at(self.cut_audio, t, t + 0.03) - level_at(self.lav, t + offset, t + offset + 0.03)
                              for t in np.arange(start, end - 0.03, 0.03) if level_at(self.cut_audio, t, t + 0.03) > SPEECH_DBFS + 5] or [0.0])
            self.pieces.append({'record_start_s': piece['record_s'], 'record_end_s': piece['record_s'] + length,
                                'source_in_s': piece['source_in_s'], 'offset_s': offset, 'match': round(match, 3), 'gain_db': float(gain)})
        self.measurements['sound_pieces'] = self.pieces

    def microphone_offset(self, camera_file, around_camera_s):
        """A camera file's clock against the lav's, by matching its own microphone to the lav: lav time = camera time + offset.
        Measured once per file, in a minute around around_camera_s, and cached in camera-offsets.json."""
        cache = self.out / 'camera-offsets.json'
        offsets = json.load(open(cache)) if cache.exists() else {}
        if camera_file not in offsets:
            rate = 8000
            lav_low = decode_audio_mono(self.edit_list['sound']['lav'], rate)
            window_start_s = max(0, around_camera_s - 30)
            raw = run(['ffmpeg', '-v', 'error', '-ss', str(window_start_s), '-t', '60', '-i', camera_file, '-map', '0:a:0',
                       '-af', 'pan=mono|c0=c0', '-ar', str(rate), '-f', 'f32le', '-']).stdout
            lag, match = best_lag(lav_low, np.frombuffer(raw, np.float32))
            offsets[camera_file] = {'lav_minus_camera_s': lag / rate - window_start_s, 'match': round(match, 3)}
            json.dump(offsets, open(cache, 'w'), indent=1)
        return offsets[camera_file]

    def lav_minus_picture_offsets(self):
        """Per camera file on the cut: lav time minus the time of the picture it shows, and where that came from.
        A camera with `picture_offset_s` in the edit list (front-camera time = camera time + offset, set picture against
        picture at ingest) takes it plus the front camera's own microphone offset: that microphone hears the room, so its
        sound and picture agree. A camera without one takes its own microphone, which is late by the radio lag when it is a
        wireless feed, as the Pocket's is."""
        picture_offsets = {camera['file']: camera['picture_offset_s'] for camera in self.edit_list.get('cameras', {}).values()
                           if 'picture_offset_s' in camera}
        front_files = [name for name, offset in picture_offsets.items() if offset == 0]
        if picture_offsets and len(front_files) != 1:
            raise SystemExit(f'qc: picture_offset_s is front-camera time minus the camera\'s own, so exactly one camera, the front, '
                             f'has 0; the edit list has {len(front_files)}: {picture_offsets}')
        offsets = {}
        for clip in self.camera_clips():
            name = clip['file']
            if name in offsets:
                continue
            clip_s = clip['source_in'] / self.source_fps(name)
            if name in picture_offsets:
                front = self.microphone_offset(front_files[0], clip_s + picture_offsets[name])
                offsets[name] = {'lav_minus_picture_s': picture_offsets[name] + front['lav_minus_camera_s'], 'timed_by_own_microphone': False,
                                 'from': f'picture_offset_s {picture_offsets[name]} s, plus the front camera microphone (match {front["match"]})'}
            else:
                microphone = self.microphone_offset(name, clip_s)
                offsets[name] = {'lav_minus_picture_s': microphone['lav_minus_camera_s'], 'timed_by_own_microphone': True,
                                 'from': f'{MICROPHONE_OFFSET_WARNING} (match {microphone["match"]})'}
                self.notes.append(f'Lip sync on {Path(name).name}: {MICROPHONE_OFFSET_WARNING}. Give its camera a picture_offset_s '
                                  'in the edit list, from inventory.md.')
        self.measurements['camera_offsets'] = offsets
        return offsets

    _source_fps = {}

    def source_fps(self, path):
        if path not in self._source_fps:
            rates = run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', path]).stdout.decode().split()
            numerator, denominator = min(rates, key=lambda r: abs(eval(r) - self.fps)).split('/')
            self._source_fps[path] = float(numerator) / float(denominator)
        return self._source_fps[path]

    def camera_clips(self):
        """Picture clips whose file has its own sound: the cameras (screen recordings and backgrounds have none)."""
        if not hasattr(self, '_camera_clips') and 'cameras' in self.edit_list:
            camera_files = {camera['file'] for camera in self.edit_list['cameras'].values()}
            self._camera_clips = [clip for clip in picture_clips(self.edit_list) if clip['file'] in camera_files]
        if not hasattr(self, '_camera_clips'):
            has_sound = {}
            for clip in picture_clips(self.edit_list):
                if clip['file'] not in has_sound:
                    has_sound[clip['file']] = bool(run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries',
                                                        'stream=index', '-of', 'csv=p=0', clip['file']]).stdout.strip())
            self._camera_clips = [clip for clip in picture_clips(self.edit_list) if has_sound[clip['file']]]
        return self._camera_clips

    # ---------- the classes ----------

    def face(self, frame):
        face = self.vision[frame].get('face')
        return face if face and face.get('left_eye_openness', -1) > 0 and face.get('right_eye_openness', -1) > 0 else None

    def heard_words(self):
        """The words heard in the cut's own sound, on the cut's clock, from --heard-words; None when not given."""
        if not self.heard_words_file:
            self.measurements['heard_words'] = 'not measured: no --heard-words file (word_times.py TIMELINE --media CUT writes one)'
            return None
        words = []
        for word in json.load(open(self.heard_words_file))['words']:
            start, text = word['start'], word.get('text', word.get('word', ''))
            if not any(ch.isalnum() for ch in text):
                continue  # Resolve marks silences and ums "(...)"
            words.append((start, text))
            if '%' in text:
                words.append((start, 'percent'))  # Resolve writes "63%" for the two words the captions show as "63 percent"
        return words

    def pixel_face_cuts(self):
        """Pixel cuts where his face jumps, appears or goes: the cross-check on the list's cuts."""
        cuts = []
        for cut in self.pixel_cuts:
            before, after = self.face(cut - 1), self.face(cut)
            if bool(before) != bool(after):
                cuts.append(cut)
            elif before and after:
                width = self.width
                centre_move = abs((before['box'][0] + before['box'][2]) - (after['box'][0] + after['box'][2])) / 2 / width
                size_change = abs((before['box'][2] - before['box'][0]) - (after['box'][2] - after['box'][0])) / max(1, before['box'][2] - before['box'][0])
                if centre_move > FACE_JUMP_FRACTION or size_change > FACE_JUMP_FRACTION:
                    cuts.append(cut)
        self.measurements['pixel_face_cuts'] = cuts
        return cuts

    def unlisted_face_cuts(self):
        """Pixel face cuts the list does not explain: not within 2 frames of a cut on him or of a listed graphic coming or
        going, and his face still moved 2 frames later (a hand across his face moves the face box for a frame or two)."""
        graphic_edges = [edge for row in self.edit_list.get('panels', []) if row.get('track', 3) >= 3
                         for edge in (row['record'], row['record'] + round(row['source_out'] - row['source_in']))]
        graphic_edges += [edge for row in self.edit_list.get('titles', []) for edge in (row['record'], row['record'] + row['frames'])]
        unlisted = []
        for cut in self.pixel_face_cuts():
            if any(abs(cut - listed) <= 2 for listed in self.cuts + graphic_edges):
                continue
            before, later = self.face(cut - 1), self.face(min(cut + 2, len(self.vision) - 1))
            if before and later and face_moved(before, later, self.width) is False:
                continue
            unlisted.append(cut)
        return unlisted

    def cross_check_cuts(self):
        """Where the pixels and the edit list disagree about a cut on him: a 'look' row each, never a fault."""
        for cut in self.unlisted_face_cuts():
            self.add('edit list against the picture', 'look', cut, cut, 'a pixel cut on his face with no listed cut within 2 frames',
                     'the picture changes here but the edit list has no cut: an unlisted change, or encoder noise', ('strip', cut))
        for cut in self.cuts:
            if cut not in self.continuing_cuts and not any(abs(cut - seen) <= 2 for seen in self.pixel_cuts):
                self.add('edit list against the picture', 'look', cut, cut, 'a listed cut with no pixel cut within 2 frames',
                         'the edit list cuts here but the picture does not change: is the render the list?', ('strip', cut))

    def eyes_at_cuts(self):
        openness = np.array([np.mean([f['left_eye_openness'], f['right_eye_openness']]) if f else np.nan
                             for f in map(self.face, range(len(self.vision)))])
        shot_normal = [np.nanmedian(openness[a:b]) if np.any(~np.isnan(openness[a:b])) else np.nan for a, b in self.shots]
        unlisted = self.unlisted_face_cuts()
        for cut in sorted(set(self.cuts) | set(unlisted)):
            verdict = 'look' if cut in unlisted else 'fault'
            worst = None
            for frame in range(cut - FRAMES_EACH_SIDE_OF_A_CUT, cut + FRAMES_EACH_SIDE_OF_A_CUT + 1):
                if 0 <= frame < len(openness) and not np.isnan(openness[frame]) and self.shot_of_frame[frame] >= 0:
                    relative = openness[frame] / shot_normal[self.shot_of_frame[frame]]
                    if worst is None or relative < worst[0]:
                        worst = (relative, frame)
            if worst and worst[0] < EYES_CLOSED_FRACTION_OF_SHOT_NORMAL:
                self.add('eyes shut at a cut', verdict, worst[1], worst[1], f'eye openness {worst[0]:.2f} of the shot\'s normal',
                         f'cut at frame {cut}; frame {worst[1]} has his eyes {100 - worst[0] * 100:.0f}% closed', ('strip', cut))

    def flashes_and_black(self):
        for clip in picture_clips(self.edit_list):
            frames = round((clip['source_out'] - clip['source_in']) / (clip.get('speed_percent', 100) / 100 if clip.get('speed_percent', 100) >= 100 else 1))
            if clip.get('track', 2) >= 2 and frames < 3:
                self.add('flash', 'fault', clip['record'], clip['record'] + frames - 1, f'{frames} frame clip', f'{Path(clip["file"]).name} is on screen for under 3 frames', ('strip', clip['record']))
        luma = self.small.mean(axis=(1, 2, 3))
        black = np.where(luma < 8)[0]
        for frame in black:
            if 2 < frame < len(luma) - 3:
                self.add('black frame', 'fault', frame, frame, f'mean level {luma[frame]:.1f}', 'a black frame inside the video', ('frame', frame))

    def picture_against_sound(self):
        offsets = self.lav_minus_picture_offsets()
        clips = sorted(self.camera_clips(), key=lambda c: c.get('track', 2))

        def picture_lav_time_and_file(frame):
            for clip in reversed(clips):
                length = clip['source_out'] - clip['source_in']
                speed = clip.get('speed_percent', 100) / 100
                if clip['record'] <= frame < clip['record'] + round(length / speed if speed >= 1 else length):
                    source_frame = clip['source_in'] + (frame - clip['record']) * speed
                    return source_frame / self.source_fps(clip['file']) + offsets[clip['file']]['lav_minus_picture_s'], clip['file']
            return None, None

        def sound_lav_time(time):
            covering = [p for p in self.pieces if p['record_start_s'] <= time < p['record_end_s']]
            return time + covering[0]['offset_s'] if len(covering) == 1 else None

        bad = []
        for frame in range(self.frame_count):
            middle = self.time(frame + 0.5)
            (picture, camera_file), sound = picture_lav_time_and_file(frame), sound_lav_time(middle)
            if picture is None or sound is None or self.frame_level[frame] < SPEECH_DBFS or not any(self.face(f) for f in range(max(0, frame - 3), min(self.frame_count, frame + 4))):
                continue
            if abs(picture + 0.5 / self.fps - sound) > OUT_OF_SYNC_SECONDS:
                bad.append((frame, picture + 0.5 / self.fps - sound, camera_file))
        runs = []
        for frame, difference, camera_file in bad:
            if runs and frame - runs[-1][1] <= 2:
                runs[-1][1] = frame; runs[-1][2].append(difference); runs[-1][3].add(camera_file)
            else:
                runs.append([frame, frame, [difference], {camera_file}])
        for first, last, differences, camera_files in runs:
            frames = last - first + 1
            verdict = 'fault' if frames >= OUT_OF_SYNC_FAULT_FRAMES else 'look'
            frozen = any(c.get('speed_percent', 100) < 100 and c['record'] <= first < c['record'] + c['source_out'] - c['source_in'] for c in clips)
            what = ('picture frozen while he speaks' if frozen else
                    f'his mouth is from {np.median(differences):+.2f} s against the sound he is heard saying')
            if any(offsets[name]['timed_by_own_microphone'] for name in camera_files):
                what += f' ({MICROPHONE_OFFSET_WARNING})'
            self.add('lips out of sync or frozen under speech', verdict, first, last, f'{frames} frames, {np.median(differences):+.2f} s', what, ('strip', first))

    def sound_joins(self):
        pieces = self.pieces
        for index, piece in enumerate(pieces):
            offset, gain = piece['offset_s'], piece['gain_db']
            for edge in ('in', 'out'):
                listed = piece['record_start_s'] if edge == 'in' else piece['record_end_s']
                neighbour = pieces[index - 1] if edge == 'in' and index > 0 else pieces[index + 1] if edge == 'out' and index + 1 < len(pieces) else None
                if neighbour and abs((neighbour['record_end_s'] + neighbour['offset_s'] if edge == 'in' else neighbour['record_start_s'] + neighbour['offset_s'])
                                     - (listed + offset)) < CONTIGUOUS_SOURCE_SECONDS:
                    continue  # the source runs on unbroken across this edge
                if edge == 'in' and listed < 0.5 or edge == 'out' and listed > len(self.cut_audio) / AUDIO_RATE - 0.5:
                    continue
                # 1. A step the edit made: the steepest 20 ms change near the edge, against the lav's change at the same moment.
                best = (0.0, listed)
                for t in np.arange(listed - 0.06, listed + 0.06, 0.0025):
                    change = (level_at(self.cut_audio, t, t + 0.01) - level_at(self.cut_audio, t - 0.01, t) if edge == 'in'
                              else level_at(self.cut_audio, t - 0.01, t) - level_at(self.cut_audio, t, t + 0.01))
                    best = max(best, (change, t))
                step, at = best
                if edge == 'in':
                    cut_before, cut_after = level_at(self.cut_audio, at - 0.02, at - 0.01), level_at(self.cut_audio, at, at + 0.01)
                    lav_step = level_at(self.lav, at + offset, at + offset + 0.01) - level_at(self.lav, at + offset - 0.02, at + offset - 0.01)
                    cut_step, louder = cut_after - cut_before, cut_after
                else:
                    cut_before, cut_after = level_at(self.cut_audio, at - 0.01, at), level_at(self.cut_audio, at + 0.01, at + 0.02)
                    lav_step = level_at(self.lav, at + offset - 0.01, at + offset) - level_at(self.lav, at + offset + 0.01, at + offset + 0.02)
                    cut_step, louder = cut_before - cut_after, cut_before
                excess = cut_step - lav_step
                frame = int(at * self.fps)
                room_tone = min(level_at(self.cut_audio, t, t + 0.01) for t in np.arange(at - ROOM_TONE_SEARCH_SECONDS, at + ROOM_TONE_SEARCH_SECONDS, 0.01))
                number = f'{cut_step:.0f} dB in 20 ms at {louder:.0f} dBFS ({louder - room_tone:.0f} dB over the room tone), {excess:.0f} dB more than the lav'
                if cut_step >= HARD_JOIN_STEP_DB and (louder >= SPEECH_DBFS or louder - room_tone >= JOIN_ABOVE_ROOM_TONE_DB):
                    if excess >= HARD_JOIN_EXCESS_OVER_LAV_DB:
                        self.add('hard sound join', 'fault', frame, frame, number, f'the sound {"starts" if edge == "in" else "stops"} sharper than his voice does', ('join', at))
                        continue
                    if excess >= LISTEN_JOIN_EXCESS_OVER_LAV_DB:
                        self.add('hard sound join', 'listen', frame, frame, number, 'steeper than his voice; only an ear can say if it sounds cut', ('join', at))
                # 2. An edge inside his speech, judged on the lav through the piece's measured offset and gain.
                edge_source = listed + offset
                windows = lambda start, count: [level_at(self.lav, start + k * 0.01, start + (k + 1) * 0.01) + gain for k in range(count)]
                if min(windows(edge_source - 0.02, 4)) >= SPEECH_DBFS:
                    self.add('clipped word at a sound join', 'fault', int(listed * self.fps), int(listed * self.fps),
                             'the lav is at speech level all through the 40 ms around the edge', f'the piece {"starts" if edge == "in" else "ends"} through a word', ('join', listed))
                    continue
                # A fragment: the kept side holds the start (or end) of a word within 300 ms of the edge, and the dropped side is clear speech.
                steps = int(FRAGMENT_LONGEST_SECONDS / 0.01)
                kept = windows(edge_source - FRAGMENT_LONGEST_SECONDS, steps) if edge == 'out' else windows(edge_source, steps)
                dropped = windows(edge_source, 3) if edge == 'out' else windows(edge_source - 0.03, 3)
                if edge == 'in':
                    kept = kept[::-1]  # read the kept side away from the edge, so a word's end becomes a rise towards the edge
                rises = [k for k in range(4, steps) if kept[k - 4] < PAUSE_DBFS and kept[k] - kept[k - 4] >= WORD_ONSET_RISE_DB]
                if rises and max(dropped) >= CLEAR_SPEECH_DBFS:
                    kept_ms = (steps - rises[-1] + 4) * 10
                    point = 'out point back' if edge == 'out' else 'in point on'
                    self.add('clipped word at a sound join', 'fault', int(listed * self.fps), int(listed * self.fps),
                             f'sound for up to {kept_ms} ms from the {point} to a pause; the dropped side is speech at {max(dropped):.0f} dBFS',
                             f'the piece {"ends" if edge == "out" else "starts"} with a short sound cut from speech its source goes on with: '
                             f'a fragment of a word, or a whole short word (the evidence shows which)', ('join', listed))

    def loudness(self):
        log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(self.path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        summary = log[log.rfind('Summary:'):]
        integrated = float(summary.split('I:')[1].split('LUFS')[0])
        true_peak = float(summary.split('Peak:')[1].split('dBFS')[0])
        self.measurements['loudness'] = {'integrated_lufs': integrated, 'true_peak_dbtp': true_peak}
        if abs(integrated - LOUDNESS_TARGET_LUFS) > LOUDNESS_TOLERANCE_LU or true_peak > TRUE_PEAK_CEILING_DBTP:
            self.add('loudness', 'fault', 0, self.frame_count - 1, f'{integrated:.1f} LUFS, {true_peak:.1f} dBTP',
                     f'the file must be {LOUDNESS_TARGET_LUFS:.0f} LUFS within {LOUDNESS_TOLERANCE_LU:.0f} LU and at most {TRUE_PEAK_CEILING_DBTP:.0f} dBTP', None)

    def captions(self):
        """Pages and lit words from the burnt-in captions; faults: a word lit in silence, captions on his mouth or nose."""
        def page_text(lines):
            return ' / '.join(line['text'] for line in lines)

        pages = []
        for frame in self.vision:
            text = page_text(frame['caption_lines'])
            if pages and pages[-1]['last'] == frame['frame'] - 1 and (text == pages[-1]['text'] or (text and pages[-1]['text'] and same_page(text, pages[-1]['text']))):
                pages[-1]['last'] = frame['frame']
            else:
                pages.append({'first': frame['frame'], 'last': frame['frame'], 'text': text})
        pages = [p for p in pages if p['text']]
        self.measurements['caption_pages'] = [{'first_frame': p['first'], 'last_frame': p['last'], 'seconds': round((p['last'] - p['first'] + 1) / self.fps, 2), 'text': p['text']} for p in pages]
        for page in pages:
            if len(page['text'].replace(' / ', ' ').split()) == 1:
                self.add('caption page broken mid-phrase', 'look', page['first'], page['last'], f'one word for {(page["last"] - page["first"] + 1) / self.fps:.1f} s',
                         f'a one-word page: "{page["text"]}"', ('frame', page['first']))

        lit_runs = self.lit_runs()
        heard = self.heard_words()
        if heard is not None:
            matched = align_lit_to_heard([(self.time(r['first']), r['word']) for r in lit_runs], heard)
            for index, run_ in enumerate(lit_runs):
                if index in matched:
                    continue
                levels = self.frame_level[run_['first']:run_['last'] + 1]
                silent_share = float(np.mean(levels < SILENCE_DBFS))
                verdict = 'fault' if silent_share >= 0.5 else 'look'
                self.add('caption word with no sound', verdict, run_['first'], run_['last'],
                         f'no matching word heard within {WORD_SEARCH_SECONDS:.0f} s; {silent_share:.0%} of its lit frames silent',
                         f'"{run_["word"]}" is lit and is not heard' if verdict == 'fault' else f'"{run_["word"]}" does not match a heard word (OCR or spelling?)', ('frame', run_['first']))

        clearance = self.look['subtitles'].get('faceClearance', {})
        lip_gap = clearance.get('lowerLipToBandTopPx', 0)
        too_close = []
        for frame in self.vision:
            face = self.face(frame['frame'])
            lines = frame['caption_lines']
            if not face or 'lips' not in face or not lines:
                continue
            band_top = clearance.get('bandTopTwoLines' if len(lines) >= 2 else 'bandTopOneLine', min(line['box'][1] for line in lines))
            gap = band_top - face['lips'][3]
            if gap < lip_gap:
                too_close.append((frame['frame'], gap))
        stretches = []
        for frame, gap in too_close:
            if stretches and frame - stretches[-1][1] <= CAPTION_ON_FACE_GAP_FRAMES:
                stretches[-1][1] = frame; stretches[-1][2] = min(stretches[-1][2], gap); stretches[-1][3] += 1
            else:
                stretches.append([frame, frame, gap, 1])
        for first, last, gap, frames in stretches:
            where = 'over his lower lip' if gap < 0 else f'{gap} px under his lower lip'
            self.add('caption on his face', 'fault', first, last, f'{frames} frames ({frames / self.fps:.1f} s); band top as close as {gap} px to his lower lip, the look asks {lip_gap}',
                     f'the caption band sits {where}', ('frame', (first + last) // 2))

    def lit_runs(self):
        """Each lit word as {first, last, word, box}: the frames its pill is on, read from the burnt-in captions."""
        if hasattr(self, '_lit_runs'):
            return self._lit_runs
        lit_runs = []
        for frame in self.vision:
            lit = [(word['text'], word['box']) for line in frame['caption_lines'] for word in line.get('words', []) if word.get('pill_fraction', 0) >= LIT_WORD_PILL_FRACTION]
            key = lit[0] if lit else None
            if key and lit_runs and lit_runs[-1]['last'] == frame['frame'] - 1 and abs(lit_runs[-1]['box'][0] - key[1][0]) < 30 and abs(lit_runs[-1]['box'][1] - key[1][1]) < 30:
                lit_runs[-1]['last'] = frame['frame']
            elif key:
                lit_runs.append({'first': frame['frame'], 'last': frame['frame'], 'word': key[0], 'box': key[1]})
        self.measurements['lit_words'] = [{'first_frame': r['first'], 'last_frame': r['last'], 'word': r['word']} for r in lit_runs]
        self._lit_runs = lit_runs
        return lit_runs

    def read_onsets(self):
        """The cut's level every 5 ms and the onsets on it, each (frame, frame its pause began or None when not after a pause)."""
        hop = TRACE_HOP_SECONDS
        count = int(len(self.cut_audio) / AUDIO_RATE / hop) - 2
        trace = np.array([level_at(self.cut_audio, k * hop, k * hop + TRACE_WINDOW_SECONDS) for k in range(count)])
        dip, peak, pause = round(ONSET_DIP_SECONDS / hop), round(ONSET_PEAK_WITHIN_SECONDS / hop), round(PAUSE_BEFORE_ONSET_SECONDS / hop)
        self.onsets, last_rising = [], -1.0
        for k in range(dip, count - peak):
            floor, top = trace[k - dip:k].max(), trace[k:k + peak].max()
            if trace[k] < floor + ONSET_START_ABOVE_DIP_DB or top < floor + ONSET_RISE_DB or top < SPEECH_DBFS:
                continue
            if k * hop - last_rising > 0.06:
                pause_began = None
                if k >= pause and trace[k - pause:k].max() < PAUSE_DBFS:
                    begin = k - pause
                    while begin > 0 and trace[begin - 1] < PAUSE_DBFS:
                        begin -= 1
                    pause_began = begin * hop * self.fps
                self.onsets.append((k * hop * self.fps, pause_began))
            last_rising = k * hop
        self.measurements['onsets'] = [{'frame': round(frame, 2), 'after_pause': began is not None} for frame, began in self.onsets]

    def highlight_timing(self):
        """Each lit word's first frame against its onset on the cut's own sound, wherever the sound shows the onset.
        After a pause the onset can only be a word's start: a fault beyond 3 frames. Inside connected speech a closure inside
        a word and a gap between words look alike on the level, so a disagreement there is a 'look' row: Resolve's heard word
        and a rise on the trace agree on an onset the lit frame misses, and no rise of its own sits at the lit frame."""
        runs = self.lit_runs()
        firsts = [run_['first'] for run_ in runs]
        rises = [frame for frame, _ in self.onsets]
        tolerance = WORD_ONSET_TOLERANCE_FRAMES
        measured_after_pause = set()
        for onset, pause_began in self.onsets:
            if pause_began is None:
                continue
            following = [i for i, first in enumerate(firsts) if first > pause_began]
            if not following:
                continue
            index = following[0]
            first, word = firsts[index], runs[index]['word']
            if first - onset > NO_LIT_WORD_AFTER_PAUSE_FRAMES:
                self.add('highlight early or late', 'look', int(onset), first, f'no lit word for {first - onset:.0f} frames after the onset at {onset:.1f}',
                         f'his voice starts after a pause and the next lit word, "{word}", comes {(first - onset) / self.fps:.2f} s later: no caption there, or the pill was not read?',
                         ('onset', (self.time(first), self.time(onset))))
                continue
            measured_after_pause.add(index)
            # A breath or click before the word is a rise too: the word's onset is the rise nearest its lit frame.
            word_onset = min((r for r in rises if onset <= r <= first + tolerance), key=lambda r: abs(r - first), default=onset)
            offset = first - word_onset
            if abs(offset) > tolerance:
                self.add('highlight early or late', 'fault', min(first, int(word_onset)), max(first, int(word_onset)),
                         f'lit {abs(offset):.1f} frames {"after" if offset > 0 else "before"} the onset at frame {word_onset:.1f}',
                         f'"{word}" lights at frame {first}; his voice starts it after a pause at frame {word_onset:.1f}',
                         ('onset', (self.time(first), self.time(word_onset))))
        heard = self.heard_words()
        if heard is None:
            return
        pairs = align_lit_to_heard([(self.time(first), run_['word']) for first, run_ in zip(firsts, runs)], heard)
        owned = {}
        for index, first in enumerate(firsts):
            near = sorted((r for r in rises if abs(r - first) <= tolerance and r not in owned), key=lambda r: abs(r - first))
            if near:
                owned[near[0]] = index
        for index, first in enumerate(firsts):
            word = runs[index]['word']
            if index in owned.values() or index in measured_after_pause or index not in pairs or any(ch.isdigit() for ch in word):
                continue
            heard_frame = heard[pairs[index]][0] * self.fps
            near = [r for r in rises if abs(r - heard_frame) <= HEARD_WORD_TO_ONSET_FRAMES and r not in owned]
            if not near:
                continue
            word_onset = min(near, key=lambda r: abs(r - heard_frame))
            offset = first - word_onset
            if abs(offset) > tolerance:
                self.add('highlight early or late', 'look', min(first, int(word_onset)), max(first, int(word_onset)),
                         f'lit {abs(offset):.1f} frames {"after" if offset > 0 else "before"} a rise at frame {word_onset:.1f}, where Resolve hears "{heard[pairs[index]][1]}"',
                         f'"{word}" lights at frame {first}; read the evidence: is the rise this word\'s start, or a sound inside the word before?',
                         ('onset', (self.time(first), self.time(word_onset))))

    def caption_edges(self):
        """Every caption pill's and letter's edges, on every frame, against the look's safe line: the button column's line
        (safeArea.buttonsLeft) and its mirror on the left, below safeArea.buttonsTop; captions.py warns on the same line."""
        safe = self.look['fusion']['safeArea']
        if self.band[1] < safe['buttonsTop']:
            return
        left, right = self.width - safe['buttonsLeft'], safe['buttonsLeft']
        top, bottom = self.band
        height = bottom - top
        decoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(self.path), '-vf',
                                    f'crop={self.width}:{height}:0:{top},scale=in_range=tv:out_range=pc:in_color_matrix=bt709,format=rgb24',
                                    '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
        frame_bytes = self.width * height * 3
        over = []
        for frame in range(self.frame_count):
            raw = decoder.stdout.read(frame_bytes)
            if len(raw) < frame_bytes:
                break
            lines = self.vision[frame]['caption_lines'] if frame < len(self.vision) else []
            if not lines:
                continue
            picture = np.frombuffer(raw, np.uint8).reshape(height, self.width, 3)
            for line in lines:
                x0, y0, x1, y1 = line['box']
                quarter = (y1 - y0) // 4
                rows = picture[max(0, y0 + quarter - top):max(0, y1 - quarter - top)].astype(np.int16)
                red, green, blue = rows[..., 0], rows[..., 1], rows[..., 2]
                pill = (red > 170) & (green > 50) & (green < 120) & (blue < 80) & (red - green > 90)
                letters = (red > 215) & (green > 215) & (blue > 215)
                columns = np.flatnonzero((pill | letters).sum(axis=0) >= 2)
                inside = np.flatnonzero((columns >= x0) & (columns <= x1))
                if not len(inside):
                    continue
                low, high = inside[0], inside[-1]
                while low > 0 and columns[low] - columns[low - 1] <= CAPTION_INK_GAP_PX:
                    low -= 1
                while high + 1 < len(columns) and columns[high + 1] - columns[high] <= CAPTION_INK_GAP_PX:
                    high += 1
                ink_left, ink_right = int(columns[low]), int(columns[high])
                if ink_left < left or ink_right > right:
                    pill_columns = np.flatnonzero(pill.sum(axis=0) >= 2)
                    pill_out = bool(len(pill_columns)) and (pill_columns.min() < left or pill_columns.max() > right) and ink_left <= pill_columns.min() and pill_columns.max() <= ink_right
                    over.append((frame, ink_left, ink_right, line['text'], pill_out))
        decoder.stdout.close()
        decoder.wait()
        stretches = []
        for frame, ink_left, ink_right, line_text, pill_out in over:
            if stretches and frame - stretches[-1]['last'] <= 1 and stretches[-1]['text'] == line_text:
                stretch = stretches[-1]
                stretch.update(last=frame, left=min(stretch['left'], ink_left), right=max(stretch['right'], ink_right), pill=stretch['pill'] or pill_out)
            else:
                stretches.append({'first': frame, 'last': frame, 'left': ink_left, 'right': ink_right, 'text': line_text, 'pill': pill_out})
        for stretch in stretches:
            sides = ([f'left edge x {stretch["left"]}, {left - stretch["left"]} px past'] if stretch['left'] < left else []) + \
                    ([f'right edge x {stretch["right"]}, {stretch["right"] - right} px past'] if stretch['right'] > right else [])
            self.add('caption past the safe line', 'fault', stretch['first'], stretch['last'], f'{"; ".join(sides)} the line at x {left} to {right}',
                     f'the caption row "{stretch["text"]}" runs past the safe line ({"its pill" if stretch["pill"] else "its letters"})',
                     ('frame', (stretch['first'] + stretch['last']) // 2))

    def camera_colour(self):
        """His skin on each camera against the reference camera (roles/colour.md): the cameras must look like one camera."""
        shot_ratios = {}
        for clip in self.camera_clips():
            end = min(clip['record'] + round(clip['source_out'] - clip['source_in']), self.frame_count)
            colours = [self.face(f)['skin_rgb'] for f in range(clip['record'] + 2, end - 2) if self.face(f) and len(self.face(f).get('skin_rgb', [])) == 3]
            if colours:
                shot_ratios.setdefault(clip['file'], []).append((float(np.median([c[0] / c[1] for c in colours])), float(np.median([c[2] / c[1] for c in colours]))))
        ratios = {camera: tuple(float(v) for v in np.median(shots, axis=0)) for camera, shots in shot_ratios.items()}
        self.measurements['camera_skin'] = {Path(c).name: {'red_over_green': round(r[0], 3), 'blue_over_green': round(r[1], 3), 'shots': len(shot_ratios[c])}
                                            for c, r in ratios.items()}
        if len(ratios) < 2:
            return
        marked = [camera['file'] for camera in self.edit_list['cameras'].values() if camera.get('reference')]
        reference = marked[0] if marked else max(ratios, key=lambda c: len(shot_ratios[c]))
        clips = sorted(self.camera_clips(), key=lambda c: c['record'])
        for camera, (red_green, blue_green) in ratios.items():
            if camera == reference:
                continue
            red_step, blue_step = red_green - ratios[reference][0], blue_green - ratios[reference][1]
            if red_step <= SKIN_RED_GREEN_ABOVE_REFERENCE and abs(blue_step) <= SKIN_BLUE_GREEN_FROM_REFERENCE:
                continue
            changes = [after['record'] for before, after in zip(clips, clips[1:]) if {before['file'], after['file']} == {camera, reference}]
            self.add('camera colour mismatch', 'fault', changes[0] if changes else 0, changes[-1] if changes else 0,
                     f'skin red/green {red_step:+.3f}, blue/green {blue_step:+.3f} against {Path(reference).name}',
                     f'his skin on {Path(camera).name} is a different colour from the reference camera, seen at {len(changes)} camera changes: ' + ', '.join(map(str, changes)),
                     ('pair', changes[0]) if changes else None)

    def graphic_text(self):
        """Text outside the caption band that sits under the phone apps' top controls or is too small to read on a phone."""
        hits = {'text under the top controls': [], 'text too small at phone width': []}
        graphic_frames = set()  # small text with no graphic on screen is in the camera picture: a book spine behind him
        for row in self.edit_list.get('panels', []):
            if row.get('track', 3) >= 3:
                graphic_frames.update(range(row['record'], row['record'] + round(row['source_out'] - row['source_in'])))
        for row in self.edit_list.get('titles', []):
            graphic_frames.update(range(row['record'], row['record'] + row['frames']))
        for frame in self.vision:
            for line in frame.get('frame_lines', []):
                x0, y0, x1, y1 = line['box']
                if y0 < PLATFORM_TOP_CONTROLS_PX:
                    hits['text under the top controls'].append((frame['frame'], line['text'], y0))
                if (y1 - y0) * PHONE_WIDTH_PX / self.width < SMALLEST_READABLE_TEXT_AT_PHONE_WIDTH_PX and len(line['text']) >= 4 \
                        and (frame['frame'] in graphic_frames or not graphic_frames):
                    hits['text too small at phone width'].append((frame['frame'], line['text'], (y1 - y0) * PHONE_WIDTH_PX / self.width))
        for kind, found in hits.items():
            stretches = []
            for frame, text, number in found:
                if stretches and frame - stretches[-1]['last'] <= FULL_FRAME_TEXT_EVERY_N_FRAMES:
                    stretches[-1]['last'] = frame; stretches[-1]['texts'].setdefault(text, number)
                else:
                    stretches.append({'first': frame, 'last': frame, 'texts': {text: number}})
            for stretch in stretches:
                texts = '; '.join(f'"{t}"' for t in list(stretch['texts'])[:6])
                number = (f'highest text top at y {min(stretch["texts"].values())}' if kind == 'text under the top controls'
                          else f'smallest line {min(stretch["texts"].values()):.1f} px tall at {PHONE_WIDTH_PX} px wide')
                self.add('graphic clipped or unreadable', 'look' if kind == 'text too small at phone width' else 'fault',
                         stretch['first'], stretch['last'], number, f'{kind}: {texts}', ('frame', stretch['first']))

    # ---------- evidence and report ----------

    def keep_rows_in_span(self):
        """With --range on a whole render, only the rows that touch the span; on a span's render, every row."""
        if self.span and not self.span_offset:
            self.rows = [row for row in self.rows if row['last_frame'] >= self.span[0] and row['frame'] <= self.span[1]]

    def evidence(self):
        folder = self.out / 'evidence'
        folder.mkdir(exist_ok=True)
        for number, row in enumerate(self.rows, 1):
            kind = row.pop('evidence_kind')
            if kind is None:
                continue
            path = folder / f'{number:03d}-{row["class"].replace(" ", "-")}-{row["frame"] + self.span_offset}.jpg'
            what, where = kind
            if what in ('strip', 'pair'):
                first = max(0, where - (3 if what == 'strip' else 1))
                count = 7 if what == 'strip' else 2
                filters = f"select='between(n\\,{first}\\,{first + count - 1})',scale={270 if what == 'strip' else 540}:-1,tile={count}x1:padding=4:color=white"
            elif what == 'frame':
                filters = f"select='eq(n\\,{where})',scale=540:-1"
            elif what == 'onset':
                lit_time, onset_time = where
                start = max(0, min(lit_time, onset_time) - 0.3)
                seconds = max(lit_time, onset_time) + 0.3 - start
                marks = ','.join(f'drawbox=x={int((t - start) / seconds * 800)}:y=0:w=3:h=360:color={colour}@0.8:t=fill'
                                 for t, colour in ((onset_time, 'red'), (lit_time, 'yellow')))
                run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-t', f'{seconds:.3f}', '-i', str(self.path), '-filter_complex',
                     "[0:a]pan=mono|c0=c0,asplit[a][b];[a]showspectrumpic=s=800x240:legend=0:scale=log:stop=8000[s];"
                     f"[b]showwavespic=s=800x120:colors=white:scale=log[w];[s][w]vstack,{marks}", '-frames:v', '1', str(path)])
                row['evidence'] = str(path.relative_to(self.out))
                continue
            else:
                start = max(0, where - 0.3)
                run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-t', '0.6', '-i', str(self.path), '-filter_complex',
                     "[0:a]pan=mono|c0=c0,asplit[a][b];[a]showspectrumpic=s=600x240:legend=0:scale=log:stop=12000[s];"
                     "[b]showwavespic=s=600x120:colors=white:scale=log[w];[s][w]vstack,drawbox=x=299:y=0:w=2:h=360:color=red@0.6:t=fill",
                     '-frames:v', '1', str(path)])
                row['evidence'] = str(path.relative_to(self.out))
                continue
            run(['ffmpeg', '-v', 'error', '-y', '-i', str(self.path), '-vf', filters, '-fps_mode', 'passthrough', '-frames:v', '1', '-q:v', '3', str(path)])
            row['evidence'] = str(path.relative_to(self.out))

    def write(self):
        for row in self.rows:
            row['frame'] += self.span_offset; row['last_frame'] += self.span_offset
            row['time_s'] = round(self.time(row['frame']), 2)
        self.rows.sort(key=lambda r: (r['frame'], r['class']))
        faults = [r for r in self.rows if r['verdict'] == 'fault']
        counts = {}
        for row in self.rows:
            counts.setdefault(row['class'], {}).setdefault(row['verdict'], 0)
            counts[row['class']][row['verdict']] += 1
        report = {'cut': str(self.path), 'frames': self.frame_count, 'fps': self.fps, 'faults': len(faults), 'counts': counts,
                  'checks': self.checks_run, 'span': self.span, 'rows': self.rows, 'picture_cuts': getattr(self, 'cuts', None),
                  'pixel_cuts': getattr(self, 'pixel_cuts', None), 'notes': self.notes, 'measurements': self.measurements}
        json.dump(report, open(self.out / 'report.json', 'w'), indent=1)
        lines = [f'<!-- Written by pipeline/b/qc.py. -->', f'# QC of {self.path.name}', '',
                 f'{len(faults)} faults. ' + (f'Loudness {self.measurements["loudness"]["integrated_lufs"]} LUFS, true peak {self.measurements["loudness"]["true_peak_dbtp"]} dBTP. ' if 'loudness' in self.measurements else '')
                 + (f'{len(self.cuts)} cuts on him in the edit list, {len(self.pixel_cuts)} picture changes in the pixels. ' if hasattr(self, 'cuts') else '')
                 + f'Checks run: {", ".join(self.checks_run)}.' + (f' Timeline frames {self.span[0]} to {self.span[1]} only.' if self.span else '')
                 + ' Rows marked look or listen are for a model or an ear to judge; they do not fail the gate.', '',
                 *[f'- {note}' for note in self.notes], *([''] if self.notes else []),
                 '| Class | Verdict | Frame | Time | Number | What | Evidence |', '| --- | --- | --- | --- | --- | --- | --- |']
        for row in self.rows:
            span = f'{row["frame"]}' if row['last_frame'] == row['frame'] else f'{row["frame"]} to {row["last_frame"]}'
            lines.append(f'| {row["class"]} | {row["verdict"]} | {span} | {row["time_s"]:.2f} s | {row["number"]} | {row["what"]} | `{row.get("evidence", "")}` |')
        lines += ['', '## Caption pages, for reading (page breaks are judged by reading, not measured)', '']
        lines += [f'- {p["first_frame"]} to {p["last_frame"]} ({p["seconds"]} s): {p["text"]}' for p in self.measurements.get('caption_pages', [])]
        (self.out / 'report.md').write_text('\n'.join(lines) + '\n')
        return len(faults)


def face_moved(before, after, width):
    """Whether his face box moved or changed size by more than FACE_JUMP_FRACTION between two frames."""
    centre_move = abs((before['box'][0] + before['box'][2]) - (after['box'][0] + after['box'][2])) / 2 / width
    size_change = abs((before['box'][2] - before['box'][0]) - (after['box'][2] - after['box'][0])) / max(1, before['box'][2] - before['box'][0])
    return centre_move > FACE_JUMP_FRACTION or size_change > FACE_JUMP_FRACTION


def same_page(a, b):
    """Two OCR readings of one caption page: most of their words agree."""
    words_a, words_b = set(a.lower().replace(' / ', ' ').split()), set(b.lower().replace(' / ', ' ').split())
    return len(words_a & words_b) >= 0.6 * max(len(words_a), len(words_b))


def similar_words(shown, spoken):
    """A lit word against a spoken one, allowing for OCR slips and spelling (numbers are compared by digits only)."""
    import difflib
    shown_key = ''.join(ch for ch in shown.lower() if ch.isalnum())
    spoken_key = ''.join(ch for ch in spoken.lower() if ch.isalnum())
    if not shown_key or not spoken_key:
        return True
    if any(ch.isdigit() for ch in shown_key):
        return True  # "$600" is said "six hundred bucks": a model reads numbers, not this check
    return difflib.SequenceMatcher(None, shown_key, spoken_key).ratio() >= 0.6


def align_lit_to_heard(lit, heard):
    """{lit index: heard index} for lit words that pair, in order, with a heard word: the most pairs, then the closest in time."""
    rows, columns = len(lit), len(heard)
    pair_score = lambda i, j: (1000 - abs(lit[i][0] - heard[j][0]) * 100
                               if abs(lit[i][0] - heard[j][0]) <= WORD_SEARCH_SECONDS and similar_words(lit[i][1], heard[j][1]) else None)
    best = np.zeros((rows + 1, columns + 1))
    for i in range(rows - 1, -1, -1):
        for j in range(columns - 1, -1, -1):
            score = pair_score(i, j)
            best[i, j] = max(best[i + 1, j], best[i, j + 1], best[i + 1, j + 1] + score if score is not None else -1)
    matched, i, j = {}, 0, 0
    while i < rows and j < columns:
        score = pair_score(i, j)
        if score is not None and best[i, j] == best[i + 1, j + 1] + score:
            matched[i] = j; i += 1; j += 1
        elif best[i, j] == best[i + 1, j]:
            i += 1
        else:
            j += 1
    return matched


def overlap_rows(box, other):
    return min(box[3], other[3]) - max(box[1], other[1]) if min(box[2], other[2]) > max(box[0], other[0]) else 0


# Each check: the measuring passes it needs, then its own passes. --only runs the named checks and their passes.
MEASURING = ('read_vision', 'read_small_frames', 'find_picture_cuts', 'read_audio', 'measure_audio_pieces', 'read_onsets')
CHECKS = {
    'eyes': (('read_vision', 'read_small_frames', 'find_picture_cuts'), ('eyes_at_cuts', 'cross_check_cuts')),
    'flashes': (('read_vision', 'read_small_frames', 'find_picture_cuts'), ('flashes_and_black',)),
    'sync': (('read_vision', 'read_audio', 'measure_audio_pieces'), ('picture_against_sound',)),
    'joins': (('read_audio', 'measure_audio_pieces'), ('sound_joins',)),
    'loudness': ((), ('loudness',)),
    'captions': (('read_vision', 'read_audio'), ('captions',)),
    'highlights': (('read_vision', 'read_audio', 'read_onsets'), ('highlight_timing',)),
    'caption-edges': (('read_vision',), ('caption_edges',)),
    'colour': (('read_vision',), ('camera_colour',)),
    'text': (('read_vision',), ('graphic_text',)),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('cut', type=Path, help='the rendered file; relative to --video-folder when that is given')
    parser.add_argument('--video-folder', type=Path, help='the video folder (default: the folder above the cut\'s versions/)')
    parser.add_argument('--edit-list', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--heard-words', type=Path, help='words heard in the cut\'s own sound, {"words": [{"start", "end", "text"}]} in cut seconds, as word_times.py TIMELINE --media CUT prints')
    parser.add_argument('--range', dest='span', type=int, nargs=2, metavar=('FIRST', 'LAST'), help='timeline frames, inclusive: the span CUT renders, or the span of a whole render to report')
    parser.add_argument('--only', nargs='+', choices=sorted(CHECKS), help='run only these checks')
    args = parser.parse_args()
    cut_path = ((args.video_folder / args.cut) if args.video_folder and not args.cut.is_absolute() and not args.cut.exists() else args.cut).resolve()
    video_folder = args.video_folder.resolve() if args.video_folder else cut_path.parent.parent
    edit_list = args.edit_list or video_folder / 'edit-list.json'
    out = args.out or video_folder / 'build' / 'qc' / cut_path.stem
    out.mkdir(parents=True, exist_ok=True)
    cut = Cut(cut_path, edit_list, out, args.heard_words, args.span)
    checks = args.only or list(CHECKS)
    if cut.span_offset:
        checks = [check for check in checks if check != 'loudness']  # a span's loudness is not the delivery's
    cut.checks_run = checks
    needed = {step for check in checks for step in CHECKS[check][0]}
    steps = [name for name in MEASURING if name in needed] + [name for check in checks for name in CHECKS[check][1]]
    for name in steps:
        print(f'qc: {name}', file=sys.stderr, flush=True)
        getattr(cut, name)()
    cut.keep_rows_in_span()
    cut.evidence()
    faults = cut.write()
    print(f'{faults} faults; report: {out / "report.md"}')
    sys.exit(1 if faults else 0)


if __name__ == '__main__':
    main()

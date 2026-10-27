#!/usr/bin/env python3
"""Written by AI on 2026-10-25 by GPT-6.1 Sol.
Execute AUDIO_LIST.json OUT.wav [--report OUT.json]; no editorial decisions.
List requires lav_file (relative to JSON), duration_s, room_tone_s [in,out],
room_tone_crossfade_ms, room_tone_end_fade_ms, audio []. All source times are
lav seconds. Pieces require source_in_s, source_out_s, record_s, fade_ms;
optional pre_roll_s extends source/record starts; overlaps sum in list order.
Optional patches require source_in_s, source_out_s, fade_ms: gain_db changes
level; replacement_source_in_s/out_s crossfade an equal-length borrowed range;
otherwise room tone replaces the range. Legacy inserts are additional pieces.
processing (default true) switches cleanup/mastering; false is raw 24-bit PCM.
Float intermediates: OUT.edit.wav, OUT.clean.wav. Default report: OUT.json.
"""
import argparse
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

CLEANUP = 'highpass=f=80,afftdn=nr=10:nf=-50,acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=1'

def required(data, key, location):
    if key not in data:
        raise ValueError(f'Missing {location}.{key}')
    return data[key]

def number(data, key, location):
    value = required(data, key, location)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
        raise ValueError(f'{location}.{key} must be a finite number')
    return value

def ffmpeg(arguments, **kwargs):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', *arguments],
                          capture_output=True, check=True, **kwargs)


def loudness(path):
    result = ffmpeg(['-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], text=True)
    summary = result.stderr[result.stderr.rfind('Summary:'):]
    return dict(zip(('integrated_lufs', 'true_peak_dbtp'),
                    (float(re.search(pattern, summary)[1]) for pattern in
                     (r'I:\s+(-?[\d.]+|[-+]?inf) LUFS', r'Peak:\s+(-?[\d.]+|[-+]?inf) dBFS'))))


def rms(samples):
    return float(20 * np.log10(np.sqrt(np.mean(samples.astype(np.float64) ** 2)) + 1e-12))


def read(source, start_s, end_s):
    start, end = round(start_s * source.getframerate()), round(end_s * source.getframerate())
    if not 0 <= start < end <= source.getnframes():
        raise ValueError(f'Lav range {start_s}..{end_s} is outside its file or empty')
    source.setpos(start)
    raw, width = source.readframes(end - start), source.getsampwidth()
    if width == 3:
        octets = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        values = octets[:, 0].astype(np.int32) | (octets[:, 1].astype(np.int32) << 8) | (octets[:, 2].astype(np.int32) << 16)
        values = np.where(values >= 1 << 23, values - (1 << 24), values)
    elif width in (2, 4):
        values = np.frombuffer(raw, f'<i{width}')
    else:
        raise ValueError('Lav must be 16-, 24- or 32-bit integer PCM')
    return (values.astype(np.float32) / (1 << (8 * width - 1))).reshape(-1, source.getnchannels())


def cosine(length):
    return (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, length))).astype(np.float32)


def build(args):
    data = json.loads(args.audio_list.read_text())
    pieces = required(data, 'audio', 'list')
    duration = number(data, 'duration_s', 'list')
    room = required(data, 'room_tone_s', 'list')
    if not isinstance(room, list) or len(room) != 2 or not all(isinstance(v, (int, float)) and np.isfinite(v) for v in room):
        raise ValueError('list.room_tone_s must be [from_s, to_s] in lav seconds')
    loop_ms = number(data, 'room_tone_crossfade_ms', 'list')
    end_ms = number(data, 'room_tone_end_fade_ms', 'list')
    processing = data.get('processing', True)
    if type(processing) is not bool or duration <= 0 or loop_ms < 0 or end_ms < 0:
        raise ValueError('processing must be boolean; duration positive; room-tone fades nonnegative')
    edges, repairs = [], []
    with wave.open(str(args.audio_list.parent / required(data, 'lav_file', 'list')), 'rb') as source:
        rate, channels = source.getframerate(), source.getnchannels()
        total = round(duration * rate)
        mix, coverage = np.zeros((total, channels), np.float32), np.zeros(total, np.float32)
        for index, piece in enumerate(pieces):
            location = f'audio[{index}]'
            source_in, source_out, record, fade_ms = (number(piece, key, location) for key in
                                                    ('source_in_s', 'source_out_s', 'record_s', 'fade_ms'))
            lead = number(piece, 'pre_roll_s', location) if 'pre_roll_s' in piece else 0
            if fade_ms < 0 or lead < 0:
                raise ValueError(f'{location}: fade_ms and pre_roll_s must be nonnegative')
            source_in, record = source_in - lead, record - lead
            samples = read(source, source_in, source_out)
            length, start = len(samples), round(record * rate)
            if start < 0 or start + length > total:
                raise ValueError(f'{location}.record_s places audio outside duration_s')
            fade = min(round(fade_ms * rate / 1000), length // 2)
            shape, keep = np.ones(length, np.float32), np.ones(length, np.float32)
            if fade:
                shape[:fade], shape[-fade:] = cosine(fade), cosine(fade)[::-1]
            for patch_index, patch in enumerate(piece.get('patches', [])):
                where = f'{location}.patches[{patch_index}]'
                pin, pout, pms = (number(patch, key, where) for key in ('source_in_s', 'source_out_s', 'fade_ms'))
                if pout <= pin or pms < 0:
                    raise ValueError(f'{where}: source_out_s must exceed source_in_s; fade_ms must be nonnegative')
                first, last, fade = round((pin - source_in) * rate), round((pout - source_in) * rate), round(pms * rate / 1000)
                gate = np.zeros(length, np.float32)
                if last > 0 and first < length:
                    gate[max(first, 0):min(last, length)] = 1
                    if first > 0:
                        edge = max(first - fade, 0)
                        gate[edge:first] = np.linspace(0, 1, first - edge, dtype=np.float32)
                    if last < length:
                        edge = min(last + fade, length)
                        gate[last:edge] = np.linspace(1, 0, edge - last, dtype=np.float32)
                gain = 10 ** (number(patch, 'gain_db', where) / 20) if 'gain_db' in patch else 0
                if 'replacement_source_in_s' in patch or 'replacement_source_out_s' in patch:
                    rin, rout = (number(patch, key, where) for key in ('replacement_source_in_s', 'replacement_source_out_s'))
                    replacement = read(source, rin, rout)
                    if first < 0 or last > length or len(replacement) != last - first or 'gain_db' in patch:
                        raise ValueError(f'{where}: replacement must fit the piece, match target samples and omit gain_db')
                    fade = min(fade, len(replacement) // 2)
                    blend = np.ones(len(replacement), np.float32)
                    if fade:
                        blend[:fade], blend[-fade:] = cosine(fade), cosine(fade)[::-1]
                    samples[first:last] = samples[first:last] * (1 - blend[:, None]) + replacement * blend[:, None]
                    repairs.append(dict(piece=index, **patch))
                    continue
                keep *= 1 - gate * (1 - gain)
                repairs.append(dict(piece=index, **patch))
            envelope = shape * keep
            mix[start:start + length] += samples * envelope[:, None]
            coverage[start:start + length] += envelope
            context = min(round(0.03 * rate), length)
            edges.append(dict(piece=index, source_in_sample=round(source_in * rate), source_out_sample=round(source_out * rate),
                              record_in_sample=start, record_out_sample=start + length,
                              in_rms_dbfs=rms(samples[:context]), out_rms_dbfs=rms(samples[-context:])))
        tone = read(source, *room)
        crossfade = min(round(loop_ms * rate / 1000), len(tone) // 3)
        bed, position, ramp = np.zeros_like(mix), 0, cosine(crossfade)
        while position < total:
            tile = tone.copy()
            if crossfade:
                if position:
                    tile[:crossfade] *= ramp[:, None]
                tile[-crossfade:] *= ramp[::-1, None]
            length = min(len(tile), total - position)
            bed[position:position + length] += tile[:length]
            position += len(tone) - crossfade
        ending = min(round(end_ms * rate / 1000), total)
        if ending:
            bed[-ending:] *= np.linspace(1, 0, ending, dtype=np.float32)[:, None]
        mix += bed * np.clip(1 - coverage, 0, 1)[:, None]
    raw, clean = args.output.with_suffix('.edit.wav'), args.output.with_suffix('.clean.wav')
    ffmpeg(['-v', 'error', '-f', 'f32le', '-ar', str(rate), '-ac', str(channels), '-i', 'pipe:0', '-c:a', 'pcm_f32le', str(raw)], input=mix.astype('<f4').tobytes())
    measurements = []
    if processing:
        ffmpeg(['-v', 'error', '-i', str(raw), '-af', CLEANUP, '-c:a', 'pcm_f32le', str(clean)])
        gain, ceiling = -14 - loudness(clean)['integrated_lufs'], -1.15
        for attempt in range(8):
            filters = (f'volume={gain:.4f}dB,aresample={rate * 4},alimiter=limit={10 ** (ceiling / 20):.9f}:attack=5:release=50:level=false:latency=true,'
                       f'aresample={rate},apad=whole_len={total},atrim=end_sample={total}')
            ffmpeg(['-v', 'error', '-i', str(clean), '-af', filters, '-c:a', 'pcm_s24le', str(args.output)])
            levels = loudness(args.output)
            measurements.append(dict(attempt=attempt + 1, gain_db=gain, limiter_ceiling_db=ceiling, **levels))
            if levels['true_peak_dbtp'] <= -1 and abs(levels['integrated_lufs'] + 14) <= 0.2:
                break
            if levels['true_peak_dbtp'] > -1:
                ceiling -= levels['true_peak_dbtp'] + 1.1
            gain += -14 - levels['integrated_lufs']
        else:
            raise ValueError(f'Could not meet loudness/true-peak target: {levels}')
    else:
        ffmpeg(['-v', 'error', '-i', str(raw), '-c:a', 'pcm_s24le', str(args.output)])
    with wave.open(str(args.output), 'rb') as final:
        if final.getnframes() != total:
            raise ValueError(f'Output has {final.getnframes()} samples; duration_s requires {total}')
    report = dict(sample_rate=rate, channels=channels, samples=total, audio=pieces, cut_levels=edges, patches=repairs,
                  room_tone_s=room, room_tone_rms_dbfs=rms(tone), processing=processing, cleanup=CLEANUP if processing else None,
                  measurements=measurements, final=loudness(args.output))
    (args.report or args.output.with_suffix('.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(output=str(args.output), samples=total, **report['final'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('audio_list', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path)
    try:
        build(parser.parse_args())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'{error}\n')

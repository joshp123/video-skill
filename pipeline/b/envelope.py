#!/usr/bin/env python3
"""Measure per-step lav RMS, quiet runs and the nearest quiet measurement.

Written by AI on 2026-10-25 by GPT-6.1 Sol. Times are WAV seconds;
RMS uses the louder channel, as pipeline/cut/build_cutlist.py's Lav does.
Requires numpy and Python 3.12+ for PCM WAVE_FORMAT_EXTENSIBLE files.
"""
import argparse
import json
import math
import os
import sys
import wave

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lav')
    parser.add_argument('--from', dest='start', type=float, required=True)
    parser.add_argument('--to', dest='end', type=float, required=True)
    parser.add_argument('--step', type=float, default=0.005)
    parser.add_argument('--quiet-dbfs', type=float, default=-46)
    parser.add_argument('--near', type=float)
    args = parser.parse_args()
    numbers = [args.start, args.end, args.step, args.quiet_dbfs]
    if args.near is not None:
        numbers.append(args.near)
    if not all(math.isfinite(value) for value in numbers):
        parser.error('arguments must be finite numbers')
    with wave.open(args.lav, 'rb') as audio:
        rate, channels, width = audio.getframerate(), audio.getnchannels(), audio.getsampwidth()
        duration = audio.getnframes() / rate
        if not 0 <= args.start < args.end <= duration or args.step * rate < 1:
            parser.error(f'require 0 <= from < to <= {duration}, and step >= {1 / rate}')
        if width not in (2, 3):
            parser.error(f'unsupported PCM sample width: {width}; expected 16 or 24 bits')
        first_sample, last_sample = round(args.start * rate), round(args.end * rate)
        levels = []
        for index in range(math.ceil((args.end - args.start) / args.step)):
            start = max(first_sample, round((args.start + index * args.step) * rate))
            end = min(last_sample, round((args.start + (index + 1) * args.step) * rate))
            if end <= start:
                continue
            audio.setpos(start)
            raw = audio.readframes(end - start)
            if width == 3:
                data = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
                data = data[:, 0] | data[:, 1] << 8 | data[:, 2] << 16
                data = np.where(data >= 1 << 23, data - (1 << 24), data) / (1 << 23)
            else:
                data = np.frombuffer(raw, '<i2').astype(np.float64) / (1 << 15)
            data = data.reshape(-1, channels)
            dbfs = float(20 * np.log10(np.max(np.sqrt(np.mean(data * data, axis=0))) + 1e-12))
            levels.append({'start': start / rate, 'end': end / rate, 'dbfs': dbfs})
    quiet_runs, quiet_levels = [], []
    for level in levels:
        if level['dbfs'] >= args.quiet_dbfs:
            continue
        quiet_levels.append(level)
        if quiet_runs and quiet_runs[-1]['end'] == level['start']:
            quiet_runs[-1]['end'] = level['end']
        else:
            quiet_runs.append({'start': level['start'], 'end': level['end']})
    for run in quiet_runs:
        run['length'] = run['end'] - run['start']
    result = {'levels': levels, 'quiet_runs': quiet_runs}
    if args.near is not None:
        closest = min(quiet_levels, key=lambda level: abs(level['start'] - args.near), default=None)
        result['nearest_quiet'] = None if closest is None else {
            'time': closest['start'], 'dbfs': closest['dbfs'],
            'distance': abs(closest['start'] - args.near)}
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    os._exit(0)

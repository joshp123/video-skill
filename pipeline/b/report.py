"""Deterministic physics checks on a finished render, plus seam WAV extraction for listening.

report.py PLAN.json --timeline NAME --render FILE

Measures only what a model cannot eyeball from frames:
1. Reads the live timeline back (`readback.describe`) into `build/report/NAME/description.json`.
2. Delivery loudness and true peak on FILE via ffmpeg `ebur128` (target -14 +/- 1 LUFS, peak <= -1.0 dBTP).
3. Black frames inside the video via ffmpeg `blackdetect` (catches dropped drives / gaps).
4. Audio seam clips (`joins seams`) around every dialogue join so a native-audio model (Gemini) or Josh can listen directly.

Everything visual (framing, eyes, captions, pills, colour match, graphics) is checked directly on frames via Resolve's MCP
(`get_thumbnails`, `get_image`, and a 1-frame still render for captions). Exit 0 always.
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import readback
import session

HERE = Path(__file__).resolve().parent
JOINS = HERE.parent / 'joins' / 'joins'
LOUDNESS_TARGET, LOUDNESS_TOL, PEAK_CEILING = -14.0, 1.0, -1.0


def probe_video(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height,r_frame_rate,nb_frames,duration',
         '-of', 'json', str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    s = (json.loads(out).get('streams') or [{}])[0]
    num, den = s.get('r_frame_rate', '25/1').split('/')
    return {
        'width': int(s.get('width', 0)),
        'height': int(s.get('height', 0)),
        'fps': round(float(num) / float(den), 3),
        'frames': int(s.get('nb_frames', 0) or 0),
        'duration_s': round(float(s.get('duration', 0) or 0), 3),
    }


def measure_loudness(path):
    """Integrated LUFS and true peak (dBTP) on the delivered file via ffmpeg ebur128."""
    log = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
        capture_output=True, text=True, check=True,
    ).stderr
    summary = log.split('Summary:')[-1]
    lufs_m = re.search(r'I:\s*([-\d.]+)\s*LUFS', summary)
    peak_m = re.search(r'Peak:\s*([-\d.]+)\s*dBFS', summary)
    lufs = float(lufs_m.group(1)) if lufs_m else None
    peak = float(peak_m.group(1)) if peak_m else None
    ok = (
        lufs is not None and abs(lufs - LOUDNESS_TARGET) <= LOUDNESS_TOL
        and peak is not None and peak <= PEAK_CEILING
    )
    return {'integrated_lufs': lufs, 'true_peak_dbtp': peak, 'ok': ok}


def detect_black_frames(path, duration_s):
    """Black stretches inside the video (ignoring the first and last 0.15 s)."""
    log = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path),
         '-vf', 'blackdetect=d=0.04:pic_th=0.98:pix_th=0.05', '-an', '-f', 'null', '-'],
        capture_output=True, text=True, check=True,
    ).stderr
    hits = []
    for m in re.finditer(r'black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)', log):
        start, end, dur = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if end > 0.15 and start < max(0.0, duration_s - 0.15):
            hits.append({'start_s': round(start, 3), 'end_s': round(end, 3), 'duration_s': round(dur, 3)})
    return hits


def report(plan_path, name, render_file):
    began, folder = time.monotonic(), plan_path.parent
    work = folder / 'build' / 'report' / name.replace('/', '_')
    work.mkdir(parents=True, exist_ok=True)

    resolve, project = session.connect(json.loads(plan_path.read_text(encoding='utf-8'))['resolve_project'])
    described = readback.describe(resolve, project, name, plan_path)
    desc_path = work / 'description.json'
    desc_path.write_text(json.dumps(described, indent=1, ensure_ascii=False), encoding='utf-8')

    video = probe_video(render_file)
    loudness = measure_loudness(render_file)
    black_frames = detect_black_frames(render_file, video['duration_s'])

    joins_at = [round(row['record_s'], 4) for row in described.get('audio', [])[1:]]
    join_times_path = work / 'join-times.json'
    join_times_path.write_text(json.dumps(joins_at), encoding='utf-8')

    seams = {'clips': [], 'all_seams': None}
    if joins_at:
        seams_dir = work / 'seams'
        seams_json = work / 'seams.json'
        done = subprocess.run(
            [str(JOINS), 'seams', '--audio', str(render_file), '--joins', str(join_times_path),
             '--out', str(seams_dir), '--json-out', str(seams_json)],
            capture_output=True, text=True,
        )
        if done.returncode == 0 and seams_json.exists():
            seams = json.loads(seams_json.read_text(encoding='utf-8'))
        else:
            seams = {'error': done.stderr[-400:]}

    return {
        'render': str(render_file),
        'video': video,
        'loudness': loudness,
        'black_frames': black_frames,
        'join_count': len(joins_at),
        'seams': seams,
        'files': {'description': str(desc_path)},
        'seconds': round(time.monotonic() - began, 1),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--timeline', required=True)
    parser.add_argument('--render', type=Path, required=True)
    args = parser.parse_args()
    session.main(lambda: report(args.plan.resolve(), args.timeline, args.render.resolve()))

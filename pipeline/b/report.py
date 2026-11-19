"""The checks on a finished cut, as one list for the model to judge: nothing here stops anything.

Written by AI on 2026-11-19 by Claude Opus 5.5, from cut.py (Claude Opus 5.5, 17 Nov), when the checks stopped being a
gate in front of every render.

report.py PLAN.json --timeline NAME --render FILE

1. The timeline read back in the edit list's shape (readback.py describe(), with the plan's cameras, sound and look):
   build/report/NAME/description.json. The timeline is the cut; no plan or edit list is trusted for what is on it.
2. The timeline's sound as mixed, before loudness normalisation (render.py --preset sound, about 3 s), and the join check
   (`joins/joins check`) on every join of the dialogue track, with the lav and the calibration span assemble.py used
   for the first cut, so both checks share one threshold.
3. qc.py on FILE (a render of the whole timeline): eyes at cuts, flashes, lip sync, loudness, captions read back from
   the picture, lit words against his voice, caption edges, colour against the reference camera, text size at phone
   width, his whole head.
Prints {joins, rows, files}: every flagged or borderline join with its score, and every fault and look row of qc.py
with its frame. Exit 0 whatever it finds.
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import readback
import render
import session

HERE = Path(__file__).resolve().parent
JOINS = HERE.parent / 'joins' / 'joins'
QC_CHECKS = ['eyes', 'flashes', 'sync', 'loudness', 'captions', 'highlights', 'caption-edges', 'colour', 'text', 'head']


def numpy_python():
    """The pipeline devenv's Python (numpy), which qc.py needs."""
    found = subprocess.run(['devenv', 'shell', '--', 'python3', '-c', 'import sys, numpy; print(sys.executable)'],
                           cwd=HERE.parent, capture_output=True, text=True)
    return found.stdout.strip().splitlines()[-1]


def report(plan_path, name, render_file):
    began, folder = time.monotonic(), plan_path.parent
    work = folder / 'build' / 'report' / name.replace('/', '_')
    work.mkdir(parents=True, exist_ok=True)
    resolve, project = session.connect(json.loads(plan_path.read_text(encoding='utf-8'))['resolve_project'])
    described = readback.describe(resolve, project, name, plan_path)
    (work / 'description.json').write_text(json.dumps(described, indent=1, ensure_ascii=False), encoding='utf-8')
    sound_file = work / 'sound-as-mixed.wav'
    if sound_file.exists():
        subprocess.run(['trash', str(sound_file)], check=True)
    render.render(project, session.timeline_named(project, name), sound_file, 'sound', loudness='off')
    joins_at = [round(row['record_s'], 4) for row in described['audio'][1:]]
    (work / 'join-times.json').write_text(json.dumps(joins_at))
    assembled = json.loads((folder / 'build' / 'assemble.json').read_text(encoding='utf-8'))
    out = {'joins': [], 'rows': [], 'files': {'description': str(work / 'description.json')}}
    done = subprocess.run([str(JOINS), 'check', '--audio', str(sound_file), '--joins', str(work / 'join-times.json'), '--lav',
                           described['sound']['lav'], '--span', assembled['calibration_span'], '--out', str(work / 'joins.json')],
                          capture_output=True, text=True)
    if done.returncode:
        out['joins'].append(f'the join check failed: {done.stderr[-400:]}')
    else:
        checked = json.loads((work / 'joins.json').read_text())
        out['joins'] = [f"join at {j['at']} s {'borderline' if j.get('borderline') else 'flagged'}: score {j['score']} "
                        f"over {checked['threshold']}, likely {j.get('likely')} (a hint)" for j in checked['joins'] if j['flag'] or j.get('borderline')]
        out['files']['joins'] = str(work / 'joins.json')
    qc_out = work / 'qc'
    subprocess.run([numpy_python(), 'qc.py', str(render_file), '--edit-list', str(work / 'description.json'), '--out', str(qc_out),
                    '--only', *QC_CHECKS], capture_output=True, text=True, cwd=HERE, env={**os.environ, 'PYTHONUTF8': '1'})
    if (qc_out / 'report.md').exists():
        out['rows'] = sorted({' '.join(line.split()) for line in (qc_out / 'report.md').read_text(encoding='utf-8').splitlines()
                              if '| fault |' in line or '| look |' in line})
        out['files']['qc'] = str(qc_out / 'report.md')
    else:
        out['rows'].append(f'qc.py wrote no report: see {qc_out}')
    out['seconds'] = round(time.monotonic() - began, 1)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--timeline', required=True)
    parser.add_argument('--render', type=Path, required=True)
    args = parser.parse_args()
    session.main(lambda: report(args.plan.resolve(), args.timeline, args.render.resolve()))

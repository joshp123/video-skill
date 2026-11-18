"""From the plan to a checked render in one call: assemble, place, finish, render, join check, gate.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild.

cut.py PLAN.json --timeline NAME --loudness PRESET [--preset phone] [--render-anyway]

Runs, in order, stopping at the first that fails: assemble.py (the edit list beside the plan, replaced), preflight.py
(the gate's eye, lip and sync checks on the planned picture, about 30 s; a fault stops the pass here, before the
3 to 6 minutes of place, render and gate, unless --render-anyway), place.py
(timeline NAME), finish.py ("NAME finish"), render.py (versions-check/NAME.mp4 in the plan's folder, captions burnt in),
render.py --preset sound --loudness off (the finish timeline's sound as mixed, before loudness normalisation, about
3 s), `joins check` on that sound at every join, and qc.py (every class but joins, which the join check replaces).
Prints one summary: each stage's seconds; every join's score on the lav and in the mix, side by side (the mix check is
given the lav and the lav check's calibration_span, so both use one threshold); and what needs the model:
edges with no pause, joins flagged or borderline, speech level steps over 6 dB, a caption the template would page,
doubtful word times, place or finish differences, the gate's fault rows (report and evidence under build/qc/NAME/). Every stage's own output is in
build/cut/NAME/. Exit 0 only when no stage failed and no row needs the model.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOINS = HERE.parent / "joins" / "joins"
LEVEL_STEP_WORTH_A_LOOK_DB = 6  # joins/README.md: ordinary speech steps 3 to 5 dB between sentences
QC_CHECKS = ["eyes", "flashes", "sync", "loudness", "captions", "highlights", "caption-edges", "colour", "text"]


def numpy_python():
    """The pipeline devenv's Python (numpy), which qc.py needs."""
    found = subprocess.run(["devenv", "shell", "--", "python3", "-c", "import sys, numpy; print(sys.executable)"],
                           cwd=HERE.parent, capture_output=True, text=True)
    return found.stdout.strip().splitlines()[-1]


def stage(name, command, out, summary):
    began = time.monotonic()
    done = subprocess.run(command, capture_output=True, text=True, cwd=HERE, env={**os.environ, "PYTHONUTF8": "1"})
    out.write_text(done.stdout + ("\n--- stderr ---\n" + done.stderr if done.stderr.strip() else ""))
    summary["stages"].append({"stage": name, "exit": done.returncode, "seconds": round(time.monotonic() - began, 1), "output": str(out)})
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--loudness", required=True,
                        help="the loudness render preset's name (loudness.py writes one): without it the render is about 10 dB quiet, "
                             "the gate fails on loudness and the pass is wasted (run 6, build 18)")
    parser.add_argument("--preset", default="phone")
    parser.add_argument("--render-anyway", action="store_true", help="place and render even when preflight finds a fault")
    args = parser.parse_args()
    plan = args.plan.resolve()
    folder = plan.parent
    edit_list = folder / "edit-list.json"
    work = folder / "build" / "cut" / args.timeline
    work.mkdir(parents=True, exist_ok=True)
    render_file = folder / "versions-check" / f"{args.timeline}.mp4"
    py = ["/usr/bin/python3", "-B"]
    summary, needs = {"timeline": args.timeline, "stages": []}, []
    began = time.monotonic()

    def finish(status):
        summary["seconds"] = round(time.monotonic() - began, 1)
        summary["needs_the_model"] = needs
        print(json.dumps(summary, indent=1, ensure_ascii=False))
        sys.exit(status)

    done = stage("assemble", py + ["assemble.py", str(plan), "--out", str(edit_list), "--force"], work / "assemble.json", summary)
    report = json.loads(done.stdout or "{}")
    if "error" in report or "edit_list" not in report:  # exit 1 with a report is "needs the model", read below
        needs.append(report.get("error", done.stderr[-500:]))
        finish(1)
    needs += [f"no pause at piece {e['piece']} {e['side']}: " + (f"cut moved from {e['at']} to {e['moved_to']} s ({e['why_moved']})"
              if "moved_to" in e else f"cut at {e['at']} s; nearest pauses {e.get('nearest_pauses')}") for e in report["edges"]]
    lav_check = report["joins"]
    needs += [f"join {j['join']} flagged on the lav (score {j['score']} over {lav_check['threshold']}; likely {j['likely']}, a hint)"
              for j in lav_check["joins"] if j["flag"]]
    needs += [f"join {j['join']} borderline on the lav, treat it as flagged (score {j['score']}, threshold {lav_check['threshold']})"
              for j in lav_check["joins"] if j.get("borderline") and not j["flag"]]
    needs += [f"join {j['join']}: speech level steps {j['level_step_db']} dB (a gain match is your call)"
              for j in lav_check["joins"] if abs(j.get("level_step_db", 0)) > LEVEL_STEP_WORTH_A_LOOK_DB]
    needs += [f"caption words: {c}" for c in report["captions"] if "is in no caption" in c]
    needs += [f"doubtful word time: piece {d.get('piece')} {d}" for d in report.get("doubtful_words", [])]
    needs += [f"piece {u['piece']} also holds {u['words']!r} (at {u['at_s']} s on the lav): {u['why']}" for u in report.get("unchosen_words", [])]
    needs += [f"caption row too wide: {w}" for w in report.get("caption_width", [])]
    needs += report.get("graphic_spans", [])
    if report.get("caption_refusals"):
        needs += [f"caption: {c}" for c in report["caption_refusals"]]
        finish(1)
    done = stage("preflight", py + ["preflight.py", str(edit_list), "--out", str(work / "preflight")], work / "preflight.json", summary)
    checked_faces = json.loads(done.stdout or "{}")
    if "error" in checked_faces:
        needs.append(f"preflight: {checked_faces['error']}")
        finish(1)
    by_cut = {c["cut"]: c for c in checked_faces["cuts"]}
    for f in checked_faces["faults"]:
        options = by_cut.get(f.get("cut"), {}).get("options")
        needs.append(f"before placing, {f['class']} at frame {f['frame']}: {f['what']}" + (f"; clean instead: {options}" if options else ""))
    needs += [f"borderline before placing, {f['class']} at frame {f['frame']}: {f['what']}" for f in checked_faces["borderline"]]
    needs += [f"look before placing: a {j['camera']}-to-{j['camera']} cut at frame {j['cut']} changes scale by {j['scale_change']}x "
              "(a small change reads as a jump cut)" for j in checked_faces["jump_candidates"]]
    needs += [f"look before placing: {m['what']}" for m in checked_faces.get("panel_moves", [])]
    summary["preflight"] = {"faults": len(checked_faces["faults"]), "borderline": len(checked_faces["borderline"]),
                            "jump_candidates": checked_faces["jump_candidates"], "output": str(work / "preflight.json")}
    if checked_faces["faults"] and not args.render_anyway:
        needs.append("stopped before place and render: fix the faults above in the plan, or run again with --render-anyway")
        finish(1)
    for name, command in (("place", py + ["place.py", str(edit_list), "--timeline", args.timeline]),
                          ("finish", py + ["finish.py", str(edit_list), "--timeline", args.timeline])):
        done = stage(name, command, work / f"{name}.json", summary)
        result = json.loads(done.stdout or "{}")
        if done.returncode:
            needs.append(f"{name}: {result.get('error') or result.get('differences', [])[:5]}")
            finish(1)
    render = py + ["render.py", str(edit_list), "--timeline", f"{args.timeline} finish", "--out", str(render_file), "--preset", args.preset]
    if args.loudness:
        render += ["--loudness", args.loudness]
    if render_file.exists():
        subprocess.run(["trash", str(render_file)], check=True)
    done = stage("render", render, work / "render.json", summary)
    if done.returncode:
        needs.append(f"render: {json.loads(done.stdout or '{}').get('error')}")
        finish(1)
    sound_file = work / "sound-as-mixed.wav"  # the join check scores the sound before loudness normalisation
    if sound_file.exists():
        subprocess.run(["trash", str(sound_file)], check=True)
    done = stage("sound as mixed", py + ["render.py", str(edit_list), "--timeline", f"{args.timeline} finish", "--out", str(sound_file),
                                        "--preset", "sound", "--loudness", "off"], work / "sound.json", summary)
    if done.returncode:
        needs.append(f"sound render: {json.loads(done.stdout or '{}').get('error')}")
        finish(1)
    joins_at = [round(row["record_s"], 4) for row in json.loads(edit_list.read_text())["audio"][1:]]
    (work / "join-times.json").write_text(json.dumps(joins_at))
    lav = (folder / json.loads(edit_list.read_text())["sound"]["lav"]).resolve()
    if not report.get("calibration_span"):
        needs.append("joins place reported no calibration_span, so the render check would use another threshold")
        finish(1)
    done = stage("joins check", [str(JOINS), "check", "--audio", str(sound_file), "--joins", str(work / "join-times.json"),
                                 "--lav", str(lav), "--span", report["calibration_span"], "--out", str(work / "joins-check.json")],
                 work / "joins-check.log", summary)
    if done.returncode == 0:
        checked = json.loads((work / "joins-check.json").read_text())
        summary["joins"] = {"model": checked.get("model", {}).get("sha256"), "threshold_lav": lav_check["threshold"],
                            "threshold_mixed": checked["threshold"], "calibration_span": report["calibration_span"],
                            "each": [{"join": r["join"], "at_s": r["at"], "lav": l["score"], "mixed": r["score"],
                                      "flag_lav": l["flag"], "flag_mixed": r["flag"], "level_step_db": r.get("level_step_db")}
                                     for l, r in zip(lav_check["joins"], checked["joins"])]}
        needs += [f"mixed join {r['join']} at {r['at']} s {'borderline' if r.get('borderline') else 'flagged'} "
                  f"(score {r['score']}; on the lav {l['score']})"
                  + ("" if l["flag"] else ": the lav check passes it, so the timeline's mix (fades, crossfade, room tone, "
                     "gain) changed it; listen, re-place it, or keep it with your reason")
                  for l, r in zip(lav_check["joins"], checked["joins"]) if r["flag"] or r.get("borderline")]
    else:
        needs.append("joins check failed: see its log")
    qc_out = folder / "build" / "qc" / args.timeline
    python = numpy_python()
    done = stage("gate", [python, "qc.py", str(render_file), "--edit-list", str(edit_list), "--out", str(qc_out), "--only", *QC_CHECKS],
                 work / "gate.log", summary)
    report_md = qc_out / "report.md"
    if report_md.exists():
        rows = [line for line in report_md.read_text().splitlines() if "| fault |" in line]
        audio_rows = json.loads(edit_list.read_text())["audio"]
        fps = float(json.loads(edit_list.read_text())["fps"])

        def on_lav(frame):
            """A timeline frame as seconds on the lav's clock, the clock word_starts_s takes."""
            t = frame / fps
            row = max((a for a in audio_rows if a["record_s"] <= t + 1e-6), key=lambda a: a["record_s"], default=None)
            return round(row["source_in_s"] + t - row["record_s"], 3) if row else None
        for row in sorted(set(re.sub(r"\s+", " ", row) for row in rows)):
            onset = re.search(r"onset at frame ([0-9.]+)", row)
            needs.append(row + (f" [onset on the lav's clock: {on_lav(float(onset.group(1)))} s, the value word_starts_s takes]"
                                if onset and "highlight" in row else ""))
        summary["gate_report"] = str(report_md)
    else:
        needs.append("gate failed: see its log")
    summary["render"] = str(render_file)
    finish(int(bool(needs)))


if __name__ == "__main__":
    main()

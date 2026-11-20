"""Place sound edges inside measured pauses of the lav, and extract short seam WAVs for listening.

  joins place LAV PIECES.json [--words TRANSCRIPT.json] [--crossfade 0.04] [--out placed.json]
  joins seams --audio FILE (--joins TIMES.json | --at T,T,...) --out DIR [--window 4.0]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import sound
from sound import SR

DEFAULT_KEEP = 0.15  # seconds of pause kept on each side of a cut when no pause length is requested
DEEP_DB = 4          # cut falls on a 10 ms frame within this many dB of the local room floor
SEARCH = 0.6         # search radius around the transcript's estimated word edge, seconds
STEP_WARN_DB = 6.0   # report level/room steps larger than this for a listen


def log(*a):
    print(*a, file=sys.stderr, flush=True)


class Recording:
    def __init__(self, path):
        t = time.time()
        self.path = path
        self.x = sound.read(path)
        self.db = sound.levels(self.x)
        self.floor = sound.floor_trace(self.db)
        self.pauses = sound.pauses(self.db, self.floor)
        log(f"read {path}: {len(self.x) / SR:.1f} s, {len(self.pauses)} pauses ({time.time() - t:.1f} s)")

    def near(self, t):
        before = [p for p in self.pauses if p[1] <= t]
        after = [p for p in self.pauses if p[0] >= t]
        fmt = lambda p: [round(p[0], 3), round(p[1], 3)] if p else None
        return dict(before=fmt(before[-1] if before else None), after=fmt(after[0] if after else None))


def quietest(rec, est):
    """The quietest 10 ms within 0.15 s of an estimate, and its level over the room floor."""
    a = max(0, int((est - 0.15) / sound.FRAME))
    b = min(len(rec.db), max(a + 1, int((est + 0.15) / sound.FRAME)))
    k = a + int(np.argmin(rec.db[a:b]))
    return dict(at=round((k + 0.5) * sound.FRAME, 3), level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1))


def place_edge(rec, est, side, want, margin):
    """Cut at one edge of a piece: on room tone inside the pause nearest the estimate."""
    if side == "start":
        cands = [p for p in rec.pauses if est - SEARCH <= p[1] <= est + SEARCH]
        best = min(cands, key=lambda p: abs(p[1] - est), default=None)
    else:
        cands = [p for p in rec.pauses if est - SEARCH <= p[0] <= est + SEARCH]
        best = min(cands, key=lambda p: abs(p[0] - est), default=None)
    if best is None or best[1] - best[0] < 2 * margin:
        q = quietest(rec, est)
        return dict(at=q["at"], pause=None, status="no pause next to this word",
                    level_db_over_floor=q["level_db_over_floor"], nearest_pauses=rec.near(est))
    word_edge = best[1] if side == "start" else best[0]
    sign = -1 if side == "start" else 1
    want = DEFAULT_KEEP if want is None else want
    a, b = int(round(best[0] / sound.FRAME)), int(round(best[1] / sound.FRAME))
    ts = (np.arange(a, b) + 0.5) * sound.FRAME
    ok = (rec.db[a:b] < rec.floor[a:b] + DEEP_DB) & (ts >= best[0] + margin) & (ts <= best[1] - margin)
    target = word_edge + sign * want
    at = float(ts[ok][np.argmin(np.abs(ts[ok] - target))]) if ok.any() else float(np.clip(target, best[0] + margin, best[1] - margin))
    k = min(len(rec.db) - 1, int(at / sound.FRAME))
    return dict(at=round(at, 4), status="pause", pause=[round(best[0], 3), round(best[1], 3)],
                kept=round(abs(at - word_edge), 3), on_room_tone=bool(ok.any()),
                level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1),
                word_edge=round(word_edge, 3), estimate_off_by=round(word_edge - est, 3))


def given(rec, at):
    k = min(len(rec.db) - 1, max(0, int(at / sound.FRAME)))
    return dict(at=round(at, 4), status="given", level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1))


def words_between(words, a, b):
    ws = [w["word"] for w in words if a <= (w["start"] + w["end"]) / 2 <= b]
    return " ".join(ws) if len(ws) <= 10 else " ".join(ws[:5]) + " ... " + " ".join(ws[-5:])


def measure_joins(rec, pieces, crossfade):
    """Join the pieces as Resolve will and measure deterministic level/room steps at every seam."""
    h, x = crossfade / 2, rec.x
    audio = [x[max(0, int(round((p["start"] - (h if k else 0)) * SR))): int(round((p["end"] + (h if k < len(pieces) - 1 else 0)) * SR))]
             for k, p in enumerate(pieces)]
    if len(audio) < 2:
        return dict(length=round(sum(len(a) for a in audio) / SR, 3), joins=[], needs_listen=[])
    y, times = sound.join(audio, [crossfade] * (len(pieces) - 1))
    side = lambda t, a, b: y[max(0, int((t + a) * SR)): max(0, int((t + b) * SR))]
    edge_db = lambda t, a, b: float(np.median(sound.levels(side(t, a, b)))) if len(side(t, a, b)) >= int(sound.FRAME * SR) else -120.0
    rows = []
    for k, (t, a, b) in enumerate(zip(times, pieces, pieces[1:])):
        level_step = sound.speech_level(side(t, 0.05, 2.0)) - sound.speech_level(side(t, -2.0, -0.05))
        room_step = edge_db(t, 0.02, 0.06) - edge_db(t, -0.06, -0.02)
        reasons = []
        if a["end_edge"]["status"] != "pause" and a["end_edge"]["level_db_over_floor"] > DEEP_DB:
            reasons.append("outgoing edge not on room tone")
        if b["start_edge"]["status"] != "pause" and b["start_edge"]["level_db_over_floor"] > DEEP_DB:
            reasons.append("incoming edge not on room tone")
        if abs(level_step) > STEP_WARN_DB:
            reasons.append(f"speech level step {level_step:+.1f} dB")
        if abs(room_step) > STEP_WARN_DB:
            reasons.append(f"room floor step {room_step:+.1f} dB")
        rows.append(dict(join=k + 1, at=round(t, 4), between=[a["piece"], b["piece"]],
                         level_step_db=round(float(level_step), 1), room_step_db=round(float(room_step), 1),
                         needs_listen=bool(reasons), reasons=reasons))
    return dict(length=round(len(y) / SR, 3), joins=rows, needs_listen=[r["join"] for r in rows if r["needs_listen"]])


def cmd_place(args):
    t0 = time.time()
    rec = Recording(args.lav)
    pieces = json.load(open(args.pieces))
    words = json.load(open(args.words))["words"] if args.words else None
    margin = args.crossfade / 2 + 0.01
    placed = []
    for k, p in enumerate(pieces):
        want = lambda side: None if (p.get("pause_before" if side == "start" else "pause_after")) is None else p["pause_before" if side == "start" else "pause_after"] / 2
        s = given(rec, p["start_at"]) if "start_at" in p else place_edge(rec, p["start"], "start", want("start"), margin)
        e = given(rec, p["end_at"]) if "end_at" in p else place_edge(rec, p["end"], "end", want("end"), margin)
        piece = dict(piece=k + 1, start=s["at"], end=e["at"], start_edge=s, end_edge=e)
        if words:
            piece["words"] = words_between(words, s["at"], e["at"])
            for edge, est in (("start_edge", p.get("start")), ("end_edge", p.get("end"))):
                ed = piece[edge]
                if ed["status"] == "given":
                    continue
                if ed.get("status") == "pause" and abs(ed["estimate_off_by"]) > 0.25:
                    ed["quietest_near_estimate"] = quietest(rec, est)
                    a, b = sorted((ed["word_edge"], est))
                    ed["words_between_estimate_and_pause"] = words_between(words, a, b) or "(none in the transcript: a breath or noise?)"
                if "nearest_pauses" in ed:
                    for side in ("before", "after"):
                        q = ed["nearest_pauses"][side]
                        if q:
                            a, b = sorted((est, q[1] if side == "before" else q[0]))
                            ed["nearest_pauses"][f"words_to_{side}"] = words_between(words, a, b)
        placed.append(piece)
    for a, b in zip(placed, placed[1:]):
        a["pause_after"] = round((a["end_edge"].get("kept") or 0) + (b["start_edge"].get("kept") or 0), 3)
    joins = measure_joins(rec, placed, args.crossfade)
    result = dict(lav=str(args.lav), crossfade=args.crossfade, default_keep_each_side=DEFAULT_KEEP,
                  pieces=placed, check=joins, seconds=round(time.time() - t0, 1))
    emit(result, args.out)


def cmd_seams(args):
    """Extract short mono WAV windows around each join time so a listening model or Josh can hear every seam."""
    import soundfile as sf

    t0 = time.time()
    times = [float(t) for t in args.at.split(",") if t.strip()] if args.at else json.load(open(args.joins))
    x = sound.read(args.audio)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    half = args.window / 2.0
    clips, stitched = [], []
    gap = np.zeros(int(0.5 * SR), dtype=np.float32)
    for k, t in enumerate(times):
        a = max(0, int(round((t - half) * SR)))
        b = min(len(x), int(round((t + half) * SR)))
        seg = x[a:b]
        clip_path = out_dir / f"join-{k:02d}-{t:.2f}s.wav"
        sf.write(clip_path, seg, SR)
        clips.append(dict(join=k, at_s=round(t, 4), file=str(clip_path), start_s=round(a / SR, 3), end_s=round(b / SR, 3)))
        if stitched:
            stitched.append(gap)
        stitched.append(seg)
    combined = None
    if stitched:
        combined = str(out_dir / "all-seams.wav")
        sf.write(combined, np.concatenate(stitched), SR)
    emit(dict(audio=str(args.audio), window_s=args.window, clips=clips, all_seams=combined, seconds=round(time.time() - t0, 1)), args.json_out)


def emit(result, out):
    text = json.dumps(result, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    if out:
        Path(out).write_text(text + "\n")
        log(f"wrote {out}")
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser(prog="joins", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("place", help="cut each kept piece inside a measured pause and measure level/room steps")
    p.add_argument("lav")
    p.add_argument("pieces")
    p.add_argument("--words", help="transcript JSON ({words: [{start, end, word}]}) to list words inside each piece")
    p.add_argument("--crossfade", type=float, default=0.04, help="crossfade at every join in seconds (default 0.04)")
    p.add_argument("--out", help="write JSON here instead of stdout")
    p.set_defaults(run=cmd_place)

    s = sub.add_parser("seams", help="extract short WAV windows around join times for direct listening")
    s.add_argument("--audio", required=True, help="rendered audio or video file")
    s.add_argument("--at", help="comma-separated join times in seconds")
    s.add_argument("--joins", help="JSON list of join times in seconds")
    s.add_argument("--window", type=float, default=4.0, help="seconds per seam clip (default 4.0)")
    s.add_argument("--out", required=True, help="directory for seam WAV clips")
    s.add_argument("--json-out", help="optional path to write JSON manifest")
    s.set_defaults(run=cmd_seams)

    args = ap.parse_args()
    if args.cmd == "seams" and not (args.at or args.joins):
        ap.error("seams needs --at T,T,... or --joins FILE")
    args.run(args)


if __name__ == "__main__":
    main()

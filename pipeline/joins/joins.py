# Written by AI on 2026.11.17 by model Claude Opus 5.5.
"""Place the sound edges of kept speech, and score every join. See README.md.

  joins place LAV PIECES.json      cut each piece inside a measured pause, then score every join
  joins check --lav LAV PIECES.json   score joins of exact pieces, before anything is placed in Resolve
  joins check --audio FILE --at T,T,...   score joins in a rendered sound file (the check that counts)
  joins examples / joins train     make labelled joins from a recording, and train a model on them
"""
import argparse, json, pickle, sys, time
from pathlib import Path
import numpy as np
import sound
from sound import SR

HERE = Path(__file__).parent
MODEL = HERE / "model" / "joins.pkl"
DEFAULT_KEEP = 0.15          # seconds of a pause kept on each side of a cut when no pause length is asked for
DEEP_DB = 4                  # a cut falls on a frame within this many dB of the room floor
SEARCH = 0.6                 # how far either side of the estimated word edge to look for a pause, seconds (transcript
                             # word times are up to half a second out)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------- scoring ----------
BUDGETS = ("0.05", "0.1", "0.2")    # 1% and 2% are not offered: they rest on a handful of saturated scores
BORDER = 0.03                        # a score this close to the threshold can flip with any small change in the sound
CAL_MARGIN = 60.0                    # calibrate on the stretch being edited, this many seconds either side
CAL_STEP = 30.0                      # ...rounded outward to whole steps, so trimming a piece does not move the threshold
OFF_MODEL = 0.15                     # own 20% threshold above the model's by more than this: an unfamiliar recording
CALIBRATION = Path.home() / ".cache" / "join-check" / "calibration"


def load_model():
    import hashlib
    model = pickle.load(open(MODEL, "rb"))
    model["id"] = dict(file=str(MODEL), sha256=hashlib.sha256(MODEL.read_bytes()).hexdigest()[:12], trained=model.get("trained"))
    return model


def probabilities(model, x, times):
    import features, training
    return training.predict(model, features.measure([features.window(x, t) for t in times])) if times else np.zeros((0, 1))


def score(model, x, times, thr):
    """Score each join time in x against the threshold. Returns one dict per join."""
    out = []
    side = lambda t, a, b: x[max(0, int((t + a) * SR)): max(0, int((t + b) * SR))]
    for k, (t, pk) in enumerate(zip(times, probabilities(model, x, times))):
        level_step = sound.speech_level(side(t, 0.05, 2)) - sound.speech_level(side(t, -2, -0.05))
        edge = lambda a, b: float(np.median(sound.levels(side(t, a, b))))
        room_step = edge(0.02, 0.06) - edge(-0.06, -0.02)
        faults = sorted(((float(pk[i]), kind) for i, kind in enumerate(model["kinds"]) if kind != "clean"), reverse=True)
        s = float(1 - pk[0])
        out.append(dict(join=k + 1, at=round(t, 4), score=round(s, 3), flag=s > thr, borderline=abs(s - thr) < BORDER,
                        likely=faults[0][1],
                        likely_share=round(faults[0][0] / max(s, 1e-9), 2),
                        level_step_db=round(float(level_step), 1), room_step_db=round(room_step, 1)))
    return out


def own_joins(rec, crossfade, n=200, seed=0, span=None):
    """Clean joins spliced from this recording's own pauses, cut exactly as `place` cuts (on room tone, up to 0.15 s
    of pause kept each side), dropping 1 to 8 stretches of speech between. Returns the joined windows' join times."""
    rng = np.random.default_rng(seed)
    margin, h = crossfade / 2 + 0.01, crossfade / 2
    lo, hi = span or (0, len(rec.x) / SR)
    cuts = []                                          # (out cut, in cut, pause) per usable pause
    for p in rec.pauses:
        if p[1] - p[0] < 2 * margin + 0.02 or p[0] < lo + 3 or p[1] > hi - 3:
            continue
        a, b = int(round(p[0] / sound.FRAME)), int(round(p[1] / sound.FRAME))
        ts = (np.arange(a, b) + 0.5) * sound.FRAME
        ok = (rec.db[a:b] < rec.floor[a:b] + DEEP_DB) & (ts >= p[0] + margin) & (ts <= p[1] - margin)
        if ok.any():
            t = ts[ok]
            cuts.append((t[np.argmin(np.abs(t - p[0] - DEFAULT_KEEP))], t[np.argmin(np.abs(t - p[1] + DEFAULT_KEEP))], p))
    lv = lambda a, b: float(np.median(sound.levels(rec.x[int(a * SR): int(b * SR)])))
    windows, tries = [], 0
    while len(windows) < n and tries < 20 * n and len(cuts) > 9:
        tries += 1
        i = int(rng.integers(len(cuts) - 9)); j = i + int(rng.integers(1, 9))
        c1, pa = cuts[i][0], cuts[i][2]
        c2, pb = cuts[j][1], cuts[j][2]
        # the same rule as the training labels: room tone differing by 4 dB or more is not a clean join
        if abs(lv(max(pa[0], c1 - 0.12), c1 - 0.01) - lv(c2 + 0.01, min(pb[1], c2 + 0.12))) >= 4:
            continue
        L = rec.x[int(round((c1 - 2.6) * SR)): int(round((c1 + h) * SR))]
        R = rec.x[int(round((c2 - h) * SR)): int(round((c2 + 2.6) * SR))]
        y, t = sound.join([L, R], [crossfade])
        windows.append((y, t[0]))
    return windows


def own_thresholds(model, rec, crossfade, span=None):
    """Thresholds from this recording's own clean joins: for each budget, the score that share of them exceeds."""
    t0 = time.time()
    key = f"{Path(rec.path).resolve()}|{Path(rec.path).stat().st_size}|{model['id']['sha256']}|{crossfade}|{span}"
    cache = CALIBRATION / (__import__("hashlib").sha256(key.encode()).hexdigest()[:16] + ".json")
    if cache.exists():
        return json.loads(cache.read_text())
    import features, training
    ws = own_joins(rec, crossfade, span=span)
    if len(ws) < 50:
        return None
    s = 1 - training.predict(model, features.measure([features.window(y, t) for y, t in ws]))[:, 0]
    cal = dict(source="this recording's own clean joins", recording=str(rec.path), joins=len(ws),
               thresholds={b: float(np.quantile(s, 1 - float(b))) for b in BUDGETS},
               median_score=float(np.median(s)), seconds=round(time.time() - t0, 1))
    CALIBRATION.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(cal))
    return cal


def flag_setting(model, false_alarm, rec=None, crossfade=0.04, span=None):
    """The threshold for this budget: from the recording's own pauses (within span) when it is at hand, else the model's."""
    key = f"{false_alarm:g}"
    if key not in BUDGETS:
        sys.exit(f"--false-alarm must be one of {', '.join(BUDGETS)}")
    cal = None
    if rec is not None:
        span = (max(0.0, float(span[0])), min(len(rec.x) / SR, float(span[1]))) if span else (0.0, len(rec.x) / SR)
        cal = own_thresholds(model, rec, crossfade, span=span)
        if cal is None:
            log(f"too few pauses in {span[0]:.0f}-{span[1]:.0f} s to calibrate on; using the model's own threshold")
    if cal:
        thr = cal["thresholds"][key]
        how = (f"set on {cal['joins']} clean joins spliced from this recording's own pauses, {span[0]:.0f} to {span[1]:.0f} s "
               f"of {cal['recording']}; the model's own threshold would be {model['thresholds'][key]:.3f}")
    else:
        thr, how = model["thresholds"][key], "the model's own, set on clean joins of its calibration recordings (pass --lav to fit it to this recording)"
    head = dict(model=model["id"], false_alarm_rate=false_alarm, threshold=round(thr, 3), threshold_from=how,
                calibration_span=f"{span[0]:g}-{span[1]:g}" if cal else None,
                meaning=f"flag is true when score > threshold; at most about {false_alarm:.0%} of clean joins are flagged "
                        "(on Josh's held-out joins, fewer: 2.8% at the 0.1 setting)")
    if cal and cal["thresholds"]["0.2"] - model["thresholds"]["0.2"] > OFF_MODEL:
        head["off_model"] = (f"this recording's own clean joins score well above the model's (20% threshold "
                             f"{cal['thresholds']['0.2']:.2f} against {model['thresholds']['0.2']:.2f}): it sounds unlike what the "
                             "model trained on. The flag is fitted to it; catches of room jumps may be lower. See README, Retraining.")
    return thr, head


# ---------- placing ----------
class Recording:
    def __init__(self, path):
        t = time.time()
        self.path = path
        self.x = sound.read(path)
        self.db = sound.levels(self.x)
        self.floor = sound.floor_trace(self.db)
        self.pauses = sound.pauses(self.db, self.floor)
        self.ends = np.array([p[1] for p in self.pauses])
        self.starts = np.array([p[0] for p in self.pauses])
        log(f"read {path}: {len(self.x) / SR:.1f} s, {len(self.pauses)} pauses ({time.time() - t:.1f} s)")

    def floor_at(self, t):
        return float(self.floor[min(len(self.floor) - 1, int(t / sound.FRAME))])

    def near(self, t):
        """The pauses on either side of t: the last that ends before it and the first that starts after it."""
        before = [p for p in self.pauses if p[1] <= t]
        after = [p for p in self.pauses if p[0] >= t]
        r = lambda p: [round(p[0], 3), round(p[1], 3)] if p else None
        return dict(before=r(before[-1] if before else None), after=r(after[0] if after else None))


def place_edge(rec, est, side, want, margin):
    """The cut at one edge of a piece. side 'start': est is the first word's estimated start; 'end': the last word's end.
    want: seconds of pause to keep on this side. margin: how far the cut must stay inside the pause."""
    if side == "start":
        cands = [p for p in rec.pauses if est - SEARCH <= p[1] <= est + SEARCH]
        best = min(cands, key=lambda p: abs(p[1] - est), default=None)
    else:
        cands = [p for p in rec.pauses if est - SEARCH <= p[0] <= est + SEARCH]
        best = min(cands, key=lambda p: abs(p[0] - est), default=None)
    if best is None or best[1] - best[0] < 2 * margin:
        # no pause next to this word: the quietest 10 ms near the estimate, reported as such
        q = quietest(rec, est)
        return dict(at=q["at"], pause=None, status="no pause next to this word",
                    level_db_over_floor=q["level_db_over_floor"], nearest_pauses=rec.near(est))
    word_edge = best[1] if side == "start" else best[0]
    sign = -1 if side == "start" else 1
    want = DEFAULT_KEEP if want is None else want
    # cut on room tone: a 10 ms frame within DEEP_DB of the floor, clear of the pause's ends by the margin, nearest the
    # wanted pause length; so a breath or a word's decay inside the pause is kept whole or left out, never cut through
    a, b = int(round(best[0] / sound.FRAME)), int(round(best[1] / sound.FRAME))
    ts = (np.arange(a, b) + 0.5) * sound.FRAME
    ok = (rec.db[a:b] < rec.floor[a:b] + DEEP_DB) & (ts >= best[0] + margin) & (ts <= best[1] - margin)
    target = word_edge + sign * want
    if ok.any():
        at = float(ts[ok][np.argmin(np.abs(ts[ok] - target))])
    else:                                              # no room tone in this pause: as near the wanted length as fits
        at = float(np.clip(target, best[0] + margin, best[1] - margin))
    k = min(len(rec.db) - 1, int(at / sound.FRAME))
    return dict(at=round(at, 4), status="pause", pause=[round(best[0], 3), round(best[1], 3)],
                kept=round(abs(at - word_edge), 3), on_room_tone=bool(ok.any()),
                level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1),
                word_edge=round(word_edge, 3), estimate_off_by=round(word_edge - est, 3))


def given(rec, at):
    """An exact cut the agent chose: used as given, with the level there."""
    k = int(at / sound.FRAME)
    return dict(at=round(at, 4), status="given", level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1))


def quietest(rec, est):
    """The quietest 10 ms within 0.15 s of an estimate, and its level over the room floor."""
    a, b = int((est - 0.15) / sound.FRAME), int((est + 0.15) / sound.FRAME)
    k = a + int(np.argmin(rec.db[a:b]))
    return dict(at=round((k + 0.5) * sound.FRAME, 3), level_db_over_floor=round(float(rec.db[k] - rec.floor[k]), 1))


def words_between(words, a, b):
    ws = [w["word"] for w in words if a <= (w["start"] + w["end"]) / 2 <= b]
    return " ".join(ws) if len(ws) <= 10 else " ".join(ws[:5]) + " ... " + " ".join(ws[-5:])


def cmd_place(args):
    t0 = time.time()
    rec = Recording(args.lav)
    pieces = json.load(open(args.pieces))
    words = json.load(open(args.words))["words"] if args.words else None
    margin = args.crossfade / 2 + 0.01
    placed = []
    for k, p in enumerate(pieces):
        def want(side):
            j = p.get("pause_before") if side == "start" else p.get("pause_after")
            return None if j is None else j / 2
        s = given(rec, p["start_at"]) if "start_at" in p else place_edge(rec, p["start"], "start", want("start"), margin)
        e = given(rec, p["end_at"]) if "end_at" in p else place_edge(rec, p["end"], "end", want("end"), margin)
        piece = dict(piece=k + 1, start=s["at"], end=e["at"], start_edge=s, end_edge=e)
        if words:
            piece["words"] = words_between(words, s["at"], e["at"])
            for edge, est in (("start_edge", p.get("start")), ("end_edge", p.get("end"))):
                ed = piece[edge]
                if ed["status"] == "given":            # an edge set by hand has no estimate to compare with
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
    joins = check_pieces(rec, placed, args.crossfade, args.false_alarm)
    result = dict(lav=str(args.lav), crossfade=args.crossfade, default_keep_each_side=DEFAULT_KEEP,
                  pieces=placed, check=joins, seconds=round(time.time() - t0, 1))
    emit(result, args.out)


def check_pieces(rec, pieces, crossfade, false_alarm):
    """Join the pieces as Resolve will (each crossfade centred on its cut) and score every join."""
    model = load_model()
    span = (CAL_STEP * np.floor((min(p["start"] for p in pieces) - CAL_MARGIN) / CAL_STEP),
            CAL_STEP * np.ceil((max(p["end"] for p in pieces) + CAL_MARGIN) / CAL_STEP))
    thr, head = flag_setting(model, false_alarm, rec, crossfade, span)
    h, x = crossfade / 2, rec.x
    audio = [x[max(0, int(round((p["start"] - (h if k else 0)) * SR))): int(round((p["end"] + (h if k < len(pieces) - 1 else 0)) * SR))]
             for k, p in enumerate(pieces)]
    y, times = sound.join(audio, [crossfade] * (len(pieces) - 1))
    res = score(model, y, times, thr)
    for r, a, b in zip(res, pieces, pieces[1:]):
        r["between"] = [a.get("piece"), b.get("piece")]
    return dict(**head, length=round(len(y) / SR, 3), joins=res, flagged=[r["join"] for r in res if r["flag"]])


def cmd_check(args):
    t0 = time.time()
    if args.audio:
        times = [float(t) for t in args.at.split(",")] if args.at else json.load(open(args.joins))
        model = load_model()
        span = tuple(float(v) for v in args.span.split("-")) if args.span else None
        thr, head = flag_setting(model, args.false_alarm, Recording(args.lav) if args.lav else None, args.crossfade, span)
        res = score(model, sound.read(args.audio), times, thr)
        result = dict(**head, audio=str(args.audio), joins=res, flagged=[r["join"] for r in res if r["flag"]])
    else:
        pieces = json.load(open(args.pieces))
        pieces = pieces["pieces"] if isinstance(pieces, dict) else pieces
        result = dict(lav=str(args.lav), **check_pieces(Recording(args.lav), pieces, args.crossfade, args.false_alarm))
    result["seconds"] = round(time.time() - t0, 1)
    emit(result, args.out)


def emit(result, out):
    text = json.dumps(result, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    if out:
        Path(out).write_text(text + "\n")
        log(f"wrote {out}")
    else:
        print(text)


# ---------- training ----------
def cmd_examples(args):
    import training
    if args.utterances:
        utts = [json.loads(l) for l in open(args.utterances)]
    else:
        words = json.load(open(args.words))["words"]
        ranges = [tuple(float(v) for v in r.split("-")) for r in args.range]
        src = Path(args.out).with_suffix(".16k.wav")
        if not src.exists():
            import soundfile as sf
            sf.write(src, sound.read(args.audio), SR)
        utts = training.align(src, words, ranges)
        log(f"{len(utts)} stretches aligned, {sum(len(u['words']) for u in utts)} words")
    training.examples(utts, args.clean, args.faulty, seed=args.seed, out=args.out)


def cmd_train(args):
    import training
    model = training.fit(args.examples, args.calibrate or args.examples)
    MODEL.parent.mkdir(exist_ok=True)
    out = Path(args.out or MODEL)
    pickle.dump(model, open(out, "wb"))
    log(f"wrote {out}: thresholds {model['thresholds']}")


def main():
    ap = argparse.ArgumentParser(prog="joins", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    fa = dict(type=float, default=0.1, help="share of clean joins the flag may wrongly flag: 0.05, 0.1 (default) or 0.2")
    xf = dict(type=float, default=0.04, help="crossfade at every join, seconds, centred on the cut (default 0.04, one frame at 25 fps; 0 for a butt join)")

    p = sub.add_parser("place", help="cut each kept piece inside a measured pause, then score every join",
                       description="PIECES.json: a list, in playing order, of {\"start\": first word's estimated start, "
                                   "\"end\": last word's estimated end} in seconds on the lav's clock; optional "
                                   "\"pause_before\"/\"pause_after\": seconds of pause wanted at that join (split evenly "
                                   "between its two sides). Without them each side keeps about 0.15 s of its own pause. "
                                   "\"start_at\"/\"end_at\" instead of start/end: an exact cut, used as given. Each edge is "
                                   "cut on room tone in the pause nearest the estimate (within 0.6 s); an edge with no pause "
                                   "says so and names the nearest pauses. Ends by scoring every join, as `check` does. "
                                   "Pass the reported calibration_span to `check --audio --span`. Details: README.md.")
    p.add_argument("lav"); p.add_argument("pieces")
    p.add_argument("--words", help="the transcript (JSON with a 'words' list of {start, end, word}): lists the words each piece now holds")
    p.add_argument("--crossfade", **xf); p.add_argument("--false-alarm", **fa); p.add_argument("--out", help="write JSON here instead of stdout")
    p.set_defaults(run=cmd_place)

    c = sub.add_parser("check", help="score joins: of exact pieces of the lav, or in a rendered sound file",
                       description="Scores every join (0 to 1) and flags those over a threshold fitted to the lav's own "
                                   "pauses. Two forms: --lav LAV PIECES.json (the pieces joined as Resolve will join them), "
                                   "or --audio RENDER --at T,... --lav LAV --span SPAN (the rendered sound; always pass "
                                   "--lav and the calibration_span `place` reported, or the flag falls back to the model's "
                                   "own threshold). Output names the model and how the threshold was set. Details: README.md.")
    c.add_argument("pieces", nargs="?", help="with --lav: pieces as `place` writes them (its output file works), or a list of {start, end}")
    c.add_argument("--lav", help="the lav: the pieces' source, and with --audio the recording whose own pauses set the flag")
    c.add_argument("--audio", help="a rendered file (any format ffmpeg reads)")
    c.add_argument("--span", help="with --audio and --lav: the calibration_span that `place` reported (START-END seconds of the lav), so both checks use one threshold; default: all of the lav")
    c.add_argument("--at", help="with --audio: join times in the file, seconds, comma-separated")
    c.add_argument("--joins", help="with --audio: a JSON list of join times instead of --at")
    c.add_argument("--crossfade", **xf); c.add_argument("--false-alarm", **fa); c.add_argument("--out")
    c.set_defaults(run=cmd_check)

    e = sub.add_parser("examples", help="make and measure labelled joins from a recording (for training)")
    e.add_argument("--audio"); e.add_argument("--words", help="transcript JSON with a 'words' list")
    e.add_argument("--range", action="append", default=[], help="START-END seconds of the recording to use; repeat")
    e.add_argument("--utterances", help="instead: a JSONL of aligned utterances {id, path (16 kHz), dur, words [{w,s,e}]}")
    e.add_argument("--clean", type=int, default=1500); e.add_argument("--faulty", type=int, default=600, help="joins of each fault kind")
    e.add_argument("--seed", type=int, default=0); e.add_argument("--out", required=True, help=".npz to write")
    e.set_defaults(run=cmd_examples)

    t = sub.add_parser("train", help="train the classifier on example files and set its thresholds")
    t.add_argument("examples", nargs="+")
    t.add_argument("--calibrate", nargs="+", help="example files of the target voice and mic; thresholds come from their clean joins")
    t.add_argument("--out", help=f"default {MODEL}")
    t.set_defaults(run=cmd_train)

    args = ap.parse_args()
    if args.cmd == "check" and not (args.audio or (args.lav and args.pieces)):
        ap.error("check needs --audio FILE --at T,... [--lav LAV] or --lav LAV PIECES.json")
    args.run(args)


if __name__ == "__main__":
    main()

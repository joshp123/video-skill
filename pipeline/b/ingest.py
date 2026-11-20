"""From a recording session's camera files (or cards) to a session the story and cut stages can stand on, in one call.

Written by AI on 2026-11-18 by Claude Opus 5.5, for the rebuild, in place of pipeline/ingest/ (October's clone, sync
and transcribe scripts) and the hand steps tools/cameras.md described.

  ingest.py start --session DIR --video DIR --source PATH [--source PATH ...] [--date YYYY-MM-DD] [--slug NAME]
                  [--look NAME] [--no-project]
      Starts the work detached (the agent's shell stops a command after two minutes) and returns at once.
  ingest.py header --video DIR --slug NAME (--like PLAN | --session DIR) [--date YYYY-MM-DD] [--look NAME]
      Another video from a session already ingested: its plan header from an earlier video's plan (which carries the
      model's corrections) or from ingest's own, paths made relative to the new folder. Then project.py on it.
  ingest.py status --session DIR [--wait SECONDS]
      What is done, every measured fact with how it was measured, and `needs_the_model`. --wait blocks until the work
      ends or SECONDS pass (at most 110, inside the shell's limit). Exit 0 once everything is done with nothing failed.

Run it with the pipeline devenv's Python (numpy): `cd pipeline && devenv shell -- python3 b/ingest.py ...`.

--session is the session's folder (Edits/YYYY-MM-DD-...-session: audio, transcript, face scans, inventory.md, the
work's own files under ingest/). --video is the video's folder (Edits/YYYY-MM-DD-slug), where the plan's header goes.
A --source is a camera file, the screen recording, or a mounted card's folder (every clip under it is copied).

What it does, longest jobs first, each result measured and written to SESSION/ingest/state.json:
1. Reads every file with ffprobe and tells the cameras apart by their own tags: the Nikon (compatible brand "niko") is
   the front camera and the master clock; the DJI Pocket (encoder "DJI ...") is the wide camera and carries the lav;
   a ReplayKit file is the screen recording.
2. Copies a card's clips into Media/Input Media/<camera>/<session>/ with ditto before anything reads them (untested:
   no card was mounted when this was written), then hashes every file (SHA-256) alongside the rest: a copy against its
   card, a file already in Input Media against the session's metadata/copy-manifest.json if there is one.
3. Extracts each camera's frames at 5 a second for the face-touch scans (both cameras, whole files, alongside).
4. Extracts the lav (the Pocket's sound) and the front camera's own sound, and measures the lav's offset on the front
   camera's clock by cross-correlation at five points spread across the take, to the sample, so drift shows.
5. Pads the lav onto the front clock (48 kHz, 24-bit) and makes the 16 kHz mono copy, and at once starts the verbatim
   transcript (skill/scripts/verbatim_transcript.py, CrisperWhisper; the long pole, about 6 minutes for 23).
6. Measures the wide camera's picture offset against the front's from his head's motion seen by both cameras (the
   face's centre in three 20 s windows at 25 fps, cross-correlated to a fraction of a frame), because the Pocket's
   picture runs ahead of its own (radio) sound.
7. Finds a room-tone window (the quietest 3 s, clean after high-passing at 1 and 4 kHz), takes stills of both cameras
   at three points with their luma spread (for the log profile, judged by eye), reads the Nikon's picture control
   with ExifTool, and indexes the screen recording's frame times.
8. Writes the video folder's plan.json header (the keys at the top of assemble.py; nothing editorial) and a measured
   section of the session's inventory.md, then runs project.py on the header (Resolve, windowless).
9. When the scans and the transcript finish: the face-touch scans on the front clock (both cameras, flagged moments
   listed), and the transcript checked for reach and long gaps.

What it leaves to the model, listed in `needs_the_model` with the evidence: the log profiles by eye, each camera's
picture against its own sound, the transcript's names, the screen recording's offset and private detail, the flagged
face touches, record.md, and anything a measurement could not settle (drift over a frame, a picture offset that
disagrees across windows, no clean room tone).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MEDIA = Path(os.environ.get("VIDEO_MEDIA", "/Volumes/Josh Extreme Pro USB4 4TB/Media"))
INPUT = MEDIA / "Input Media"
CACHE = MEDIA / "Edits/.cache"
SCRIPTS = REPO / "skill/scripts"
SR = 48000
CAMERA_FOLDERS = {"front": "Nikon ZF", "wide": "DJI Osmo Pocket 4", "screen": "Screen"}
LOG_NAMES = {"front": "Nikon N-Log", "wide": "DJI D-Gamut/D-Log"}  # Resolve's names for the input colour spaces
OFFSET_POINTS, OFFSET_WINDOW_S = 5, 20.0
PICTURE_WINDOWS, PICTURE_WINDOW_S = 5, 20.0
DRIFT_WORTH_A_LOOK_S = 0.02  # half a frame at 25 fps
FACE_FPS = 5
# Inside the devenv, DEVELOPER_DIR and SDKROOT point at Nix's Apple SDK, which turns /usr/bin/python3 into Nix's Python
# (no Resolve scripting) and swiftc's SDK into an older one: Apple's own tools get the environment without them.
APPLE_ENV = {k: v for k, v in os.environ.items() if k not in ("DEVELOPER_DIR", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET")}


# ---------- small helpers ----------

def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, **kwargs)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout
    return json.loads(out)


def kind_of(info):
    tags = {k.lower(): v for k, v in (info["format"].get("tags") or {}).items()}
    if "niko" in tags.get("compatible_brands", ""):
        return "front"
    if tags.get("encoder", "").startswith("DJI"):
        return "wide"
    if "replaykit" in tags.get("com.apple.quicktime.author", "").lower():
        return "screen"
    return None


def video_stream(info):
    return next(s for s in info["streams"] if s["codec_type"] == "video")


def read_wav_mono(path, start=None, length=None, rate=SR):
    import numpy as np
    command = ["ffmpeg", "-v", "error"]
    if start is not None:
        command += ["-ss", f"{max(0.0, start):.6f}"]
    command += ["-i", str(path)]
    if length is not None:
        command += ["-t", f"{length:.6f}"]
    command += ["-ac", "1", "-ar", str(rate), "-f", "f32le", "-"]
    return np.frombuffer(run(command).stdout, np.float32).astype(np.float64)


def lag_of(reference, other, max_lag):
    """The lag (in samples, fractional) at which OTHER best matches REFERENCE: reference[n] ~ other[n - lag]."""
    import numpy as np
    n = len(reference) + len(other)
    size = 1 << (n - 1).bit_length()
    spectrum = np.fft.rfft(reference - reference.mean(), size) * np.conj(np.fft.rfft(other - other.mean(), size))
    c = np.fft.irfft(spectrum / (np.abs(spectrum) + 1e-12), size)  # phase transform: sharp peaks for speech
    lags = np.r_[0:max_lag + 1, size - max_lag:size]
    k = lags[int(np.argmax(c[lags]))]
    peak = c[k]
    left, right = c[(k - 1) % size], c[(k + 1) % size]
    shift = 0.5 * (left - right) / (left - 2 * peak + right) if (left - 2 * peak + right) != 0 else 0.0
    lag = (k if k <= size // 2 else k - size) + shift
    strength = float(peak / (np.sqrt(np.mean(c ** 2)) + 1e-12))
    return lag, strength


# ---------- the state file ----------

class State:
    def __init__(self, session):
        self.path = session / "ingest" / "state.json"
        self.lock = threading.Lock()
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {"steps": {}, "facts": {}, "needs": []}

    def save(self):
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False, default=str))
            os.replace(tmp, self.path)

    def step(self, name, status, **extra):
        with self.lock:
            row = self.data["steps"].setdefault(name, {})
            if status == "running":
                row["started"] = time.time()
            if status in ("done", "failed"):
                row["seconds"] = round(time.time() - row.get("started", time.time()), 1)
            row.update(status=status, **extra)
        self.save()

    def fact(self, key, value, how):
        with self.lock:
            self.data["facts"][key] = {"value": value, "how": how}
        self.save()

    def need(self, what):
        with self.lock:
            self.data["needs"].append(what)
        self.save()


def stage(state, name):
    """Run the decorated function as a step: its status, time and any error go to the state file."""
    def wrap(function):
        def inner(*args, **kwargs):
            state.step(name, "running")
            try:
                result = function(*args, **kwargs)
                state.step(name, "done", result=result)
                return result
            except Exception as error:
                state.step(name, "failed", error=f"{type(error).__name__}: {error}", trace=traceback.format_exc()[-2000:])
                raise
        return inner
    return wrap


# ---------- the work ----------

def work(session):
    request = json.loads((session / "ingest" / "request.json").read_text())
    state = State(session)
    video = Path(request["video"])
    session_name = session.name
    work_dir = CACHE / "ingest" / session_name
    work_dir.mkdir(parents=True, exist_ok=True)
    (session / "audio").mkdir(parents=True, exist_ok=True)
    (session / "transcript").mkdir(parents=True, exist_ok=True)
    (session / "face-touch").mkdir(parents=True, exist_ok=True)
    began = time.time()
    state.data["started"] = began
    state.save()

    # 1. what each file is
    @stage(state, "probe")
    def classify():
        files = []
        for source in request["sources"]:
            source = Path(source)
            candidates = [source] if source.is_file() else sorted(
                p for p in source.rglob("*") if p.suffix.upper() in (".MOV", ".MP4", ".LRF") and not p.name.startswith("."))
            for path in candidates:
                info = probe(path)
                files.append({"path": str(path), "kind": kind_of(info) if path.suffix.upper() != ".LRF" else "proxy",
                              "bytes": path.stat().st_size, "duration_s": float(info["format"]["duration"]),
                              "video": {k: video_stream(info).get(k) for k in ("codec_name", "width", "height", "r_frame_rate",
                                                                              "avg_frame_rate", "nb_frames", "color_range")},
                              "audio": [{k: s.get(k) for k in ("codec_name", "channels", "sample_rate")}
                                        for s in info["streams"] if s["codec_type"] == "audio"],
                              "tags": info["format"].get("tags")})
        kinds = [f["kind"] for f in files]
        for needed in ("front", "wide"):
            if kinds.count(needed) != 1:
                raise RuntimeError(f"expected one {needed} camera file, found {kinds.count(needed)}: {kinds}")
        return files
    files = classify()
    by_kind = {f["kind"]: f for f in files if f["kind"] in ("front", "wide", "screen")}

    # 2. copies: a card's clips are copied first (every later step reads the copy), then every file is hashed alongside
    @stage(state, "copy from cards")
    def copy_cards():
        copied = []
        for f in files:
            path = Path(f["path"])
            if INPUT in path.parents:
                continue
            target = INPUT / CAMERA_FOLDERS.get(f["kind"], "Other") / session_name / path.name
            if target.exists():
                raise RuntimeError(f"{target} exists; not overwriting a copy")
            target.parent.mkdir(parents=True, exist_ok=True)
            run(["ditto", str(path), str(target)])
            f["source"], f["path"] = str(path), str(target)
            copied.append(str(target))
        return copied
    copy_cards()

    def hashes():
        state.step("hashes", "running")
        try:
            manifest_path = session / "metadata" / "copy-manifest.json"
            manifest = {Path(m["copy"]).name: m for m in json.loads(manifest_path.read_text())} if manifest_path.exists() else {}
            rows = []
            for f in files:
                copy = Path(f["path"])
                row = {"file": copy.name, "copy": str(copy), "bytes": copy.stat().st_size, "sha256": sha256(copy)}
                if "source" in f:
                    row.update(source=f["source"], sha256_source=sha256(Path(f["source"])))
                    row["matches"] = row["sha256"] == row["sha256_source"] and row["bytes"] == f["bytes"]
                else:
                    known = manifest.get(copy.name)
                    row["matches"] = (known["sha256"] == row["sha256"] and known["bytes"] == row["bytes"]) if known else None
                rows.append(row)
            bad = [r["file"] for r in rows if r["matches"] is False]
            if bad:
                state.need(f"copies that do not match their card or the session's copy-manifest.json: {bad}; do not delete the card")
            state.step("hashes", "done", result=rows)
        except Exception as error:
            state.step("hashes", "failed", error=f"{type(error).__name__}: {error}")
    copier = threading.Thread(target=hashes)
    copier.start()

    # 3. frames for the face scans, alongside
    face_binary = CACHE / "bin" / "face_touch"
    source = SCRIPTS / "face_touch.swift"
    if not face_binary.exists() or face_binary.stat().st_mtime < source.stat().st_mtime:
        face_binary.parent.mkdir(parents=True, exist_ok=True)
        run(["/usr/bin/swiftc", "-O", "-module-cache-path", str(CACHE / "modulecache"), str(source), "-o", str(face_binary)], env=APPLE_ENV)

    scans = {}

    def scan(kind):
        name = f"face scan {kind}"
        state.step(name, "running")
        try:
            frames = work_dir / f"frames-{kind}"
            if frames.exists():
                shutil.rmtree(frames)
            frames.mkdir(parents=True)
            run(["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-i", by_kind[kind]["path"], "-map", "0:v:0",
                 "-vf", f"fps={FACE_FPS},scale=640:-2", "-q:v", "4", str(frames / "%06d.jpg")])
            raw = run([str(face_binary), str(frames), str(FACE_FPS), "0"]).stdout.decode()
            (work_dir / f"face-{kind}-file-clock.csv").write_text(raw)
            shutil.rmtree(frames)
            scans[kind] = raw
            state.step(name, "done", result={"samples": raw.count("\n") - 1})
        except Exception as error:
            state.step(name, "failed", error=f"{type(error).__name__}: {error}")
    scanners = [threading.Thread(target=scan, args=(k,)) for k in ("front", "wide")]
    for t in scanners:
        t.start()

    # 4. the lav's offset on the front clock
    @stage(state, "lav offset")
    def lav_offset():
        lav_raw = work_dir / "lav-pocket-48k.wav"
        front_raw = work_dir / "front-camera-48k.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", by_kind["wide"]["path"], "-map", "0:a:0", "-ar", str(SR), "-c:a", "pcm_s24le", str(lav_raw)])
        run(["ffmpeg", "-v", "error", "-y", "-i", by_kind["front"]["path"], "-map", "0:a:0", "-ar", str(SR), "-c:a", "pcm_s24le", str(front_raw)])
        return measure_offset(front_raw, lav_raw)
    offset = lav_offset()
    lav_offset_s = offset["offset_s"]
    state.fact("lav_offset_s", lav_offset_s, offset["how"])
    if offset["drift_s"] > DRIFT_WORTH_A_LOOK_S:
        state.need(f"the lav drifts {offset['drift_s'] * 1000:.1f} ms against the front camera over the take "
                   f"({offset['points']}): more than half a frame; decide whether a speed correction is needed")

    # 5. the padded lav, its 16 kHz copy, and the transcript started
    @stage(state, "lav on the front clock")
    def pad():
        lav_raw = work_dir / "lav-pocket-48k.wav"
        padded = session / "audio" / "lav-front-48k.wav"
        small = session / "audio" / "lav-front-16k.wav"
        samples = round(lav_offset_s * SR)
        front_samples = int(json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=duration_ts", "-of", "json",
                                            str(work_dir / "front-camera-48k.wav")]).stdout)["streams"][0]["duration_ts"])
        shift = f"adelay=delays={samples}S:all=1" if samples >= 0 else f"atrim=start_sample={-samples},asetpts=PTS-STARTPTS"
        audio_filter = f"{shift},apad,atrim=end_sample={front_samples}"  # the front camera's length, sample for sample
        run(["ffmpeg", "-v", "error", "-y", "-i", str(lav_raw), "-af", audio_filter, "-c:a", "pcm_s24le", str(padded)])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(padded), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(small)])
        check = measure_lag(work_dir / "front-camera-48k.wav", padded, 60.0)
        return {"padded": str(padded), "small": str(small), "samples": samples,
                "check": f"the padded lav against the front camera's sound at front 60 s: {check * 1000:+.2f} ms"}
    padded = pad()

    # The recogniser runs on the lav as recorded, with the offset added to its times: 36 s of padding ahead of the
    # first word only gives it silence to hallucinate in, and October's transcript was made the same way.
    transcript_base = session / "transcript" / "lav-verbatim-front"
    transcript_log = work_dir / "transcript.log"
    lav_small = work_dir / "lav-pocket-16k.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(work_dir / "lav-pocket-48k.wav"), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(lav_small)])
    state.step("transcript", "running")
    transcriber = subprocess.Popen(
        ["devenv", "shell", "--", "uv", "run", "-q", "--with", "torch", "--with", "transformers==4.46.3", "--with", "accelerate",
         "--with", "numpy", "--with", "soundfile", "--with", "soxr", "python", "-B", "-I", "verbatim_transcript.py",
         str(lav_small), str(transcript_base), f"{lav_offset_s:.6f}"],
        cwd=SCRIPTS, stdout=open(transcript_log, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    state.data["steps"]["transcript"]["pid"] = transcriber.pid
    state.save()

    def transcript_done():
        code = transcriber.wait()
        try:
            checked = check_transcript(transcript_base, padded["padded"])
        except Exception as error:
            checked = {"error": f"{type(error).__name__}: {error}"}
        state.step("transcript", "done" if code == 0 and "error" not in checked else "failed", result=checked, log=str(transcript_log))
        if checked.get("gaps_over_10_s"):
            state.need(f"the transcript has no words in {checked['gaps_over_10_s']} (front seconds): the recogniser drops words "
                       "after a long pause (on 12 Oct it lost 'Cut. And [UM] d- open this on fucking Google.' at 924.5 s); "
                       "transcribe each gap you might use again on its own (tools/rig-and-ingest.md)")
    transcript_watch = threading.Thread(target=transcript_done)
    transcript_watch.start()

    # 6. the wide camera's picture offset
    @stage(state, "wide picture offset")
    def picture_offset():
        return measure_picture_offset(by_kind, lav_offset_s, work_dir, face_binary)
    try:
        picture = picture_offset()
        wide_picture_s = picture["offset_s"]
        state.fact("wide_picture_offset_s", wide_picture_s, picture["how"])
        if picture["spread_s"] > 0.02:  # on 12 Oct the windows fell in two clusters 80 ms apart: no median is right
            wide_picture_s = lav_offset_s
            state.need(f"the wide camera's picture offset: his head's motion disagrees across the take ({picture['windows']}), "
                       f"so the header carries the lav's offset, {lav_offset_s:.3f} s; on 12 Oct the picture was 40 ms later "
                       "(36.777 s, from the clap and his lips). Settle it by eye on the clap or a p, b or m and set "
                       "the wide camera's picture_offset_s")
    except Exception:
        wide_picture_s = lav_offset_s
        state.need("the wide camera's picture offset could not be measured from his head's motion (see the step's error); "
                   f"the header uses the lav's offset, {lav_offset_s:.6f} s: measure picture against picture before cutting")

    # 7. room tone, stills, profile, screen index
    @stage(state, "room tone")
    def room():
        return find_room_tone(Path(padded["padded"]), max(0.0, lav_offset_s),
                              min(by_kind["front"]["duration_s"], by_kind["wide"]["duration_s"] + lav_offset_s))
    tone = room()
    if tone.get("window"):
        state.fact("room_tone_s", tone["window"], tone["how"])
    else:
        state.need("no 3 s room-tone window passed the click check: choose one by ear and level")

    @stage(state, "stills and profiles")
    def stills():
        out = video / "build" / "ingest" / "stills"
        out.mkdir(parents=True, exist_ok=True)
        rows = {}
        for kind in ("front", "wide"):
            duration = by_kind[kind]["duration_s"]
            rows[kind] = []
            for share in (0.1, 0.5, 0.9):
                at = round(duration * share, 2)
                path = out / f"{kind}-{at:.0f}s.jpg"
                run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", by_kind[kind]["path"], "-frames:v", "1", "-q:v", "3", str(path)])
                stats = run(["ffmpeg", "-v", "error", "-ss", str(at), "-i", by_kind[kind]["path"], "-frames:v", "1",
                             "-vf", "signalstats,metadata=print:file=-", "-f", "null", "-"]).stdout.decode()
                values = dict(re.findall(r"lavfi\.signalstats\.(YMIN|YLOW|YHIGH|YMAX|SATAVG)=([0-9.]+)", stats))
                rows[kind].append({"at_s": at, "still": str(path), **{k: float(v) for k, v in values.items()}})
        exiftool = sorted(Path("/nix/store").glob("*-Image-ExifTool-*/bin/exiftool"))
        if exiftool:
            tags = json.loads(run([str(exiftool[-1]), "-j", "-PictureControlName", "-PictureControlBase", "-LensModel",
                                   "-FNumber", "-ISO", "-WhiteBalance", by_kind["front"]["path"]]).stdout)[0]
            rows["front_maker_notes"] = {k: v for k, v in tags.items() if k != "SourceFile"}
        return rows
    profile = stills()
    front_control = str(profile.get("front_maker_notes", {}).get("PictureControlName", ""))
    state.fact("front_log", LOG_NAMES["front"] if "N-Log" in front_control else None,
               f"the Nikon's maker notes (ExifTool): picture control {front_control or 'unread'}")
    if "N-Log" not in front_control:
        state.need(f"the Nikon's picture control reads {front_control or 'nothing'}, not N-Log: set the front camera's log in "
                   "the plan from the stills, or none")
    state.need("the wide camera's log profile cannot be read from its file (DJI's tags are unreadable): confirm D-Log by eye "
               f"on the stills (flat, low contrast; luma 10th to 90th percentile {[(r.get('YLOW'), r.get('YHIGH')) for r in profile['wide']]} "
               f"of 0 to 1023; a Rec.709 picture of the same room spreads far wider), {[r['still'] for r in profile['wide']]}")

    if "screen" in by_kind:
        @stage(state, "screen index")
        def screen():
            times = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0",
                         by_kind["screen"]["path"]]).stdout.decode().split()
            times = sorted(float(t.strip(",")) for t in times if t.strip(","))
            index = session / "ingest" / "screen-frame-times.txt"
            index.write_text("\n".join(f"{t:.3f}" for t in times) + "\n")
            created = {k: (f["tags"] or {}).get("creation_time") for k, f in by_kind.items()}
            return {"frames": len(times), "index": str(index), "creation_times": created}
        screen_index = screen()
        state.need("the screen recording's offset on the front clock and its private detail: fix the offset on two events "
                   "both clocks record (his face lit by the screen, key clicks against characters appearing) far apart, and "
                   f"look at each change for emails and names; creation times (not to be trusted, off by seconds): "
                   f"{screen_index['creation_times']}; frame times: {screen_index['index']} (tools/rig-and-ingest.md)")

    # 8. the plan's header, inventory.md, the project
    @stage(state, "plan header")
    def header():
        date = request.get("date") or session_name[:10]
        slug = request.get("slug") or video.name[11:]
        look = request.get("look") or "2026-10-16-signpost-pill"
        feel = json.loads((REPO / "looks" / look / "look.json").read_text())["colour"]["feel"]
        rel = lambda path: os.path.relpath(path, video)
        fps = round(Fraction(by_kind["front"]["video"]["r_frame_rate"]))
        plan = {"_about": f"Header written by pipeline/b/ingest.py on {datetime.date.today()} from measured facts "
                          f"({session / 'ingest' / 'state.json'}); nothing editorial.",
                "resolve_project": f"{date} {slug}", "look": look, "fps": fps, "format": {"width": 1080, "height": 1920},
                "cameras": {
                    "front": {"file": rel(by_kind["front"]["path"]), "log": LOG_NAMES["front"], "group": "front",
                              "grade": feel, "picture_offset_s": 0, "reference": True},
                    "wide": {"file": rel(by_kind["wide"]["path"]), "log": LOG_NAMES["wide"], "group": "wide",
                             "grade": feel, "picture_offset_s": round(wide_picture_s, 3), "blur": True}},
                "sound": {"lav": rel(padded["padded"]), "room_tone_s": tone.get("window"), "room_tone_crossfade_ms": 200,
                          "room_tone_end_fade_ms": 300},
                "transcript": rel(str(transcript_base) + ".json")}
        video.mkdir(parents=True, exist_ok=True)
        target = video / "plan.json"
        if target.exists():
            target = video / "plan.header.json"
            state.need(f"{video / 'plan.json'} already exists, so the header went to {target}: merge its keys by hand")
        target.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
        write_session_header(session, plan, date, target)
        return {"plan": str(target), "header": plan}
    plan = header()
    write_inventory(session, state, files, offset, padded, tone, profile)

    if not request.get("no_project"):
        @stage(state, "project")
        def project():
            done = subprocess.run(["/usr/bin/python3", "-B", str(HERE / "project.py"), plan["plan"]],
                                  capture_output=True, text=True, env={**APPLE_ENV, "PYTHONUTF8": "1"})
            result = json.loads(done.stdout or "{}")
            if done.returncode or "error" in result:
                raise RuntimeError(result.get("error") or done.stderr[-500:])
            return result
        try:
            project()
        except Exception as error:
            state.need(f"project.py did not finish ({error}): see the project step's error, fix it, and run project.py on "
                       f"{plan['plan']} again (it adds only what is missing)")

    # 9. the long jobs' results
    for t in scanners:
        t.join()
    offsets = {"front": 0.0, "wide": wide_picture_s}
    flagged = {}
    for kind, raw in scans.items():
        lines = raw.strip().splitlines()
        rows = [line.split(",") for line in lines[1:]]
        shift = offsets[kind] + 2 / 25  # fps=5 takes input frame 5n+2 (checked on these files, 22 Oct)
        out = ["seconds,touching,points,face_x,face_y,face_h"] + [",".join([f"{float(r[0]) + shift:.3f}"] + r[1:]) for r in rows]
        (session / "face-touch" / f"{kind}.csv").write_text("\n".join(out) + "\n")
        flagged[kind] = moments([float(r[0]) + shift for r in rows if r[1] == "1"])
    if flagged:
        both = sorted(set(flagged.get("front", [])) | set(flagged.get("wide", [])))
        state.fact("face_touch_moments", {k: len(v) for k, v in flagged.items()},
                   f"face_touch.swift on both cameras' whole files at {FACE_FPS} a second, front clock; moments: {both[:60]}")
        state.need(f"look at every flagged face touch near a line you keep, on full-size frames ({len(both)} moments on "
                   f"either camera, a touch on one is a touch on both; all in face-touch/front.csv and wide.csv): {both}")
    copier.join()
    transcript_watch.join()
    state.need("the transcript's names (the recogniser mishears them: on 12 Oct 'codecs' for Codex, 'clawed' for Claude): correct them in a working copy from the tool's "
               "README and help, word by word, keep the raw file, and point the plan's transcript at the copy "
               "(tools/rig-and-ingest.md)")
    state.need("each camera's picture against its own sound: his lips closing on a p, b or m against the lav, late in the take "
               "(the wide camera's offset above is picture against picture)")
    state.need("record.md: Josh's words about this video (the raw-steering skill's scripts)")
    state.data["finished"] = time.time()
    state.data["seconds"] = round(time.time() - began, 1)
    state.save()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def measure_lag(reference_path, other_path, at_s, length=OFFSET_WINDOW_S, max_lag_s=0.05):
    """OTHER's lag against REFERENCE at the same file time AT_S, in seconds: reference(t) ~ other(t - lag)."""
    a = read_wav_mono(reference_path, at_s, length)
    b = read_wav_mono(other_path, at_s, length)
    lag, _ = lag_of(a, b, int(max_lag_s * SR))
    return lag / SR


def measure_offset(front_path, lav_path):
    """The lav's offset (front time = lav time + offset): a coarse search on the two sounds' envelopes over the whole
    take, then five 20 s windows at 48 kHz, each to a fraction of a sample."""
    import numpy as np
    rate = 1000
    front = read_wav_mono(front_path, rate=8000)
    lav = read_wav_mono(lav_path, rate=8000)
    envelope = lambda x: np.abs(x[: len(x) // 8 * 8]).reshape(-1, 8).mean(1)  # 1 kHz envelope
    coarse_lag, strength = lag_of(envelope(front), envelope(lav), len(front) // 8)
    coarse = coarse_lag / rate
    overlap_start, overlap_end = max(0.0, coarse), min(len(front) / 8000, len(lav) / 8000 + coarse)
    points = []
    for i in range(OFFSET_POINTS):
        at = overlap_start + (overlap_end - overlap_start - OFFSET_WINDOW_S) * (i + 0.5) / OFFSET_POINTS
        a = read_wav_mono(front_path, at, OFFSET_WINDOW_S)
        b = read_wav_mono(lav_path, at - coarse, OFFSET_WINDOW_S)
        lag, quality = lag_of(a, b, int(0.05 * SR))
        points.append({"front_s": round(at, 1), "offset_s": round(coarse + lag / SR, 6), "peak": round(quality, 1)})
    values = sorted(p["offset_s"] for p in points)
    offset = values[len(values) // 2]  # the middle of the take: half the drift either side, not all of it at one end
    slope = np.polyfit([p["front_s"] for p in points], [p["offset_s"] for p in points], 1)[0]
    drift = abs(slope) * (overlap_end - overlap_start)
    return {"offset_s": offset, "coarse_s": round(coarse, 4), "points": points, "drift_s": round(drift, 6),
            "how": f"cross-correlation of the lav with the front camera's own sound: coarse {coarse:.3f} s over the whole take "
                   f"(envelopes, peak {strength:.0f}), then five 20 s windows at 48 kHz (phase transform, sub-sample): "
                   + ", ".join(f"{p['offset_s']:.6f} at front {p['front_s']:.0f} s" for p in points)
                   + f"; the median is used; drift {drift * 1000:.1f} ms over the whole overlap (straight-line fit)"}


def measure_picture_offset(by_kind, sound_offset, work_dir, face_binary):
    """The wide camera's picture offset (front time = wide file time + offset), from his head's motion: the face's
    centre on both cameras at 25 fps in three 20 s windows, cross-correlated, refined to a fraction of a frame."""
    import numpy as np
    fps = 25.0
    front_len, wide_len = by_kind["front"]["duration_s"], by_kind["wide"]["duration_s"]
    start, end = max(0.0, sound_offset) + 30, min(front_len, wide_len + sound_offset) - 30
    windows = []
    for i in range(PICTURE_WINDOWS):
        at = start + (end - start - PICTURE_WINDOW_S) * (i + 0.5) / PICTURE_WINDOWS
        traces = {}
        for kind, file_at in (("front", at), ("wide", at - sound_offset - 1.0)):
            length = PICTURE_WINDOW_S + (2.0 if kind == "wide" else 0.0)
            folder = work_dir / f"picture-{kind}-{i}"
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True)
            # showinfo gives each frame's own time after the seek, so a seek that lands up to a frame late costs nothing
            shown = run(["ffmpeg", "-v", "info", "-hide_banner", "-ss", f"{file_at:.3f}", "-i", by_kind[kind]["path"], "-t", f"{length:.3f}",
                         "-map", "0:v:0", "-vf", "showinfo,scale=640:-2", "-q:v", "4", str(folder / "%06d.jpg")]).stderr.decode()
            frame_times = [file_at + float(t) for t in re.findall(r"\] n:\s*\d+ pts:\s*-?\d+ pts_time:(-?[0-9.]+)", shown)]
            rows = [line.split(",") for line in run([str(face_binary), str(folder), str(fps), "0"]).stdout.decode().splitlines()[1:]]
            shutil.rmtree(folder)
            if not 0 <= len(frame_times) - len(rows) <= 1:  # showinfo also sees the frame that -t then drops
                raise RuntimeError(f"{kind}: {len(rows)} frames scanned but {len(frame_times)} frame times read")
            t = np.array(frame_times[:len(rows)])
            y = np.array([float(r[4]) if r[4] else np.nan for r in rows])
            x = np.array([float(r[3]) if r[3] else np.nan for r in rows])
            h = np.array([float(r[5]) if r[5] else np.nan for r in rows])
            traces[kind] = (t, x, y, h)
        tf, xf, yf, hf = traces["front"]
        tw, xw, yw, hw = traces["wide"]
        best = None
        for lag in np.arange(-0.2, 0.2001, 0.002):  # candidate corrections to the sound's offset
            score = 0.0
            for f_signal, w_signal in ((yf, yw), (xf, xw), (hf, hw)):
                w_on_front = np.interp(tf, tw + sound_offset + lag, w_signal, left=np.nan, right=np.nan)
                ok = ~np.isnan(f_signal) & ~np.isnan(w_on_front)
                if ok.sum() < 100:
                    continue
                smooth = np.ones(5) / 5  # Vision's box jitters frame to frame; unsmoothed, correlations stayed under 0.4
                df = np.diff(np.convolve(f_signal[ok], smooth, "valid"))  # motion, not position: the two angles differ
                dw = np.diff(np.convolve(w_on_front[ok], smooth, "valid"))
                if df.std() > 0 and dw.std() > 0:
                    score += float(np.corrcoef(df, dw)[0, 1])
            if best is None or score > best[1]:
                best = (lag, score)
        windows.append({"front_s": round(at, 1), "offset_s": round(sound_offset + best[0], 4), "correlation": round(best[1] / 3, 3)})
    good = [w for w in windows if w["correlation"] >= 0.5]
    if not good:
        raise RuntimeError(f"his head's motion did not match between the cameras in any window: {windows}")
    values = sorted(w["offset_s"] for w in good)
    offset = values[len(values) // 2]
    return {"offset_s": offset, "windows": windows, "spread_s": round(max(values) - min(values), 4),
            "how": "his head's motion (the face box's centre and height, frame to frame, Apple Vision) on both cameras at 25 fps in five "
                   "20 s windows, smoothed over 5 frames, cross-correlated in 2 ms steps: " + ", ".join(
                       f"{w['offset_s']:.3f} at front {w['front_s']:.0f} s (correlation {w['correlation']})" for w in windows)
                   + "; the median of windows with correlation 0.5 or more"}


def find_room_tone(padded, first_s, last_s):
    """The quietest 3 s of the lav between FIRST_S and LAST_S (where the lav has sound, not padding) that has no click: no 5 ms window more than 6 dB over its band's own
    median after high-passing at 1 and 4 kHz (the check October's sound used)."""
    import numpy as np
    x = read_wav_mono(padded)
    hop = int(0.03 * SR)
    frames = len(x) // hop
    level = 10 * np.log10((x[: frames * hop].reshape(frames, hop) ** 2).mean(1) + 1e-12)
    width = int(3.0 / 0.03)
    window_level = np.convolve(level, np.ones(width) / width, mode="valid")
    peak = np.array([level[i:i + width].max() for i in range(0, len(window_level))])  # loudest 30 ms inside the window
    order = np.argsort(peak)
    order = order[(order * 0.03 >= first_s + 1.0) & (order * 0.03 + 3.0 <= last_s - 1.0)]
    tried = []
    taken = []
    for i in order[:400]:
        start = i * 0.03
        if start < first_s + 1.0 or start + 3.0 > last_s - 1.0 or any(abs(start - t) < 3.0 for t in taken):
            continue
        taken.append(start)
        clip = x[int(start * SR):int((start + 3.0) * SR)]
        spectrum = np.fft.rfft(clip)
        freqs = np.fft.rfftfreq(len(clip), 1 / SR)
        clean = True
        for cutoff in (1000, 4000):
            band = np.fft.irfft(np.where(freqs >= cutoff, spectrum, 0), len(clip))
            small = int(0.005 * SR)
            band_level = 10 * np.log10((band[: len(band) // small * small].reshape(-1, small) ** 2).mean(1) + 1e-15)
            if (band_level > np.median(band_level) + 6).any():
                clean = False
        tried.append({"window": [round(start, 2), round(start + 3.0, 2)], "peak_dbfs": round(float(peak[i]), 1),
                      "mean_dbfs": round(float(window_level[i]), 1), "clean": clean})
        if clean:
            return {"window": [round(start, 2), round(start + 3.0, 2)], "tried": tried,
                    "how": f"the quietest 3 s of the lav (loudest 30 ms inside it {peak[i]:.1f} dBFS, mean {window_level[i]:.1f}) "
                           f"with no 5 ms window 6 dB over its band's median at 1 and 4 kHz; {len(tried) - 1} quieter windows failed that"}
        if len(tried) >= 20:
            break
    return {"window": None, "tried": tried}


def moments(times, gap=0.5):
    """Flagged sample times grouped into moments [first, last]."""
    out = []
    for t in sorted(times):
        if out and t - out[-1][1] <= gap:
            out[-1][1] = round(float(t), 2)
        else:
            out.append([round(float(t), 2), round(float(t), 2)])
    return [tuple(m) for m in out]


def check_transcript(base, audio):
    path = Path(str(base) + ".json")
    if not path.exists():
        return {"error": "no transcript written"}
    words = json.loads(path.read_text())["words"]
    length = float(json.loads(run(["ffprobe", "-v", "error", "-show_format", "-of", "json", str(audio)]).stdout)["format"]["duration"])
    gaps = [(round(a["end"], 1), round(b["start"], 1)) for a, b in zip(words, words[1:]) if b["start"] - a["end"] > 10]
    return {"words": len(words), "first_s": words[0]["start"] if words else None, "last_s": words[-1]["end"] if words else None,
            "audio_s": round(length, 1), "gaps_over_10_s": gaps,
            "note": "look at every long gap: the recogniser can loop over a pause and drop the words it loses track of"}


def write_inventory(session, state, files, offset, padded, tone, profile):
    """A measured section in the session's inventory.md (appended; what the model judged it adds itself)."""
    lines = [f"\n## Measured by ingest.py, {datetime.date.today()}\n",
             f"Written by pipeline/b/ingest.py (AI, Claude Opus 5.5's code). Every fact below was measured; its raw "
             f"results are in `ingest/state.json`. The front camera's clock is the master: front time = a file's own "
             f"time + its offset.\n",
             "| File | Kind | Length | Picture | Audio | Bytes |", "| --- | --- | --- | --- | --- | --- |"]
    for f in files:
        v = f["video"]
        audio = ", ".join(f"{a['codec_name']} {a['channels']} ch {a['sample_rate']}" for a in f["audio"]) or "none"
        lines.append(f"| `{Path(f['path']).name}` | {f['kind']} | {f['duration_s']:.2f} s | {v.get('width')}x{v.get('height')} "
                     f"{v.get('codec_name')}, {v.get('avg_frame_rate')} fps, range {v.get('color_range')} | "
                     f"{audio} | {f['bytes']:,} |")
    lines += ["",
              f"- **The lav's offset:** {offset['offset_s']:.6f} s. {offset['how']}.",
              f"- **The lav on the front clock:** `{os.path.relpath(padded['padded'], session)}` ({padded['samples']} samples of "
              f"padding) and its 16 kHz mono copy `{os.path.relpath(padded['small'], session)}`; {padded['check']}.",
              f"- **The wide camera's picture offset:** {state.data['facts'].get('wide_picture_offset_s', {}).get('value')} s. "
              f"{state.data['facts'].get('wide_picture_offset_s', {}).get('how', 'not measured')}.",
              f"- **Room tone:** {tone.get('window')}. {tone.get('how', 'no clean window found')}.",
              f"- **The Nikon's maker notes:** {profile.get('front_maker_notes')}.",
              f"- **Stills for the log profiles** (luma spread per still): "
              + "; ".join(f"{k}: " + ", ".join(f"{r['at_s']:.0f} s {r.get('YLOW')}-{r.get('YHIGH')}" for r in profile[k]) for k in ("front", "wide")) + "."]
    with open(session / "inventory.md", "a") as handle:
        handle.write("\n".join(lines) + "\n")


# ---------- a second video from an ingested session ----------

HEADER_KEYS = ("look", "fps", "format", "cameras", "sound", "transcript")
SESSION_HEADER = "plan-header.json"  # the session's facts for any video's plan, paths relative to the session folder


def write_session_header(session, header, date, source):
    """SESSION/plan-header.json: HEADER's keys with its paths, relative to the folder holding SOURCE, made relative to the
    session folder."""
    move = lambda path: os.path.relpath((Path(source).parent / path).resolve(), session)
    keep = {key: json.loads(json.dumps(header[key])) for key in HEADER_KEYS}
    for camera in keep["cameras"].values():
        camera["file"] = move(camera["file"])
    keep["sound"]["lav"], keep["transcript"] = move(keep["sound"]["lav"]), move(keep["transcript"])
    (session / SESSION_HEADER).write_text(json.dumps({"_about": f"The session's facts for any video's plan header (ingest.py "
                                                     f"header --session). Paths are relative to this folder. Written "
                                                     f"{datetime.date.today()} from {source}.", "date": date, **keep},
                                                    indent=1, ensure_ascii=False) + "\n")


def header_like(video, slug, like=None, session=None, date=None, look=None):
    """The plan header for another video from the same session: the header keys of LIKE (an earlier video's plan, which
    holds whatever the model corrected since ingest: the transcript copy with names fixed, a picture offset) or else the
    session's own header, SESSION/plan-header.json (ingest writes it; paths relative to the session folder), with its
    paths made relative to VIDEO and its own project name. Nothing editorial."""
    if like:
        source, folder = json.loads(Path(like).read_text()), Path(like).absolute().parent
    elif (session / SESSION_HEADER).exists():
        source, folder = json.loads((session / SESSION_HEADER).read_text()), session
    else:
        raise FileNotFoundError(f"{session / SESSION_HEADER} does not exist: give --like an earlier video's plan from this session")
    header = {key: json.loads(json.dumps(source[key])) for key in HEADER_KEYS}
    move = lambda path: os.path.relpath((folder / path).resolve(), video.absolute())
    for camera in header["cameras"].values():
        camera["file"] = move(camera["file"])
    header["sound"]["lav"], header["transcript"] = move(header["sound"]["lav"]), move(header["transcript"])
    if look:
        header["look"] = look
        feel = json.loads((REPO / "looks" / look / "look.json").read_text())["colour"]["feel"]
        for camera in header["cameras"].values():
            camera["grade"] = feel
    date = date or source.get("date") or source["resolve_project"][:10]
    plan = {"_about": f"Header written by pipeline/b/ingest.py header on {datetime.date.today()} from {like or session}; nothing editorial.",
            "resolve_project": f"{date} {slug}", **header}
    video.mkdir(parents=True, exist_ok=True)
    target = video / ("plan.header.json" if (video / "plan.json").exists() else "plan.json")
    target.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    return {"plan": str(target), "resolve_project": plan["resolve_project"],
            "next": f"/usr/bin/python3 -B {HERE / 'project.py'} '{target}' makes its project"}


# ---------- the command ----------

def status(session, wait):
    path = session / "ingest" / "state.json"
    deadline = time.time() + min(wait, 110)
    while True:
        data = json.loads(path.read_text()) if path.exists() else {}
        if data.get("finished") or time.time() >= deadline:
            break
        time.sleep(2)
    steps = {name: {k: v for k, v in row.items() if k in ("status", "seconds", "error")} for name, row in data.get("steps", {}).items()}
    for name, row in steps.items():
        if row.get("status") == "running":
            row["running_for_s"] = round(time.time() - data["steps"][name].get("started", time.time()), 1)
    failed = [n for n, r in steps.items() if r.get("status") == "failed"]
    if data.get("stopped"):
        failed.append(f"the work stopped: {data['stopped']}")
    return {"finished": bool(data.get("finished")), "seconds": data.get("seconds"), "steps": steps,
            "facts": data.get("facts", {}), "needs_the_model": data.get("needs", []), "failed": failed,
            "state": str(path)}, (0 if data.get("finished") and not failed else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--session", type=Path, required=True)
    start.add_argument("--video", type=Path, required=True)
    start.add_argument("--source", type=Path, action="append", required=True)
    start.add_argument("--date")
    start.add_argument("--slug")
    start.add_argument("--look")
    start.add_argument("--no-project", action="store_true")
    show = sub.add_parser("status")
    show.add_argument("--session", type=Path, required=True)
    show.add_argument("--wait", type=float, default=0)
    second = sub.add_parser("header", help="the plan header for another video from an ingested session")
    second.add_argument("--video", type=Path, required=True)
    second.add_argument("--slug", required=True)
    second.add_argument("--like", type=Path, help="an earlier video's plan from the same session (default: the session's plan-header.json)")
    second.add_argument("--save-for-session", action="store_true",
                        help="with --like and --session: also save that plan's facts as the session's plan-header.json")
    second.add_argument("--session", type=Path)
    second.add_argument("--date")
    second.add_argument("--look")
    worker = sub.add_parser("work")
    worker.add_argument("--session", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "header":
        if not args.like and not args.session:
            sys.exit(json.dumps({"error": "give --like PLAN or --session SESSION"}))
        if args.save_for_session:
            if not (args.like and args.session):
                sys.exit(json.dumps({"error": "--save-for-session needs --like PLAN and --session SESSION"}))
            like = json.loads(args.like.read_text())
            feel = json.loads((REPO / "looks" / like["look"] / "look.json").read_text())["colour"]["feel"]
            for camera in like["cameras"].values():  # the session's start; a video's own grade is the colour stage's
                camera["grade"] = feel
                camera.pop("why", None)
            write_session_header(args.session.absolute(), like, args.date or like["resolve_project"][:10], args.like.absolute())
        print(json.dumps(header_like(args.video, args.slug, args.like, args.session and args.session.absolute(), args.date, args.look), indent=1))
        return
    session = args.session.absolute()
    if args.command == "start":
        (session / "ingest").mkdir(parents=True, exist_ok=True)
        if (session / "ingest" / "state.json").exists():
            sys.exit(json.dumps({"error": f"{session} has an ingest already; status --session to read it"}))
        (session / "ingest" / "request.json").write_text(json.dumps(
            {"video": str(args.video.absolute()), "sources": [str(s.absolute()) for s in args.source], "date": args.date,
             "slug": args.slug, "look": args.look, "no_project": args.no_project}, indent=1))
        log = open(session / "ingest" / "work.log", "w")
        process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "work", "--session", str(session)],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps({"started": True, "pid": process.pid, "status": f"ingest.py status --session '{session}' --wait 100"}))
    elif args.command == "status":
        result, code = status(session, args.wait)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        sys.exit(code)
    else:
        try:
            work(session)
        except Exception as error:
            state = State(session)
            state.data.update(finished=time.time(), stopped=f"{type(error).__name__}: {error}", trace=traceback.format_exc()[-3000:])
            state.save()
            raise


if __name__ == "__main__":
    main()

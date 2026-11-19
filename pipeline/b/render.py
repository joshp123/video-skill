"""Render a timeline from Resolve's render cache and wait for it.

Written by AI on 2026-11-17 by Claude Opus 5.5, from pipeline/resolve/render_timeline.py (GPT-6.1 Sol, 22 Oct; Claude
Opus 5.5, 26 and 27 Oct), as a command on the shared Resolve session. Renders from the render cache since 2026-11-19
(Claude Opus 5.5): every job uses cached frames where Resolve has them (UseRenderCachedImagesForRecording, which only a
render preset's file sets: the settings are saved as a preset, exported, the flag set in the file, and imported back).
build.py flags the background blur's node for the cache; Resolve fills the cache in the background while it is idle
(cache_filling() says whether it still is), and a render before that works the missing frames out live.

render.py PLAN.json --timeline NAME --out FILE [--preset phone|post|master|still] [--range IN OUT] [--no-captions]
          [--loudness PRESET]

- phone: H.264 High, multi-pass, sized to a 28 MB budget (Resolve's AAC is a fixed 320 kbit/s): the file Josh watches.
- post: H.264 High at 8 Mbit/s for 1080 by 1920 (X Media Studio's 5 to 8 Mbit/s), AAC 48 kHz: the file he posts.
- master: ProRes 422 HQ with 24-bit 48 kHz PCM.
- still: one lossless 16-bit PNG of a one-frame --range (Resolve appends the frame number to the name).
- sound: the sound only, 24-bit 48 kHz WAV, in about 3 s, in the format of the audio-only loudness preset (Resolve takes
  no WAV codec name by script); with --loudness off, the default, as the timeline mixes it (the join
  check scores this, since loudness normalisation moves clean joins' scores).
The caption track is burnt in unless --no-captions. --range is in timeline frames from 0, both ends included.
--loudness names a render preset that normalises the delivery's loudness (pipeline/b/loudness.py writes one); it is
loaded first and the format above set on top of it. --loudness off loads a preset with normalisation off ("B sound as
mixed ...", written the first time it is needed), the only way to turn it off once a project has rendered with one.

Refuses an existing file. A render blocks every other Resolve call until it ends (smoke tests, 17 Nov), so this returns only when the job is
complete, with its marks cleared and the job deleted. A job Resolve refuses to start is deleted and made again
(session.start_render: after a loudness-preset render the next job is refused until it is remade, 18 Nov). A finished file counts only when ffprobe finds a video stream in it (run 4 wrote two with sound and no picture).
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import session

FORMATS = {"phone": ("mp4", "H264"), "post": ("mp4", "H264"), "master": ("mov", "ProRes422HQ"), "still": ("png", "RGB16"),
           "sound": ("wav", None)}


CACHED_PRESET = "pipeline from cache"


def from_cache(project):
    """Make the current render settings use cached frames: save them as a preset, set the flag in its exported file,
    import it and load it (no call sets the flag; tested 18 and 19 Nov)."""
    resolve = session.start()
    directory = session.CACHE / "render-presets"
    if CACHED_PRESET in (project.GetRenderPresetList() or []):
        project.DeleteRenderPreset(CACHED_PRESET)
    if not project.SaveAsNewRenderPreset(CACHED_PRESET):
        raise RuntimeError("Could not save the render settings as a preset")
    exported = directory / f"{CACHED_PRESET} export"
    if not resolve.ExportRenderPreset(CACHED_PRESET, str(exported)):
        raise RuntimeError("Could not export the render preset")
    project.DeleteRenderPreset(CACHED_PRESET)
    found = sorted(exported.rglob("*.xml")) if exported.is_dir() else [exported]
    text = found[0].read_text(encoding='utf-8')
    if "<UseRenderCachedImagesForRecording>" not in text:
        raise RuntimeError("The exported render preset has no UseRenderCachedImagesForRecording")
    path = directory / f"{CACHED_PRESET}.xml"
    path.write_text(re.sub(r"<UseRenderCachedImagesForRecording>\w+<", "<UseRenderCachedImagesForRecording>true<", text))
    if not resolve.ImportRenderPreset(str(path)) or not project.LoadRenderPreset(CACHED_PRESET):
        raise RuntimeError(f"Could not import and load {path}")


def cache_filling(project, settle_s=20, limit_s=1800):
    """Wait until Resolve has written nothing to the project's render cache for SETTLE_S seconds. It fills the cache in the
    background while idle, and re-caches a changed clip by rewriting its files, so the folder's size can stay the same;
    the newest write is what tells. Returns {megabytes, seconds}."""
    folder = Path(project.GetSetting("perfCacheClipsLocation")) / project.GetUniqueId()
    began = time.monotonic()
    while time.monotonic() - began < limit_s:
        files = [f.stat() for f in folder.rglob("*.dvcc")] if folder.exists() else []
        newest = max((f.st_mtime for f in files), default=0)
        if time.monotonic() - began >= settle_s and time.time() - newest >= settle_s:
            break
        time.sleep(2)
    return {"megabytes": round(sum(f.st_size for f in files) / 2 ** 20), "seconds": round(time.monotonic() - began)}


def render(project, timeline, output, preset="phone", frame_range=None, captions=True, loudness=None):
    """Render TIMELINE to OUTPUT and wait. Returns {output, seconds, status}."""
    output = Path(output)
    if output.exists() or (preset == "still" and list(output.parent.glob(output.stem + "*.png"))):
        raise FileExistsError(f"Refusing to overwrite {output}")
    if preset == "still" and (not frame_range or frame_range[0] != frame_range[1]):
        raise ValueError("The still preset needs a one-frame --range IN IN")
    start = timeline.GetStartFrame()
    if not project.SetCurrentTimeline(timeline):
        raise RuntimeError(f"Could not make {timeline.GetName()!r} current")
    if preset == "sound" and not loudness:
        loudness = "off"  # Resolve takes no WAV codec name by script; the format comes from the audio-only preset
    if loudness == "off":
        import loudness as presets
        loudness = presets.as_mixed(session.start(), project, session.CACHE / "render-presets")
    if loudness and not project.LoadRenderPreset(loudness):
        raise RuntimeError(f"Could not load the render preset {loudness!r}")
    settings = timeline.GetSettings()
    output.parent.mkdir(parents=True, exist_ok=True)
    wanted = {"TargetDir": str(output.parent), "CustomName": output.stem, "ExportVideo": preset != "sound", "ExportAudio": preset != "still",
              "FormatWidth": int(settings["timelineResolutionWidth"]), "FormatHeight": int(settings["timelineResolutionHeight"]),
              "ExportSubtitle": captions}
    if captions and preset != "sound":
        wanted["SubtitleFormat"] = "BurnIn"
    else:
        wanted["ExportSubtitle"] = False
    if frame_range:
        wanted.update(SelectAllFrames=False, MarkIn=start + frame_range[0], MarkOut=start + frame_range[1])
        frames = frame_range[1] - frame_range[0] + 1
    else:
        wanted["SelectAllFrames"] = True
        frames = timeline.GetEndFrame() - start
    if preset in ("master", "sound"):
        wanted.update(AudioCodec="lpcm", AudioBitDepth=24, AudioSampleRate=48000)
    if preset in ("phone", "post"):
        seconds = frames / float(settings["timelineFrameRate"])
        bitrate = 8000 if preset == "post" else int(28000000 * 8 / seconds / 1000 - 320)
        wanted.update(VideoQuality=bitrate, EncodingProfile="High", MultiPassEncode=True, NetworkOptimization=True,
                      AudioCodec="aac", AudioSampleRate=48000, ColorSpaceTag="Rec.709", GammaTag="Rec.709")

    def add_job():
        if preset == "sound":
            if project.GetCurrentRenderFormatAndCodec()["format"] not in ("wav", "unknown"):  # the API reads the preset's WAV as unknown
                raise RuntimeError(f"the preset {loudness!r} did not set WAV")
        elif not project.SetCurrentRenderFormatAndCodec(*FORMATS[preset]):
            raise RuntimeError(f"Could not set the format for {preset}")
        if not project.SetRenderSettings(wanted):
            raise RuntimeError(f"SetRenderSettings refused {wanted}")
        if preset != "sound":
            from_cache(project)
            project.SetRenderSettings(wanted)
        return project.AddRenderJob()
    began = time.monotonic()
    job = None
    try:
        job = session.start_render(project, add_job)
        while True:
            status = project.GetRenderJobStatus(job) or {}
            state = str(status.get("JobStatus", "")).lower()
            if state == "complete":
                break
            if "fail" in state or "cancel" in state:
                raise RuntimeError(f"Render {state}: {status}")
            time.sleep(1)
    finally:
        timeline.ClearMarkInOut("all")
        if job:
            project.DeleteRenderJob(job)
    session.no_dialogs("rendering")
    if preset != "still":
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(output)],
                               capture_output=True, text=True).stdout
        kinds = sorted(stream["codec_type"] for stream in json.loads(probe or "{}").get("streams", []))
        if ("audio" if preset == "sound" else "video") not in kinds:
            raise RuntimeError(f"{output} has no video stream (streams: {kinds or 'none'}); do not use it")
    return {"output": str(output), "seconds": round(time.monotonic() - began, 1), "status": status}


def run(list_path, name, output, preset, frame_range, captions, loudness, wait_for_cache=False):
    data = json.loads(list_path.read_text(encoding='utf-8'))
    resolve, project = session.connect(data["resolve_project"])
    if project.IsRenderingInProgress():
        raise RuntimeError("Resolve is already rendering")
    timeline = session.timeline_named(project, name)
    if timeline is None:
        raise ValueError(f"No timeline {name!r}")
    project.SetCurrentTimeline(timeline)
    filled = cache_filling(project) if wait_for_cache else None
    result = render(project, timeline, output, preset, frame_range, captions, loudness)
    if filled:
        result["waited_for_the_cache"] = filled
    resolve.OpenPage("edit")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--preset", choices=sorted(FORMATS), default="phone")
    parser.add_argument("--range", dest="frame_range", type=int, nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--no-captions", action="store_true")
    parser.add_argument("--loudness", help="a loudness preset's name, or off")
    parser.add_argument("--wait-for-cache", action="store_true",
                        help="first wait until Resolve's background fill of the render cache stops growing")
    args = parser.parse_args()
    session.main(lambda: run(args.plan.resolve(), args.timeline, args.out.absolute(), args.preset, args.frame_range,
                             not args.no_captions, args.loudness, args.wait_for_cache))

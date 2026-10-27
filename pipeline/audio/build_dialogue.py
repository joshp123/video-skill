#!/usr/bin/env python3
"""Originally written by GPT-6.1 Sol.
Written by AI on 2026-10-22 by GPT-6.1 Sol: room tone, output and patch gain from data.
Updated by AI on 2026-10-22 by GPT-6 Astra: high-frequency room-tone checks and scratch paths.

Build sample-accurate dialogue from an edit folder's build/cutlist.json.
Usage: python3 pipeline/audio/build_dialogue.py EDIT [--output build/dialogue.wav]
Room-tone coordinates and audio cuts use the front camera's clock.
"""

import argparse
import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np


FADE_S = 0.015
TARGET_LUFS = -14.0
TRUE_PEAK_CEILING_DB = -1.0
CLEANUP = "highpass=f=80,afftdn=nr=10:nf=-50,acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=1"


def run_ffmpeg(arguments, **kwargs):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-y", *arguments],
        capture_output=True, check=True, **kwargs,
    )


def measure_loudness(path):
    result = run_ffmpeg(["-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], text=True)
    summary = result.stderr[result.stderr.rfind("Summary:"):]
    return {
        "integrated_lufs": float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary)[1]),
        "true_peak_dbtp": float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)[1]),
    }


def read_pcm(source, start_s, end_s):
    rate = source.getframerate()
    start_sample, end_sample = round(start_s * rate), round(end_s * rate)
    if not 0 <= start_sample < end_sample <= source.getnframes():
        raise ValueError(f"Lav range {start_s:.6f}..{end_s:.6f} is outside its file")
    source.setpos(start_sample)
    raw = source.readframes(end_sample - start_sample)
    width = source.getsampwidth()
    if width == 3:
        octets = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        values = octets[:, 0].astype(np.int32) | (octets[:, 1].astype(np.int32) << 8) | (octets[:, 2].astype(np.int32) << 16)
        values = np.where(values >= 1 << 23, values - (1 << 24), values)
        samples = values.astype(np.float32) / (1 << 23)
    elif width in (2, 4):
        samples = np.frombuffer(raw, f"<i{width}").astype(np.float32) / (1 << (8 * width - 1))
    else:
        raise ValueError(f"Expected 16-, 24- or 32-bit PCM lav; got {width * 8}-bit")
    return samples.reshape(-1, source.getnchannels())


def rms_db(samples):
    return float(20 * np.log10(np.sqrt(np.mean(samples.astype(np.float64) ** 2)) + 1e-12))


def inspect_room_tone(source, room_tone, lav_offset_s):
    rate, channels = source.getframerate(), source.getnchannels()
    start_s, end_s = (time - lav_offset_s for time in room_tone)
    context_start_s = max(0, start_s - 0.05)
    samples = read_pcm(source, context_start_s, end_s)
    window_samples = round(0.005 * rate)
    checks = []
    for cutoff_hz in (1000, 4000):
        filtered = run_ffmpeg([
            "-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", str(channels), "-i", "pipe:0",
            "-af", f"highpass=f={cutoff_hz},atrim=start_sample={round((start_s - context_start_s) * rate)}",
            "-f", "f32le", "pipe:1",
        ], input=samples.astype("<f4").tobytes()).stdout
        values = np.frombuffer(filtered, "<f4").reshape(-1, channels)
        windows = values[:len(values) // window_samples * window_samples].reshape(-1, window_samples, channels)
        levels = 20 * np.log10(np.sqrt(np.mean(windows.astype(np.float64) ** 2, axis=1)).max(axis=1) + 1e-12)
        median = float(np.median(levels))
        suspect = np.flatnonzero(levels > median + 6)
        checks.append({
            "highpass_hz": cutoff_hz, "window_s": 0.005,
            "median_dbfs": round(median, 2), "threshold_dbfs": round(median + 6, 2),
            "suspect_windows": [{
                "from_s": round(room_tone[0] + int(index) * window_samples / rate, 6),
                "to_s": round(room_tone[0] + (int(index) + 1) * window_samples / rate, 6),
                "rms_dbfs": round(float(levels[index]), 2),
            } for index in suspect],
        })
    return checks


def patch_envelope(clip, length, rate, patches):
    """Attenuate each patch's source range with its fades; absent gain replaces it with room tone.

    A patch removes a sound (a clipped breath, a scrap of the next word) without moving any cut."""
    keep = np.ones(length, np.float32)
    for patch in patches:
        fade = round(patch.get("fade_s", FADE_S) * rate)
        start = round((patch["from_s"] - clip["audio_in_s"]) * rate)
        end = round((patch["to_s"] - clip["audio_in_s"]) * rate)
        if end <= 0 or start >= length:
            continue
        gate = np.zeros(length, np.float32)
        gate[max(start, 0):min(end, length)] = 1
        if start > 0:
            ramp_start = max(start - fade, 0)
            gate[ramp_start:start] = np.linspace(0, 1, start - ramp_start, dtype=np.float32)
        if end < length:
            ramp_end = min(end + fade, length)
            gate[end:ramp_end] = np.linspace(1, 0, ramp_end - end, dtype=np.float32)
        gain = 10 ** (patch["gain_db"] / 20) if "gain_db" in patch else 0
        keep *= 1 - gate * (1 - gain)
    return keep


def build(edit_folder, output, cutlist=Path("build/cutlist.json")):
    edit_folder = edit_folder.resolve()
    cut = json.loads((edit_folder / cutlist).read_text())
    edit_data = json.loads((edit_folder / "edit/edit.json").read_text())
    room_tone = edit_data["media"]["lav"]["room_tone_s"]
    patches = edit_data.get("dialogue_patches", [])
    # A borrowed word: the same speaker's word from elsewhere in the same recording, laid in where his
    # take swallowed it. at_s is on the receiving clip's source clock; from_s..to_s is the word itself.
    inserts = edit_data.get("dialogue_inserts", [])
    # A line's sound may start before its picture (an audio pre-roll, e.g. to keep the breath that
    # starts a new thought) when the picture there is covered; the timing of every clip is unchanged.
    preroll = {line["id"]: line["audio_preroll_s"] for line in edit_data["lines"] if line.get("audio_preroll_s")}
    final_path = edit_folder / output
    build_folder = final_path.parent
    build_folder.mkdir(parents=True, exist_ok=True)
    report_path = build_folder / "dialogue-report.json"
    lav_path = (edit_folder / cut["media"]["lav"]["file"]).resolve()
    lav_offset_s = cut["media"]["lav"]["offset_s"]
    with wave.open(str(lav_path), "rb") as source:
        rate, channels = source.getframerate(), source.getnchannels()
        total_samples = round(cut["duration_s"] * rate)
        mix = np.zeros((total_samples, channels), np.float32)
        coverage = np.zeros(total_samples, np.float32)
        cut_levels = []
        for clip in cut["audio_clips"]:
            lead = preroll.get(clip.get("line"), 0.0) if clip.get("part", 0) == 0 else 0.0
            if lead:
                clip = {**clip, "audio_in_s": clip["audio_in_s"] - lead,
                        "audio_timeline_in_s": clip["audio_timeline_in_s"] - lead}
            samples = read_pcm(source, clip["audio_in_s"] - lav_offset_s, clip["audio_out_s"] - lav_offset_s)
            fade_samples = min(round(FADE_S * rate), len(samples) // 2)
            ramp = (0.5 - 0.5 * np.cos(np.linspace(0, math.pi, fade_samples))).astype(np.float32)
            envelope = np.ones(len(samples), np.float32)
            envelope[:fade_samples], envelope[-fade_samples:] = ramp, ramp[::-1]
            envelope *= patch_envelope(clip, len(samples), rate, patches)
            placement_s = clip["audio_timeline_in_s"]
            destination_start = round(placement_s * rate)
            destination_end = destination_start + len(samples)
            if destination_start < 0 or destination_end > total_samples:
                raise ValueError(f"Clip {clip.get('line', clip.get('line_id'))} audio extends outside the cut: {placement_s:.6f}s..{destination_end / rate:.6f}s")
            mix[destination_start:destination_end] += samples * envelope[:, None]
            coverage[destination_start:destination_end] += envelope
            context_samples = min(round(0.03 * rate), len(samples))
            cut_levels.append({
                "line": clip.get("line", clip.get("line_id")),
                "timeline_in_s": destination_start / rate,
                "source_in_front_s": clip["audio_in_s"],
                "source_out_front_s": clip["audio_out_s"],
                "in_rms_dbfs": round(rms_db(samples[:context_samples]), 2),
                "out_rms_dbfs": round(rms_db(samples[-context_samples:]), 2),
            })

        for insert in inserts:
            clip = next((c for c in cut["audio_clips"] if c["audio_in_s"] <= insert["at_s"] < c["audio_out_s"]), None)
            if clip is None:
                raise ValueError(f"Insert at {insert['at_s']} falls in no audio clip")
            word = read_pcm(source, insert["from_s"] - lav_offset_s, insert["to_s"] - lav_offset_s)
            fade = min(round(0.01 * rate), len(word) // 2)
            ramp = (0.5 - 0.5 * np.cos(np.linspace(0, math.pi, fade))).astype(np.float32)
            shape = np.ones(len(word), np.float32)
            shape[:fade], shape[-fade:] = ramp, ramp[::-1]
            start = round((clip["audio_timeline_in_s"] + insert["at_s"] - clip["audio_in_s"]) * rate)
            mix[start:start + len(word)] += word * shape[:, None]
            coverage[start:start + len(word)] += shape

        tone = read_pcm(source, room_tone[0] - lav_offset_s, room_tone[1] - lav_offset_s)
        room_tone_checks = inspect_room_tone(source, room_tone, lav_offset_s)
        crossfade_samples = min(round(0.5 * rate), len(tone) // 3)
        bed = np.zeros_like(mix)
        ramp = (0.5 - 0.5 * np.cos(np.linspace(0, math.pi, crossfade_samples))).astype(np.float32)
        position = 0
        while position < total_samples:
            piece = tone.copy()
            if position:
                piece[:crossfade_samples] *= ramp[:, None]
            piece[-crossfade_samples:] *= ramp[::-1, None]
            length = min(len(piece), total_samples - position)
            bed[position:position + length] += piece[:length]
            position += len(tone) - crossfade_samples
        fade_out_samples = min(round(1.5 * rate), total_samples)
        bed[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples, dtype=np.float32)[:, None]
        mix += bed * np.clip(1 - coverage, 0, 1)[:, None]

    work_folder = build_folder / "audio"
    work_folder.mkdir(parents=True, exist_ok=True)
    raw_path = work_folder / "dialogue_edit.wav"
    clean_path = work_folder / "dialogue_clean.wav"
    run_ffmpeg(["-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", str(channels), "-i", "pipe:0", "-c:a", "pcm_f32le", str(raw_path)], input=mix.astype("<f4").tobytes())
    run_ffmpeg(["-v", "error", "-i", str(raw_path), "-af", CLEANUP, "-c:a", "pcm_f32le", str(clean_path)])
    clean_levels = measure_loudness(clean_path)
    gain_db = TARGET_LUFS - clean_levels["integrated_lufs"]
    limiter_ceiling_db = TRUE_PEAK_CEILING_DB - 0.15
    measurements = []
    for attempt in range(8):
        limiter_amplitude = 10 ** (limiter_ceiling_db / 20)
        filters = (
            f"volume={gain_db:.4f}dB,aresample={rate * 4},"
            f"alimiter=limit={limiter_amplitude:.9f}:attack=5:release=50:level=false:latency=true,"
            f"aresample={rate},apad=whole_len={total_samples},atrim=end_sample={total_samples}"
        )
        run_ffmpeg(["-v", "error", "-i", str(clean_path), "-af", filters, "-c:a", "pcm_s24le", str(final_path)])
        levels = measure_loudness(final_path)
        measurements.append({"attempt": attempt + 1, "gain_db": gain_db, "limiter_ceiling_db": limiter_ceiling_db, **levels})
        if levels["true_peak_dbtp"] <= TRUE_PEAK_CEILING_DB and abs(levels["integrated_lufs"] - TARGET_LUFS) <= 0.2:
            break
        if levels["true_peak_dbtp"] > TRUE_PEAK_CEILING_DB:
            limiter_ceiling_db -= levels["true_peak_dbtp"] - TRUE_PEAK_CEILING_DB + 0.1
        gain_db += TARGET_LUFS - levels["integrated_lufs"]
    else:
        raise RuntimeError(f"Could not meet dialogue target after measured correction: {levels}")

    with wave.open(str(final_path), "rb") as final:
        final_samples = final.getnframes()
        if final_samples != total_samples:
            raise RuntimeError(f"Final dialogue length is {final_samples} samples; cut list needs {total_samples}")
    report = {
        "_about": "Written by AI on 2026-10-21 by GPT-6.1 Sol; generated from edit/edit.json and build/cutlist.json.",
        "edit_sha256": cut["edit_sha256"],
        "output": str(final_path), "source": str(lav_path), "sample_rate": rate,
        "channels": channels, "samples": final_samples, "duration_s": final_samples / rate,
        "room_tone_front_s": list(room_tone), "dialogue_patches": patches, "dialogue_inserts": inserts, "audio_preroll_s": preroll, "room_tone_rms_dbfs": round(rms_db(tone), 2),
        "room_tone_checks": room_tone_checks,
        "fade_s": FADE_S, "cleanup": CLEANUP, "limiter_latency_compensated": True,
        "limiter_oversampling": 4, "measurements": measurements,
        "final": levels, "cut_levels": cut_levels,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{final_path}: {final_samples / rate:.3f} s, {levels['integrated_lufs']:.1f} LUFS integrated, {levels['true_peak_dbtp']:.1f} dBTP (measured on final 24-bit WAV)")
    print(f"Room tone: front {room_tone[0]:.3f}..{room_tone[1]:.3f} s, {rms_db(tone):.1f} dBFS RMS")
    for check in room_tone_checks:
        print(f"Room tone above {check['highpass_hz']} Hz: {len(check['suspect_windows'])} suspect 5 ms windows over median +6 dB ({check['threshold_dbfs']:.1f} dBFS); see {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edit_folder", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/dialogue.wav"))
    parser.add_argument("--cutlist", type=Path, default=Path("build/cutlist.json"))
    args = parser.parse_args()
    build(args.edit_folder, args.output, args.cutlist)

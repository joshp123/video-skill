#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol.
Updated by AI on 2026-10-22 by GPT-6 Astra: alignment and graphic-edge faults."""

import argparse
import importlib.util
import json
import math
import re
import subprocess
from fractions import Fraction
from pathlib import Path
if "EDIT_FOLDER" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("edit_folder", type=Path)
    parser.add_argument("dialogue_file", type=Path)
    parser.add_argument("--cutlist", type=Path, default=Path("build/cutlist.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--bin-name", default="Generated")
    parser.add_argument("--transcribe-project", help="Use this already-open project for scratch transcription; never switch projects")
    args = parser.parse_args()
    EDIT_FOLDER, DIALOGUE_FILE = args.edit_folder, args.dialogue_file
    CUTLIST_FILE, OUTPUT_FILE, REPORT_FILE, BIN_NAME = args.cutlist, args.output, args.report, args.bin_name
    TRANSCRIBE_PROJECT = args.transcribe_project

edit = json.loads((Path(EDIT_FOLDER)/"edit/edit.json").read_text())
expected_project = globals().get("TRANSCRIBE_PROJECT") or edit["resolve_project"]

import time
if "resolve" not in globals():
    import DaVinciResolveScript
    resolve = DaVinciResolveScript.scriptapp("Resolve")

def call(method, *args):
    deadline = time.monotonic() + 1800
    while resolve.GetProjectManager().GetCurrentProject().GetName() != expected_project:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Expected project {expected_project!r} was unavailable for 30 minutes")
        time.sleep(30)
    return method(*args)

project = call(resolve.GetProjectManager().GetCurrentProject)

mp = call(project.GetMediaPool)
root = call(mp.GetRootFolder)
def find(folder, path):
    for item in call(folder.GetClipList) or []:
        if call(item.GetClipProperty, "File Path") == str(path):
            return item
    for child in call(folder.GetSubFolderList) or []:
        item = find(child, path)
        if item is not None:
            return item

def import_media(path, bin_name):
    item = find(root, path)
    if item is None:
        folder = next((child for child in call(root.GetSubFolderList) or [] if call(child.GetName) == bin_name), None)
        if folder is None:
            folder = call(mp.AddSubFolder, root, bin_name)
        call(mp.SetCurrentFolder, folder)
        try:
            item = call(mp.ImportMedia, [str(path)])[0]
        finally:
            call(mp.SetCurrentFolder, previous_folder)
    return item

def seconds(tc, fps):
    h, m, s, f = map(int, tc.split(":"))
    return h * 3600 + m * 60 + s + f / fps

folder = Path(EDIT_FOLDER).resolve()
path = (folder/Path(DIALOGUE_FILE)).resolve()
cut_path = (folder/Path(globals().get("CUTLIST_FILE", "build/cutlist.json"))).resolve()
output_path = (folder/Path(globals().get("OUTPUT_FILE") or cut_path)).resolve()
report_path = (folder/Path(globals().get("REPORT_FILE") or output_path.with_name("alignment-report.json"))).resolve()
if output_path != cut_path and output_path.exists():
    raise FileExistsError(f"Refusing to overwrite {output_path}")
if output_path != cut_path and report_path.exists():
    raise FileExistsError(f"Refusing to overwrite {report_path}")
cut = json.loads(cut_path.read_text())
audio = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration_ts,time_base,sample_rate", "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout)["streams"][0]
sample_rate = int(audio["sample_rate"])
dialogue_samples = round(int(audio["duration_ts"])*Fraction(audio["time_base"])*sample_rate)
dialogue_seconds = dialogue_samples/sample_rate
required_samples = round(Fraction(cut["duration_frames"])*sample_rate/Fraction(str(cut["fps"])))
if dialogue_samples != required_samples:
    raise RuntimeError(f"Dialogue is {dialogue_seconds:.3f}s; cut list needs {cut['duration_s']:.3f}s. Rebuild dialogue with build_dialogue.py before alignment.")
previous_folder = call(mp.GetCurrentFolder)
item = import_media(path, globals().get("BIN_NAME", "Generated"))
call(resolve.OpenPage, "edit")
t0 = time.monotonic()
assert call(item.TranscribeAudio, False)
transcript = call(item.GetTranscription)
clip_fps = float(call(item.GetClipProperty, "FPS"))
origin = seconds(call(item.GetClipProperty, "Start TC"), clip_fps)
recognized = [{"text": w["text"].strip(), "start": seconds(w["start"], clip_fps)-origin, "end": seconds(w["end"], clip_fps)-origin}
              for segment in transcript["segments"] for w in segment["words"] if w["text"].strip() != "(...)"]
def normalized(text):
    return re.sub(r"[^a-z0-9']", "", text.lower().replace("’", "'"))
line_ids = list(dict.fromkeys(w["line"] for w in cut["words"]))
print(f"Resolve words: {len(recognized)}; kept words: {len(cut['words'])}", flush=True)
position = 0
pairs = []
extra_resolve_words = []
for line in line_ids:
    kept = [w for w in cut["words"] if w["line"] == line]
    line_position = 0
    while line_position < len(kept):
        if position >= len(recognized):
            pairs.extend((word, None) for word in kept[line_position:])
            break
        if normalized(kept[line_position]["word"]) == normalized(recognized[position]["text"]):
            pairs.append((kept[line_position], recognized[position]))
            line_position += 1
            position += 1
            continue
        agreements = [(max(i,j), i+j, i, j)
                      for i in range(min(3, len(kept)-line_position-1)+1)
                      for j in range(min(3, len(recognized)-position-1)+1)
                      if (i or j) and normalized(kept[line_position+i]["word"]) == normalized(recognized[position+j]["text"])]
        if not agreements:
            pairs.append((kept[line_position], recognized[position]))
            line_position += 1
            position += 1
            continue
        _, _, cut_ahead, resolve_ahead = min(agreements)
        for offset in range(cut_ahead):
            partner = recognized[position+offset] if offset < resolve_ahead else None
            pairs.append((kept[line_position+offset], partner))
        extra_resolve_words.extend({"line":line, **word} for word in recognized[position+cut_ahead:position+resolve_ahead])
        line_position += cut_ahead
        position += resolve_ahead
extra_resolve_words.extend({"line":None, **word} for word in recognized[position:])

rejected_zero_length_words = []
for index, (word, partner) in enumerate(pairs):
    if partner is not None and partner["end"] <= partner["start"]:
        rejected_zero_length_words.append({"line":word["line"], "word":word["word"], "resolve_word":partner})
        pairs[index] = (word, {"text":"", "start":word["t"], "end":word["end"], "interpolated":True})

unpaired = []
index = 0
while index < len(pairs):
    if pairs[index][1] is not None:
        index += 1
        continue
    first = index
    while index < len(pairs) and pairs[index][1] is None:
        index += 1
    if first == 0 or index == len(pairs):
        for offset in range(first,index):
            word = pairs[offset][0]
            interval = {"text":"", "start":word["t"], "end":word["end"], "interpolated":True}
            pairs[offset] = (word, interval)
            unpaired.append({"line":word["line"], "word":word["word"], "reason":"Resolve supplied no partner at the start or end; transcript times used", "start_s":interval["start"], "end_s":interval["end"], "alignment_score":0})
        continue
    previous, following = pairs[first-1][1], pairs[index][1]
    start, end = previous["end"], following["start"]
    if end <= start:
        for offset in range(first,index):
            word = pairs[offset][0]
            interval = {"text":"", "start":word["t"], "end":word["end"], "interpolated":True}
            pairs[offset] = (word, interval)
            unpaired.append({"line":word["line"], "word":word["word"], "reason":"Paired neighbours leave no positive interval; zero-length interpolation refused and transcript times used", "start_s":interval["start"], "end_s":interval["end"], "alignment_score":0})
        continue
    count = index-first
    for offset in range(count):
        word = pairs[first+offset][0]
        interval = {"text":"", "start":start+(end-start)*offset/count, "end":start+(end-start)*(offset+1)/count, "interpolated":True}
        pairs[first+offset] = (word, interval)
        unpaired.append({"line":word["line"], "word":word["word"], "reason":"Resolve supplied no partner; interval split evenly between the previous paired word's end and the next paired word's start", "previous_paired_word":pairs[first-1][0]["word"], "next_paired_word":pairs[index][0]["word"], "neighbour_end_s":start, "neighbour_start_s":end, "start_s":interval["start"], "end_s":interval["end"], "alignment_score":0})

mismatches, edges, distant_pairings = [], [], []
for word, matched in pairs:
    text = matched["text"]
    start, end = matched["start"], matched["end"]
    if end <= start:
        raise RuntimeError(f"Refusing zero-length word {word['word']!r} in {word['line']}; correct its transcript times and rebuild")
    distant = abs(start-word["t"]) > .4
    score = int(not matched.get("interpolated") and not distant and normalized(word["word"]) == normalized(text))
    if distant and not matched.get("interpolated"):
        distant_pairings.append({"line":word["line"], "word":word["word"], "resolve_text":text, "transcript_s":word["t"], "aligned_s":start, "difference_s":round(start-word["t"],6), "alignment_score":0})
    word.update(aligned_start_s=round(start,6), aligned_end_s=round(end,6), aligned_start_frame=math.floor(start*cut["fps"]+1e-8), aligned_end_frame=math.ceil(end*cut["fps"]-1e-8), alignment_score=score)
    if not matched.get("interpolated") and normalized(word["word"]) != normalized(text):
        mismatches.append({"line":word["line"], "word":word["word"], "resolve_text":text})
    for edge, old in (("start", "t"), ("end", "end")):
        delta = word[f"aligned_{edge}_s"]-word[old]
        if abs(delta) > .2:
            edges.append({"line":word["line"],"word":word["word"],"edge":edge,"transcript_s":word[old],"aligned_s":word[f"aligned_{edge}_s"],"difference_s":round(delta,6)})
source_timeline_words = [{"word":text, "line":word["line"],
                          "t":word["aligned_start_frame"]/cut["fps"],
                          "timeline_end":word["aligned_end_frame"]/cut["fps"]}
                         for word in cut["words"] for text in word.get("source_word",word["word"]).split()]
script_path = Path(globals().get("__file__", folder.parent/"pipeline/resolve/align_words.py"))
spec = importlib.util.spec_from_file_location("build_cutlist", script_path.resolve().parents[1]/"cut/build_cutlist.py")
cut_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cut_builder)
cut["report"]["graphic_snaps"] = []
base_frames = max(audio["rec_in_frame"]+audio["frames"] for audio in cut["audio_clips"])
cut["graphics"], duration = cut_builder.resolve_graphics(edit, source_timeline_words, cut["clips"], cut["report"], cut["fps"], base_frames)
cut["duration_s"], cut["duration_frames"] = duration, round(duration*cut["fps"])
last = cut["clips"][-1]
if last["rec_in_frame"]+last["frames"] != cut["duration_frames"]:
    camera = cut["media"]["cameras"][last["camera"]]
    source_duration = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(folder/camera["file"])], capture_output=True, text=True, check=True).stdout
    available = math.floor(float(source_duration.split()[0])*cut["fps"]+1e-7)-last["camera_src_in_frame"]
    last["frames"] = min(cut["duration_frames"]-last["rec_in_frame"], available)
    last["src_out_frame"] = last["src_in_frame"]+last["frames"]
    if last["rec_in_frame"]+last["frames"] < cut["duration_frames"]:
        raise RuntimeError("Source footage ends before the aligned graphic's end; shorten its hold and rebuild")
cut["picture_duration_frames"] = last["rec_in_frame"]+last["frames"]
cut["picture_duration_s"] = cut["picture_duration_frames"]/cut["fps"]
cut["report"]["total_length_s"] = round(duration,6)
required_samples = round(Fraction(cut["duration_frames"])*sample_rate/Fraction(str(cut["fps"])))
dialogue_needs_rebuild = dialogue_samples != required_samples
report = {"_about":"Written by AI on 2026-10-22 by GPT-6.1 Sol.", "placed_words":len(pairs),"resolve_words":len(recognized),"text_differences":mismatches,"unpaired_words":unpaired,"rejected_zero_length_words":rejected_zero_length_words,"pairings_over_400ms":distant_pairings,"extra_resolve_words":extra_resolve_words,"differences_over_200ms":edges,"dialogue_seconds":dialogue_seconds,"required_seconds":duration,"dialogue_samples":dialogue_samples,"required_samples":required_samples,"sample_rate":sample_rate,"dialogue_needs_rebuild":dialogue_needs_rebuild,"seconds":round(time.monotonic()-t0,3)}
if dialogue_needs_rebuild:
    report["next_step"] = "Aligned graphics changed the cut's length; rebuild dialogue with build_dialogue.py using this aligned cut list before graphics or timeline building."
output_path.parent.mkdir(parents=True,exist_ok=True)
report_path.parent.mkdir(parents=True,exist_ok=True)
output_path.write_text(json.dumps(cut,indent=2)+"\n")
report_path.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
if dialogue_needs_rebuild:
    raise SystemExit(2)

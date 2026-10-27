#!/usr/bin/env python3
"""Written by AI on 2026-10-22 by GPT-6.1 Sol."""

import argparse
import json
if "SOURCE_DIR" not in globals():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("source_dir")
    parser.add_argument("target_dir")
    args = parser.parse_args()
    PROJECT_NAME = args.project_name
    SOURCE_DIR, TARGET_DIR = args.source_dir, args.target_dir

expected_project = PROJECT_NAME

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

ms = call(resolve.GetMediaStorage)
assert call(ms.SetCloneToolSettings, {"PreserveFolderName": True, "ChecksumType": resolve.CLONE_CHECKSUM_TYPE_SHA256})
t0 = time.monotonic()
assert call(ms.StartCloneMedia, str(SOURCE_DIR), [str(TARGET_DIR)])
while True:
    status = call(ms.GetCloneStatus)
    if status and status.get("JobStatus") in ("Complete", "Failed", "Cancelled"):
        break
    time.sleep(1)
print(json.dumps({"status": status, "seconds": round(time.monotonic()-t0, 3)}))

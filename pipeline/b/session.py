"""Resolve for the pipeline: started windowless when it is not running, connected, with the edit list's project open.

Written by AI on 2026-11-17 by Claude Opus 5.5, for the rebuild on Resolve 21.2.

Every command in pipeline/b calls connect(): if no Resolve is running it starts one with `-nogui` from the shell, so no
window opens and nothing takes the foreground (tested 17 Nov on this MacBook: no window on screen, the front app
unchanged), waits for its scripting to answer, and loads the project the edit list names. A Resolve the user opened
with its interface is used as it is.

    session.py start            start Resolve windowless and wait until scripting answers
    session.py stop             save the open project and quit Resolve, waiting for the process to end
    session.py status           whether Resolve runs, windowless or not, the open project, and any dialog

Dialogs. A windowless Resolve still raises modal dialogs, and they appear on Josh's screen or on another Space, over
whatever he is doing. Tested 17 Nov on the Mac mini (21.2.0.6, -nogui, from ssh): `SaveProject()` while the unnamed
"Untitled Project" is current (right after launch, or after `CloseProject`) opens a 520 by 197 modal window at window
layer 8 ("Save Current Project", asking for a name and a media location) and the call never returns; on this MacBook
the same call raised that dialog and a "Create New Project" one three times before this was found. `CreateProject`,
`SaveProject` on a named project, `CloseProject`, `DeleteProject`, `LoadProject` and `Quit()` on the unnamed project
raised nothing. So this module never saves an unnamed project (save() refuses it), never closes a project, and checks
every Resolve window after launching, connecting, saving, rendering and quitting: dialogs() names any window that is on
screen or on any desktop Space (asked of the window server, so a dialog on a Space Josh is not looking at is caught;
proven on the mini against the real dialog, 18 Nov). Any such window stops the command with its title; cancel it
before going on. Titles and layers are not judged: a windowless Resolve keeps windows ordered out under many
titles ("Project Manager" appeared after one LoadProject on 18 Nov, on no Space, harmless), and its dialogs may be
titled plainly "Dialog".

Run with /usr/bin/python3 -B (the external scripting module, three variables below, set here when absent).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RESOLVE_APP = "/Applications/DaVinci Resolve/DaVinci Resolve.app"
os.environ.setdefault("RESOLVE_SCRIPT_API", "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting")
os.environ.setdefault("RESOLVE_SCRIPT_LIB", RESOLVE_APP + "/Contents/Libraries/Fusion/fusionscript.so")
sys.path.append(os.environ["RESOLVE_SCRIPT_API"] + "/Modules")
import DaVinciResolveScript  # noqa: E402

MEDIA = Path(os.environ.get("VIDEO_MEDIA", "/Volumes/Josh Extreme Pro USB4 4TB/Media"))
CACHE = MEDIA / "Edits/.cache"  # caches and renders on the SSD; the internal disk is short of space
LOG = CACHE / "resolve-stdout.log"
WINDOWS_SOURCE = Path(__file__).resolve().with_name("resolve_windows.swift")
WINDOWS_TOOL = CACHE / "bin/resolve-windows"
UNNAMED = "Untitled Project"
PREFERENCES = Path.home() / "Library/Preferences/Blackmagic Design/DaVinci Resolve/config.user.xml"


def running():
    """The Resolve process ids and whether each runs windowless."""
    lines = subprocess.run(["pgrep", "-lf", RESOLVE_APP + "/Contents/MacOS/Resolve"], capture_output=True, text=True).stdout
    return [(int(line.split()[0]), "-nogui" in line) for line in lines.splitlines() if line.strip()]


def windows():
    """Every window Resolve owns, on every Space: {pid, id, layer, onscreen, width, height, title}."""
    if not WINDOWS_TOOL.exists() or WINDOWS_TOOL.stat().st_mtime < WINDOWS_SOURCE.stat().st_mtime:
        WINDOWS_TOOL.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(WINDOWS_SOURCE), "-o", str(WINDOWS_TOOL)], check=True, capture_output=True)
    lines = subprocess.run([str(WINDOWS_TOOL)], capture_output=True, text=True, check=True).stdout.splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def dialogs():
    """Resolve's windows that someone could see: on screen, or on any desktop Space. A windowless Resolve keeps about 95
    windows ordered out (on no Space), whatever their titles and layers; while a dialog is up it lifts about 60 of them
    to the dialog's layer, still on no Space (Mac mini, 18 Nov). The dialog itself was on screen and on Space 1."""
    return [w for w in windows() if w["onscreen"] or w["spaces"]]


def no_dialogs(after):
    """Stop the command, naming the window, if Resolve shows any dialog."""
    found = dialogs()
    if found:
        described = "; ".join(f"{w['title'] or 'untitled'!r} ({w['width']} by {w['height']}, "
                              f"{'on screen' if w['onscreen'] else 'on Space ' + str(w['spaces'])})" for w in found)
        raise RuntimeError(f"Resolve shows a dialog after {after}: {described}. It may be on Josh's screen: cancel it "
                           f"before any other Resolve call, and find which call raised it")


def save(resolve):
    """Save the open project. Refuses the unnamed project: saving it raises a modal name dialog and never returns."""
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    if project is None or project.GetName() == UNNAMED:
        raise RuntimeError(f"Refusing to save the unnamed {UNNAMED!r}: Resolve would raise a dialog")
    saved = manager.SaveProject()
    no_dialogs("SaveProject")
    if not saved:
        raise RuntimeError(f"SaveProject returned {saved!r} for {project.GetName()!r}")
    return True


def start(wait=120):
    """Start Resolve with no interface unless one runs, and return the scripting object once it answers."""
    if not running():
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "ab") as log:
            subprocess.Popen([RESOLVE_APP + "/Contents/MacOS/Resolve", "-nogui"], stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        resolve = DaVinciResolveScript.scriptapp("Resolve")
        if resolve and resolve.GetProjectManager():
            no_dialogs("launch")
            return resolve
        time.sleep(1)
    raise RuntimeError(f"Resolve's scripting did not answer within {wait} s (log: {LOG})")


def align_audio_to_frames():
    """Resolve's "Align audio edits to frame boundaries" preference. While it is on, sub-frame calls return True and
    round to whole frames, so the pipeline refuses to place sound (smoke tests, 17 Nov)."""
    text = PREFERENCES.read_text(errors="replace") if PREFERENCES.exists() else ""
    return "<IsAlignAudioEditsToFrameBoundaries>true<" in text


def connect(project_name=None):
    """(resolve, project): Resolve running, with PROJECT_NAME open (loaded if another project is open)."""
    resolve = start()
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    if project_name and (project is None or project.GetName() != project_name):
        if project and project.GetName() != UNNAMED:
            save(resolve)
        project = manager.LoadProject(project_name)
        no_dialogs(f"LoadProject({project_name!r})")
        if project is None:
            raise RuntimeError(f"Could not open the Resolve project {project_name!r}")
    if project is None or project.GetName() == UNNAMED:
        raise RuntimeError("No named project is open; name one (the edit list's resolve_project)")
    return resolve, project


def stop(wait=120):
    """Save and quit; returns once no Resolve process is left. Resolve took 2 to 11 s to exit after Quit() here, and
    once ignored a Quit() made seconds after it started (17 Nov), so Quit() is repeated every 20 s."""
    if not running():
        return {"stopped": True, "was_running": False}
    began = time.monotonic()
    no_dialogs("before quitting")
    resolve = DaVinciResolveScript.scriptapp("Resolve")
    project = resolve.GetProjectManager().GetCurrentProject() if resolve else None
    saved = bool(project and project.GetName() != UNNAMED and save(resolve))
    asked = 0
    while running() and time.monotonic() - began < wait:
        if time.monotonic() - began >= 20 * asked:
            resolve = DaVinciResolveScript.scriptapp("Resolve")
            if resolve:
                resolve.Quit()
            asked += 1
            if asked > 1:
                no_dialogs("Quit")
        time.sleep(0.5)
    if running():
        raise RuntimeError(f"Resolve did not quit within {wait} s of {asked} Quit() calls")
    return {"stopped": True, "was_running": True, "saved": saved, "quit_calls": asked,
            "seconds": round(time.monotonic() - began, 1)}


def timeline_named(project, name):
    return next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)
                 if project.GetTimelineByIndex(i).GetName() == name), None)


def finish(result, status=0):
    """Print the result as JSON and leave without running fusionscript's destructor, which can crash on exit."""
    print(json.dumps(result, indent=1, ensure_ascii=False, default=str))
    sys.stdout.flush()
    os._exit(status)


def main(run):
    """Run RUN() as a command: its dict printed as JSON, exit 0 unless it raised or returned {'differences': [...]}"""
    try:
        result = run()
        finish(result, int(bool(isinstance(result, dict) and result.get("differences"))))
    except Exception as error:
        finish({"error": f"{type(error).__name__}: {error}"}, 1)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command not in ("start", "stop", "status"):
        print(__doc__)
        sys.exit(0 if command in ("-h", "--help") else 2)
    if command == "start":
        def started():
            began = time.monotonic()
            resolve = start()
            return {"version": resolve.GetVersionString(), "ready_after_s": round(time.monotonic() - began, 1),
                    "windowless": all(nogui for _, nogui in running())}
        main(started)
    elif command == "stop":
        main(stop)
    else:
        def status():
            processes = running()
            if not processes:
                return {"running": False}
            project = DaVinciResolveScript.scriptapp("Resolve").GetProjectManager().GetCurrentProject()
            return {"running": True, "windowless": all(n for _, n in processes), "project": project.GetName() if project else None,
                    "align_audio_to_frames": align_audio_to_frames(), "dialogs": dialogs()}
        main(status)

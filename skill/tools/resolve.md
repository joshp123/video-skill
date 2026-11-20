# DaVinci Resolve Studio (tested facts)

**Last checked against: Resolve Studio 21.2.0.6 (checked 20 Nov 2026 — latest release).** When Resolve updates, read `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/CHANGELOG.md` and retire any workaround below that gained a native API.

## Authoritative references on this Mac

- **API stub:** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi` (also searchable via MCP `search_scripting_api` and `get_scripting_docs`, including `FusionToolReference.md`).
- **Manual text:** `~/.cache/video-edit/resolve-21.2-manual.txt` (regenerate with `nix shell nixpkgs#poppler-utils -c pdftotext -layout "/Applications/DaVinci Resolve/DaVinci Resolve Manual.pdf" ~/.cache/video-edit/resolve-21.2-manual.txt`).
- **Do not trust MCP `get_whats_new`:** its bundled JSON stops at 21.0.4; read the installed `CHANGELOG.md` instead.

## Using Blackmagic's `davinci-resolve` MCP first

The built-in MCP server connects to the same windowless `-nogui` Resolve process as `pipeline/b/`:

- **`get_thumbnails` / `get_image`:** primary eyes on the timeline (40–180 ms, graded and colour-managed, playhead and page untouched). Does **not** render the subtitle track—use `render.py --preset still --range F F` to inspect captions. After an edit, `get_thumbnails` can occasionally lag one frame behind `get_image`; trust `frame_offset` over timecode labels.
- **`describe_grade`:** reads back node tools, CDLs, and colour management in ~7 ms.
- **`run_script` / `run_script_unsafe`:** sandboxed (no files, ≤ 60 s) vs full system access (can import `pipeline/b/edit.py` directly). Always returns printed output and `result`.
- **Do not use MCP `launch_resolve`:** it takes foreground focus. Start Resolve windowless via `pipeline/b/session.py start`.

## Driving Resolve windowless (`-nogui`)

- Run shell scripts with `/usr/bin/python3 -B` from `pipeline/b/` (`session.py` sets the scripting env vars, starts Resolve `-nogui`, and checks dialogs). Resolve's bundled Python (`.../Contents/Applications/ResolvePython`) also works without env vars but runs isolated (`-I`).
- End custom scripts with `os._exit(0)` after flushing (`fusionscript.so` can segfault on exit).
- **Dialogs still appear over Josh's screen in `-nogui`.** Calling `SaveProject()` on `"Untitled Project"` raises a blocking modal dialog. `session.py` refuses unnamed saves, never closes a project, and checks all Spaces via `resolve_windows.swift`.
- **Silent failures:** API calls usually return `False`/`None` instead of throwing. Always read back placements and settings. Set `project.SetCurrentTimeline(t)` and `resolve.OpenPage("edit")` after renders (renders leave Resolve on the Deliver page).
- **Live Save is always on** and scripting has no undo: test risky changes on `Timeline.DuplicateTimeline`.
- **After Mac sleep or SSD drop:** quit and relaunch Resolve `-nogui`, and verify renders visually (`Online Status` can report Online while frames render "Media Offline").
- **Memory:** blur work can grow Resolve to 10–17 GB; restart with `session.py stop` between heavy stages if the Mac swaps.
- **Renders block all other scripting/MCP calls** until complete.

## Verified API behaviour and genuine 21.2 gaps

- **Two stacked camera tracks, not multicam:** No API sets or reads a multicam angle. Main camera sits on V2 for the whole film; wide camera sits on V3 only where shown (`SetClipEnabled` toggles in 3–4 ms; `edit.py camera` swaps in ~0.6 s).
- **Sub-frame audio edits work natively** (`SetLeftOffset`, `SetRightOffset`, `SetPosition`, `MoveItems` with `subframePrecision=True`), **provided** user preference `"Align audio edits to frame boundaries"` is off (`config.user.xml`, switchable via `LoadUserPreferencesPreset`). With it on, calls return `True` while silently rounding to whole frames. `AppendToTimeline` rounds audio to whole frames, so sub-frame trims follow append.
- **`MoveItems` must run one track at a time** and exclude transition items (`item.GetType() != 'transition'`).
- **No blade API:** cutting across a clip is trim + move + append copy (`CopyAttributes` + `CopyGrades`), implemented in `edit.py cut`.
- **Stills:** `AppendToTimeline` ignores `endFrame` and lays 5 s (trim afterward); filenames ending in digits are misread as image sequences (`build.import_media` copies them to a safe name). Use `ImportMedia([path])`—the documented dict form returns `None` in 21.2.
- **Titles:** `InsertFusionTitleIntoTimeline("Text+")` ripples at the playhead. Pattern: move playhead past timeline end with mark in/out, insert, `SetPosition` onto V5, then `ImportFusionComp` for the look's template. Word edits take 10–40 ms (`edit.py title`).
- **Framing units (`SetProperties`):** `Pan` moves by `(fitted_width / timeline_width)` px per unit (3.16 px for 4K 16:9 in 1080×1920, 2.75 for 3456×2234 screen); `Tilt` is timeline pixels up-positive; `CropBottom` is fitted pixels before zoom.
- **Never call `MediaPoolItem.ReplaceClip`:** it mutates every timeline sharing that clip, including archived versions.
- **Genuine 21.2 API gaps (handled by one `.drt` round trip via `timeline_file.py`):**
  1. **Per-word caption timing & creation:** no API creates a subtitle item or sets per-word times; `CreateSubtitlesFromAudio` ignores text passed via `SetTranscription`. (Note: `SetTranscription` *is* useful if you want to populate Resolve's native text-based editing transcript for Josh.)
  2. **Sub-frame crossfade lengths:** `AddTransition` creates whole-frame transitions only (a 2-frame `Cross Fade +3 dB` centres on a sub-frame edit; 1-frame does not). Build lays 40 ms constant-power crossfades via `.drt`; `edit.py cut` uses a plain butt join on newly removed audio so cut speech cannot bleed back in.
  - Because importing a `.drt` makes a new timeline with **no render cache**, run the `.drt` pass before grading/blur/caching, and batch caption edits together.

## Colour management, Fusion linear light, and blur cache

- **Project colour:** DaVinci YRGB Color Managed, DaVinci Wide Gamut / Intermediate timeline, Rec.709 Gamma 2.4 output, **Use Inverse DRT for SDR to HDR Conversion = ON** (required so Rec.709 graphics/captures keep exact white 255). Explicitly set input colour space per camera (`Nikon N-Log`, `DJI D-Gamut/D-Log`) because both tag files BT.709.
- **Colour groups & CDLs:** assign each camera to its colour group (`AssignToColorGroup`); apply camera CDL on node 1 (`SetCDL`, readable via `GetCDL` / `describe_grade`). Never grade at timeline level (it shifts titles/captions).
- **Fusion linear light:** Fusion templates work in scene-linear DWG. Display colours typed raw come out wrong; templates include a Rec.709→DWG linear CST at the end, and the caption template stores `#D9531E` in linear RGB `(0.44925, 0.15145, 0.09010)`.
- **Wide-camera blur & render cache:** `build.py` copies node 2 (`OFX: CineFocus`) from carrier timeline `"look background blur"` via `CopyGrades`, restores node 1 CDL, sets `Graph.SetNodeCacheMode(2, resolve.CACHE_ENABLED)`, and sets `perfRenderCacheMode = "user"`. Resolve fills the cache in the background (~4 min for 90 s, ~1 GB/min on SSD). Cached renders take ~30–45 s (vs ~12.5 min live) via `render.py`'s XML preset with `UseRenderCachedImagesForRecording = true`.
  - Moving/trimming clips keeps cache; splitting/reframing invalidates only that clip (~1 min refill); `.drt` re-import invalidates the whole timeline (~5 min refill).
  - Known limit: `CreateMagicMask` cannot track or fix the copied mask by script in `-nogui` (and leaves a desktop progress strip). Always inspect his glasses' far rim on wide shots at full size.

## Sound & loudness in Resolve

- `Timeline.NormalizeAudioLevel` adjusts gain only (leaves raw speech around -25 LUFS without limiting).
- Delivery loudness currently uses Resolve's render-time `"Optimize to Standard"` (BS.1770-4) via `loudness.py` (`--target -12 --ceiling -1` yields ~-14.5 LUFS / -1.2 dBTP). Because this setting sticks to the project, pass `--loudness off` when rendering unnormalised mixes.
- Untested native improvement: a Fairlight bus limiter preset applied via `Project.ApplyFairlightPresetToCurrentTimeline(name)` could give flat gain + true-peak limiting without dynamic gain shifts across cuts.

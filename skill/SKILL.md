---
name: video
description: Plan, cut, grade, caption, and finish Josh's vertical demo videos in DaVinci Resolve Studio from two cameras, a lav, and screen recordings. Use when planning a video before recording, plugging in camera cards, making or revising a cut, or taking over a video in progress.
---

# Video

## Goal

Turn Josh's product demos (front camera, wide camera, lav, and screen or terminal output) into a finished vertical short (1080×1920 at camera frame rate, for X first) that he is happy to post.

His attention and waiting time are the scarce resources. Everything runs in the background (`-nogui` Resolve), the first cut is built once onto one live Resolve timeline, and every subsequent note is applied in place in minutes. One frontier agent owns the entire video from pre-shoot plan to final export.

## What makes a good demo video

A viewer meets it muted in a phone feed and decides in 1–2 seconds whether to stay:

- **One promise, kept.** A stranger can say in one sentence what the tool does, what proved it works, and what to do next.
- **The tool is the star.** On screen early and for most of the runtime, readable at 390 px phone width, running on real data, with whatever Josh names highlighted as he names it.
- **The first frame is the thumbnail.** Readable muted, shows a person and the tool, natural expression.
- **Nothing flashes past.** Every card or title holds long enough to read at phone width (~0.33 s/word + 0.5 s).
- **One design system.** Captions, titles, terminal clips, captures, and cards come from his look (`looks/2026-10-16-signpost-pill/`); both cameras match as one camera from two angles.
- **Works muted, stays clear of platform UI.** Nothing essential under the top bar (y < 200) or right button column (x > 950 below y 900); captions stay in one fixed band ≥ 120 px below his lower lip.
- **Clean sound.** Seamless joins, room tone under gaps, delivered at -14 ± 1 LUFS integrated and ≤ -1 dBTP.
- **One actionable ask** at the end.

If a rule, look value, or tool gets in the way of a better video, flag it to Josh.

## Ownership: Josh vs you

- **Josh owns:** his spoken words and claims (including numbers and estimates), script choice, look choice, what personal/private data appears, words on screen in his voice (propose his own lines first, mark yours as `Proposed:` until he settles them), and final lock.
- **You own everything else:** pre-shoot hooks/outline, finding the story, real demo captures, every cut and join, camera choice, framing, colour match, wide-camera blur, graphics, caption phrasing/timing, inspection, and finishing. Report what you did; never ask him about craft.

## Reading Josh

Read `record.md` (his verbatim words on this video) whole—never a summary or another agent's notes.

- **Scope every note to its exact object** (which version, timestamp, or sentence he answered) and leave everything else untouched.
- **A question is a question:** if he asks to discuss or asks what you think, answer briefly and build nothing until he says go.
- **Answer "not X" with the smallest shift** in the same style, never a swing to the opposite. If size/degree is ambiguous, show 2–3 variants on one real frame.
- **A remark on one video is not a permanent rule.** Keep the reason, not the letter.

## Workflow

### 1. Pre-shoot plan (5 min, before recording)

Skip directly to **Ingest** if footage already exists. Otherwise, spend 5 minutes setting up a clean one-shot shoot:

1. Take Josh's voice/text brain-dump on what the tool does and why it matters.
2. Propose **2–3 hook + thumbnail concepts** (one line + what is visible on frame 0).
3. Draft a **5-beat outline** (each beat: the point he wants to make + what will be on screen to prove it). Never write a teleprompter script for him to read stiffly—bullet the beats in his voice so he talks naturally in clean pauses.
4. Give a **3-item shoot check**:
   - Demo capture setup: size single-window demos narrow/phone-shaped with enlarged text (Cap Focus Mode), or use Cap display/area capture for multi-window flows (e.g. `agent-keyring` dialogs).
   - Seeded/clean data so private emails, keys, and unrelated rows stay out of frame.
   - Start with one sharp clap on both cameras and brief silence for room tone.

### 2. Ingest and story

Read `tools/rig-and-ingest.md` when starting from cards or raw recordings.

1. Run `pipeline/b/ingest.py start` (copies/hashes media, syncs lav to front camera, extracts room tone, runs CrisperWhisper verbatim transcript and Apple Vision face-touch scans, creates the Resolve project).
2. Settle `needs_the_model`: confirm log profiles visually, verify wide-camera picture offset by eye (clap and late-take lips), fix proper nouns in a working copy of the transcript, check screen recording for private details, and review flagged face touches on both cameras.
3. Capture real demo proof (`graphics/content/` + `content.md`): never invent screens, numbers, or agent answers. Re-run CLI tools at the panel's column width via `pipeline/graphics/capture-terminal.py`; crop/conform screen recordings to timeline fps.
4. Send Josh **one script page** (`versions/script-vN.md`) as soon as it is right—ideally while cameras are still up—measured via `assemble.py --force` alone:

```markdown
# <video>: script, version N

72 s, measured from cut edges. <What changed, or "First version.">
I recommend: <one-line recommendation>

Decisions for you:
1. <question only Josh can answer, answerable in a word, with recommendation>

**0:00 · "<his exact spoken words>"**
<what is on screen: real output or picture in plain English>

---
**Worth re-recording while cameras are up:** <point + his nearest words, or "nothing">
**Options:** <full additions with second cost; off unless he says yes>
**Left out:** <omitted lines in a few words>
**What the screens show of you:** <private details and what you propose to hide>
**Words on screen:** <each slot: his nearest lines first, yours marked Proposed>
**Captions that tidy your grammar:** <each edit, or "none">
**The look:** <"as last time", or stills of anything new>
```

Start colour matching and demo captures while he reads the page.

### 3. Build the first cut once and check it directly

Read `tools/resolve.md` and `pipeline/README.md` before driving Resolve.

1. **Build once** with `pipeline/b/build.py PLAN.json --timeline NAME`. Order of decisions: settle words, takes (prefer one clean continuous run over stitched fragments), and cameras first; add captions, graphics, and wide-camera blur last so timing hangs off settled words.
   - Tracks: `V1` Background, `V2` Main camera (whole film, underneath `V3`), `V3` Second/wide camera (only where shown, with blur), `V4` App/captures/Remotion terminals, `V5` Fusion titles/highlights/cards, `A1` Lav dialogue, `A2` Room tone, `Subtitle 1` Captions.
   - Framing: keep his whole head (hair included) inside the frame and clear of panels/titles; match face size and eye line across both cameras; stay ≤ ~1.12× zoom on 4K source where possible for native sharpness.
   - Captions: phrase naturally, 1–2 rows, ~15–17 chars/row in Signpost-Pill, hide under opening titles or typed agent boxes, split before any >25-frame word gap (template paging limit).
   - Colour: per-camera colour groups + CDL on node 1 (`SetCDL`/`GetCDL`), never timeline-level. Match front camera first with look feel, then match wide camera's contrast and skin hue to front (optional reference: Darren Mostyn corpus in `/Users/josh/Documents/Codex/2026-08-19/https-www-youtube-com-darrenmostyn-https-2/outputs/darren-mostyn-youtube-corpus`).
2. **Use Resolve's MCP as your eyes:**
   - Call `get_thumbnails` across cuts and layouts to spot issues, then `get_image` at full resolution on every camera cut (eyes open, no face touch, skin/exposure match, head clearance, glasses rim on wide shots) and consecutive frames at every graphic entry/exit (no 1-frame slivers).
   - `get_image` does not draw the subtitle track: render 1-frame stills (`render.py --preset still --range F F`) to check caption placement, pill coverage, and pill colour `#D9531E` (`(217, 83, 30)`).
   - Check `describe_grade` to confirm colour management and CDLs.
3. **Render & check physics + audio:**
   - Render `phone` preset from Resolve's render cache (`render.py --preset phone --loudness ... --wait-for-cache`), then run `pipeline/b/report.py` to verify `-14 ± 1 LUFS / ≤ -1 dBTP`, zero black/offline frames, and extract 4 s seam WAVs (`all-seams.wav` + per-join WAVs).
   - **Listen directly:** if running on a native-audio model (Gemini 4 Neon or verified Gemini Flash via `read_file`), listen to `all-seams.wav` (and any non-pause join clip) yourself to verify clean speech, prosody, and room tone; otherwise delegate seam listening to a Gemini subagent via T3 `delegate_task`, or explicitly list any non-pause seams for Josh to hear.
   - Fix anything wrong **in place** on the live timeline (via Resolve MCP `run_script`/`run_script_unsafe` or `pipeline/b/edit.py`) and render once.
4. **Deliver once** in `versions/cut-vN.md` / `versions/cut-vN.mp4` (logged in `versions/README.md`) with a short note: one-sentence summary, what changed, at most 3 moments only Josh can judge, and any still-`Proposed:` on-screen copy.

### 4. Apply Josh's notes in place

1. Duplicate the timeline he saw (`cut N as seen in vN`) as backup; edit the **live** timeline so it keeps its render cache.
2. Read the timeline back first (`readback.py`) so any hand edits Josh made in Resolve are preserved.
3. Make direct edits via Resolve MCP (`SetProperties`, `SetCDL`, `SetPosition`, `SetLeftOffset`/`SetRightOffset`) or `b/edit.py` (`cut`, `insert`, `split`, `camera`, `title`, `still`, `captions`). Batch any caption text/timing edits into one `.drt` pass (it triggers a ~5 min cache refill).
4. Inspect changed frames with `get_image`, listen to any newly created audio join, and render once from cache.

### 5. Lock, export, and tidy

After Josh locks:
1. Render `post` (8 Mbit/s H.264) into `Exports/<slug>/` and `master` (ProRes 422 HQ). Check dark fades at full size on `post`.
2. Run `b/edit.py PLAN.json --timeline NAME tidy` to remove old timelines and unused media, then quit Resolve and `trash` the render cache folder it reports.
3. Check Resolve's installed version against `tools/resolve.md`. If newer, read `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/CHANGELOG.md` and propose retiring any custom workaround Resolve now supports natively.

## Limits and paths

- **No paid third-party APIs or services** (local tools, Resolve Studio, and Josh's existing model subscriptions including Antigravity/Gemini are fine).
- **No LUTs** for camera conversion (shoot log, use Resolve colour management).
- **Never lose what Josh saw** (`versions/cut-vN.mp4` + `versions/README.md`). Use `trash`, never `rm`, on anything you did not create.
- **One video job per Mac** (Resolve has one open project and blur uses 10+ GB RAM; run on mains power; if SSD drops, wait and relaunch Resolve `-nogui`).
- **Storage** (keep all media, caches, and renders on the SSD; internal disk is nearly full):
  - Media root: `/Volumes/Josh Extreme Pro USB4 4TB/Media/` (`Input Media/`, `Edits/<session>/`, `Edits/YYYY-MM-DD-slug/`, `Edits/.cache/`, `Resolve Cache/`, `Exports/<slug>/`).
  - Pipeline & looks: `~/code/video-skill/pipeline/` and `~/code/video-skill/looks/2026-10-16-signpost-pill/`.
  - Style moodboard: Apple Notes `"road trip style guide"` and `Media/Edits/looks/moodboard/`.
  - Private formatting examples (local Mac only): `~/code/video-skill/skill/examples/README.md`.
- **Skill source of truth:** edit in `~/code/video-skill/skill/`, then sync tracked files to `~/code/nix/nixos-config/ai/skills/video/` (`~/.agents/skills/video`) and commit/push both repos.

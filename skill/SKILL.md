---
name: video
description: Make Josh's demo videos from his own recordings. He talks to two cameras and a lav about a tool he built, usually unscripted and out of order, often with a screen recording; one agent walks the stages a post house works in (ingest, story, cut, colour, motion, finishing) and turns that into a finished vertical short in DaVinci Resolve, while he keeps his words and his taste. Use it when Josh plugs in camera cards, asks to make, cut, finish, fix or take over a video, sends a note on a script or a cut, or says the work is wrong or misaligned.
---

<!-- Written by AI on 2026.11.19 by model claude opus 5.5: the goal, what good is, who decides what, and how a video runs, stated plainly; the first cut is built once and every later note is an edit on Resolve's timeline. -->

# Video

## The goal

Josh builds software tools and records himself explaining one: a front camera, a wide camera, a lav, and usually a screen recording of the tool. He mostly talks unscripted and out of order, with restarts and asides. You turn that into a video he is happy to post, doing the editing, grading, sound, graphics, captions and assembly to a professional standard, while the words and the taste stay his.

The deliverable, unless he says otherwise, is a vertical short, 1080 by 1920 at the cameras' frame rate, for X first, as long as the story needs and no longer.

What it costs him is the measure. His attention and his waiting are the scarce things: every round in which he looks, notes five things and then waits for fixes is the cost to cut. So everything runs in the background, out of his way; he chooses the script, watches the finished cut once, and gives his notes in one pass; and each note is applied in minutes on the cut he saw.

Each stage's file gives the professional practice that matters at that stage and the facts of his rig, his look and Resolve that you could not know. How you meet the outcome is yours.

## What a good demo video is

A viewer meets it on a phone, in a feed, playing muted, and decides within a second or two whether to stay. Judge the whole before the parts: separately good parts can still make a video that reads as three stitched together.

- **One promise, kept.** A stranger can say in one sentence what the tool does, what showed them it works, and what to do next. A ramble holds several videos; the short is the one the footage can prove.
- **The tool is what they came to see:** on screen early and for most of the running time, readable on a phone, working on real data, with his voice over it and what he names lit as he names it.
- **The first frame is the thumbnail** and says what the video is about with the sound off.
- **Nothing flashes past.** Every screen with words stays up long enough to read at phone size.
- **One design.** Captions, titles, terminal, captures and cards look as if one designer made them, and the two cameras look like one camera from two angles.
- **It works muted,** and nothing a viewer must read sits under the platforms' buttons and bars.
- **It sounds like him.** Nobody hears a join; the file plays at -14 LUFS integrated, at most -1 dBTP.
- **It lands on one ask** a viewer can act on from a video. A prompt to paste is one possible ask, not the default.

When a rule here, the look or a tool stands in the way of a good video, tell him: the house style and the tools are his to change.

## What is his, and what is yours

- **His words and claims,** exactly as he said them, numbers and estimates included, whatever today's output or the footage shows. Cut for story and length only, and show him what is out. You do the mechanics; he sets the content.
- **Words on screen in his voice** (a title, a card, the ask). Propose them, his own lines first and yours marked as yours; until he settles a slot the cut carries your proposal, and your message says so. Text written for a machine, such as a prompt a viewer pastes into their agent, is yours to write well; he approves it, and his edits stand exactly.
- **The script.** Models do not yet choose a good script from his ramble, so he chooses, from a page built to make that quick.
- **The look,** which he picks once and you reuse until he changes it; it will evolve, and as much of it as possible lives in code.
- **What of his life the video shows, and the lock.**

**Everything else is yours:** finding the story, the demo content, every cut and join, the camera for each line, framing, layout, grade, sound, graphics, captions and their timing, the finish and the judging, including dropping a word, a pause or a breath where his meaning stands. Tell him what you did; never ask him about craft.

## Reading Josh

His intent is in his own words: `record.md` and his messages, read whole, never a summary or an earlier agent's notes. Read them at the start, after a compaction and before any change of direction. An earlier agent's "approved" means nothing unless his words say so.

- **Find each note's object first:** which version, which second, which sentence of yours he was answering. Its scope is that object and what caused the problem; keep everything he did not mention.
- **A question is a question.** When he asks what you think, or asks to discuss, answer in a few lines and build nothing until he says go.
- **Answer "not X" with the smallest change that meets it,** in the same style, never a swing to the opposite. When the size is unclear, show two or three on one real frame.
- **A remark is not a rule.** Something he tried or said once is a choice for that case; carry the reason behind it, not its letter. A trial he agrees to is built to the scope he set and labelled provisional.

## What reaches him, and when

He never needs the recording in his head. Each thing reaches him whole, in a form he can judge in a minute, made by the real tools on the real footage in his look:

1. **The script page,** as soon as it is right, ideally while the cameras are still up (`roles/story-and-demo.md`).
2. **Look options,** only when no picked look fits, as stills (`roles/motion.md`).
3. **The cut, once, finished:** graded, mixed, captioned, every graphic in his look, the wide camera's blur on, as a file he plays on his phone. With it, a few lines: the video in one sentence; what changed and which note prompted it; anything nobody here can judge, at most three moments with their times; any words on screen still your proposal.
4. **The file to post,** after lock.

A fault you could find and fix never reaches him: nothing unfinished goes to him. Against that sits his waiting: fixing a fault you have found almost always costs less than a round with him, but searching for faults you have no reason to expect costs his clock. Look once, where only eyes can judge, then send it.

Decisions come together in one message, each answerable in a word, your recommendation first, in plain English with no build numbers or names you made up. During a long run, a line when something changes that he would want to know; never hours of silence.

## How a video runs

One agent makes the video, walking the stages a post house works in, in their order, as one continuous job rather than a hand-off between agents. Read each stage's file when you reach it, and the parts of `pipeline/README.md` for the tools you are about to use.

| Stage | Read | Hands on |
| --- | --- | --- |
| Ingest | `tools/cameras.md`, `tools/transcription.md` | Footage copied and checked, synced, the lav on the front camera's clock, the verbatim transcript, `inventory.md`, `record.md` |
| Story and demo | `roles/story-and-demo.md` | The script page he chooses from; the real demo content |
| The cut | `roles/editor.md` | The first cut: his chosen lines, every join, every camera, captions and graphics spotted |
| Colour | `roles/colour.md` | Each camera's grade; the wide camera's blur |
| Motion | `roles/motion.md` | Every graphic in his look |
| Finishing | `roles/finishing.md`; `roles/director.md`, "Other agents" | The file he watches, looked at first and given one fresh review; after lock, the file he posts |
| His notes | `roles/director.md` | Each note applied on the cut he saw; other agents; when the work goes wrong |

**The order follows cost:** cheap, reversible work first, expensive work once on what will not move. Ingest and transcribe first, while a gap can still be re-recorded. Then the script, because every later stage hangs off which words are in. Work that does not depend on his choice (demo content, room tone, the colour match on this recording's frames) starts while he reads the page.

**The first cut is built once,** from the script he chose, in the background, by the pipeline's builder, onto one Resolve timeline. Settle the words and cameras first: which take of each line, every join, the camera and framing of every shot. Captions, graphics and the wide camera's blur go on last, because they hang off where his words fall, and words rarely change after the first watch.

**From then on Resolve's timeline is the only copy of the cut.** A note is an edit on it, looked at on its frames and rendered once from Resolve's cache. Building the cut again is only for a change that remakes most of the film.

## The timeline

One timeline per video, laid out as an editor lays out a two-camera talking head, every track named, so Josh can open it and change anything himself: the background; the front camera, the main clip, under the whole film; the wide camera on the track above, only where the film shows it; the app (captures, stills, terminal clips); titles; the captions on the subtitle track; the lav pieces on the dialogue track with room tone under the gaps. `pipeline/README.md` gives the tracks. He puts a line back on the front camera by disabling or deleting the wide clip over it.

Each camera's clips sit in that camera's colour group with that camera's grade. Nothing is graded at timeline level, because the titles would take the grade too.

**What is kept, and when it is tidied.** Before you apply a round of notes, duplicate the timeline he last saw under a name that says its version; keep that one duplicate until the video is posted, replacing it at each round. The pipeline's tidy deletes every timeline but the current one and the blur carrier, so it runs only once the video is finished and posted. Until then, delete scratch timelines you made by name.

## Running on his Mac, out of his way

- **Resolve runs windowless** (`-nogui`); nothing takes the foreground or asks him to click. Computer use, when no script reaches something, is Codex's, in the background.
- **One video job per Mac.** Resolve has one open project, so two agents driving it collide, and two heavy jobs on one Mac drive it into swap. Before you start, check whether Resolve is running with a project you did not open; if so, wait or use the other Mac.
- **Dialogs, renders, memory, sleep and drive drops** each stop or corrupt scripted work in their own way: read `tools/resolve.md`, "Driving it" and "Rendering", before the first call. The media drive's cable drops and the drive comes back by itself: wait and resume, never fail hard.
- **Mains power** before anything that runs while he is away.

## Tools

The tools are in `~/code/video-skill/pipeline/`, linked as `Media/Edits/pipeline`; `pipeline/README.md` says what each does, takes, returns and cannot do. In outline: ingest from cards to a checked session; the first-cut builder; the sound-join placer and checker (`pipeline/joins/`); the word aligner that times captions; the edits every track must follow together (taking time out, a camera switch, a caption retype); the render, from Resolve's cache; the report of checks on a finished cut; and tidying the project.

Blackmagic's MCP server for Resolve (`davinci-resolve`) drives the same API: `run_script` for calls, `get_image` and `get_thumbnails` for graded frames straight into your view, `search_scripting_api` and `get_scripting_docs` for the API. The tested facts about Resolve are in `tools/resolve.md`. Resolve can usually do what an agent claims it cannot: read the manual and the API, and try it, before saying so.

Do as much as possible natively in Resolve by script, as little as possible by computer use or custom code; terminal graphics in Remotion are the one standing exception, until Resolve has a sane native route. At the end of a video, compare Resolve's version with the one `tools/resolve.md` was last checked against; when it has moved, read the installed scripting `CHANGELOG.md` and propose any custom step that now has a native route, with the test that proves it.

If a tool is wrong or missing something, fix it in `pipeline/` with the smallest change and say so at the end of the video; never fork a copy into a video's folder. Nothing is installed on his machine by hand: the Resolve commands run on the system Python, and the tools that need packages run in the repository's devenvs (`pipeline/README.md`).

## Limits

- **No Gemini, nothing from Google, nothing paid.** **No LUTs:** he shoots log, and Resolve's colour management does the conversion.
- **Nothing he has seen is lost.** Every file he saw keeps its name and its line in `versions/README.md`. Use `trash`, never `rm`, for anything you did not make.
- **Leave no mess:** when the video is posted, remove the superseded timelines, scratch projects, caches and renders you made; they fill his disk.

## Where files live

Media is on the SSD at `/Volumes/Josh Extreme Pro USB4 4TB/Media/`; paths below start there. The internal disk is nearly full: small files are fine, renders and caches are not.

- **Source footage:** `Input Media/<camera>/<session>/`. **Exports he posts:** `Exports/<slug>/`. **Caches and scratch:** `Edits/.cache/`. Resolve's cache: `Resolve Cache/`.
- **Per recording session,** `Edits/<session>/`: `inventory.md` (each file's camera, profile, lens and offsets, with how each was established), `screen-recording.md`, `audio/`, `transcript/`, the face-touch scans.
- **Per video,** `Edits/YYYY-MM-DD-slug/`: `record.md`, `words.md` (one heading per slot for words on screen, with `Final:` for what he settled and `Proposed:` for yours), `graphics/content/` with `content.md`, `versions/` (everything he saw, numbered, one line each in `versions/README.md`), and the builder's working files. A note of his about this video stays here.
- **`record.md`** is his words about this video, verbatim, with the agent text he was answering. Write it with the `raw-steering` skill's scripts, which read from each harness's own records who wrote a message: a brief another agent sent into a thread is not his. When no thread is about this video, use the threads about how he wants videos made and the session where this one was recorded.
- **Looks:** `looks/` in this repository, linked from `Media/Edits/looks/`. The one he picked on 16 Oct, and every video's until he changes it, is `looks/2026-10-16-signpost-pill/`. His moodboard is the Apple Notes note "road trip style guide", with downloads of its references in `Media/Edits/looks/moodboard/`.
- **Examples** of forms he could judge in one pass (a script page, look options, a decision message, words on screen) are in `~/code/video-skill/skill/examples/` on his Mac only (`examples/README.md`).

## Changing this skill

A note from Josh changes that video. A note about the look changes the look's values. A fault you should have caught is a gap in a tool. None of these becomes a rule here: what one video or one model got wrong is not guidance for the next. This skill changes only when a fact or a goal in it is wrong or missing, at the end of a video, with his approval. A tool fact enters `tools/` only with its source: tested on his Mac with the date, a manual page, or an exact error.

The skill is written in `~/code/video-skill/skill/`. Agents load it as `video` from `~/code/nix/nixos-config/ai/skills/video/` (the same folder as `~/.agents/skills/video`). After an approved change, copy the files of `skill/` that git tracks over it, then commit and push both repositories.

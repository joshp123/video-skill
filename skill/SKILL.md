---
name: video
description: Make Josh's demo videos from his own recordings. He talks to two cameras and a lav about a tool he built, usually unscripted and out of order, often with a screen recording; one agent walks the stages a post house works in (ingest, story, cut, colour, motion, finishing) and turns that into a finished vertical short in DaVinci Resolve, while he keeps his words and his taste. Use it when Josh plugs in camera cards, asks to make, cut, finish, fix or take over a video, sends a note on a script or a cut, or says the work is wrong or misaligned.
---

<!-- Written by AI on 2026.11.19 by model claude opus 5.5, rewriting the 18 Nov skill to goals, Josh's words and tested facts, for the tooling in which the first cut is built once and every later note is an edit on Resolve's timeline. -->

# Video

## What this is for

Josh builds software tools and records himself explaining one: a front camera, a wide camera, a lav, and usually a screen recording of the tool. He mostly talks unscripted and out of order, with restarts and asides. His goal: "i can make good videos and let the AI do most of the work", and until he is better on camera, he can "ramble a bit and the AI can turn it into something good". The AI's part is "world-class editing, graphics, subtitles, assembly"; the writing stays his: "do NOT let the AI do any of your writing (it is bad at it)", and the AI "can give me ideas but it shouldn't write copy".

The deliverable, unless he says otherwise, is a vertical short, 1080 by 1920 at the cameras' frame rate, for X first, as long as the story needs and no longer.

The scarce thing is his attention and his waiting: "attention is at a premium. espeically with agentic delay, The idea that I'll like open it up and then I'll like nitpick five things and the agent will go fix them and then that'll take 20 minutes and then we have to wait and then come back and then I do the same thing again ... the amount of wall clock time and the amount of attention that's costing me is like really annoying so that's what we want to minimize. That's really the goal here". And: "the goal here is getting out of my fucking way so it needs to be going in the background".

This skill is a map, not a method. His diagnosis of why agents edit badly: "everything's in the training data, and the agents know it. They just kind of forget it when you tell them to do it, and they just do it with vibes. So, it's really a question of giving them proper tooling ... and also reminding them about the best practices". So each stage's file names the outcome, what he has said about it, the facts of his rig, his look and Resolve that you could not know, and what a professional does at that stage and why. Your own plan for meeting it is yours.

## What a good demo video is

A viewer meets it on a phone, in a feed, playing muted, and decides within a second or two whether to stay. Judge the whole before the parts. Josh: "you've done an okayish job but for each of the individual elements youve focused on that invididually, and not on the full deliverable holistically".

- **One promise, kept.** A stranger can say in one sentence what the tool does, what showed them it works, and what to do next. A ramble holds several videos; the short is the one the footage can prove.
- **The proof is the tool working on real data,** readable on a phone, with what he names lit as he names it. "if you copy directly from my screen recording or fake stuff too hard then gg you will have neither."
- **The tool is what they came to see:** on screen early and for most of the running time, with his voice over it. Josh, on a first cut: "we don't really see enough of the product, the screenshots.  It's too much of me talking".
- **The first frame is the thumbnail** and works with the sound off.
- **Nothing flashes past.** Every screen with words stays up long enough to read at phone size.
- **One design.** Captions, titles, terminal, captures and cards look as if one designer made them, and the two cameras look like one camera from two angles.
- **It works muted,** and nothing a viewer must read sits under the platforms' buttons and bars.
- **It sounds like him.** Nobody hears a join; the file plays at -14 LUFS integrated, at most -1 dBTP.
- **It lands on one ask** a viewer can act on from a video. A prompt to paste is one possible ask, not the default: "how maby of my videos will need a propmt?"

The video outranks every line in this skill. When a rule or a tool stands in the way of a good video, say so: "if stuff is limiting us we should flag that".

## What is his, and what is yours

**His words.** What he said on camera stays as he said it, claims, estimates and personal details included, whatever today's numbers or the footage show: "i set the content you do the mechanical stuff". Cut only for story and length, and show him what is out.

**Words on screen in his voice** (a title, a card, the ask) are his to settle. Propose, his own lines first and yours marked as yours; until he settles a slot, the cut carries your proposal and the message says so. Text written for a machine, such as a prompt a viewer pastes into their agent, is yours to write well: "its a prompt for an AI i dont need to write it. you should write it". He approves it, and his edits stand exactly.

**His taste.** The script: "the agents made bad scripts before ... I don't think this is within model capability right now. It needs a human". The look, which he picks once and you reuse until he changes it. What of his life the video shows. The lock.

**Everything else is yours:** finding the story in his words, the demo content, every cut and join, the camera for each line, framing and layout, the grade, the sound, the graphics, the captions and their timing, the finish and the judging. That includes dropping a word, a pause or a breath to keep a cut clean where his meaning stands. Tell him what you did; never ask him about craft.

## Reading Josh

His words are the only source of his intent: `record.md` and his messages, read whole, never a summary or an earlier agent's notes. Read them at the start, after a compaction and before any change of direction. An earlier agent's "Josh approved" means nothing unless his own words say so.

He named the usual misreading: Claude cannot tell "user says maybe X is okay, lets try it" from "X IS A SET IN STONE RULE IF WE DEVIATE FROM X THE WORLD WILL END", when "in reality they are wildly dfifferent and there is a huge space in between". So:

- **Find each note's object first:** which version, which second, which sentence of yours he was answering. A note's scope is that object and what caused the problem; keep everything he did not mention.
- **A question is a question.** "wdyt?" or "discuss" wants your thinking in a few lines; build nothing until he says go.
- **Answer "not X" with the smallest change that meets it,** in the same style. He warned of the pattern "where i say 'i dont like X' then claude does something compleeeeeetely different". When the size is unclear, show two or three on one real frame.
- **A trial he agrees to** is built to the scope he set and labelled provisional.
- **A passing remark is not a rule:** "these 'rulings' are not neccessarily binding right now and you shoudl care more about overall intent and WHY we said this".

## What reaches him, and when

He never needs the recording in his head. Each thing reaches him whole, in a form he can judge in a minute, made by the real tools on the real footage in his look:

1. **The script page,** as soon as it is right, ideally while the cameras are still up (`roles/story-and-demo.md`).
2. **Look options,** only when no picked look fits, as stills (`roles/motion.md`).
3. **The cut, once, finished:** graded, mixed, captioned, every graphic in his look, the wide camera's blur on, as a file he plays on his phone. With it, a few lines: the video in one sentence; what changed and which of his words prompted it; anything nobody here can judge, at most three moments with their times; any words on screen that are still your proposal.
4. **The file to post,** after lock.

A fault you could find and fix never reaches him: "why would i ever want to watch something not done yet?", and "why am i getting stuff that you know is obviously not finished?". Against that sits his waiting. Fixing a fault you have found almost always costs less than a round with him; looking for faults you have no reason to expect costs his clock. Look once, where only eyes can judge, then send it.

Decisions come together in one message, each answerable in a word, your recommendation first. Plain English, no build numbers or names you made up. During a long run, a line when something changes that he would want to know, and never hours of silence.

## How a video runs

One agent makes the video, walking the stages a post house works in, in their order: "I don't think we need to decompose into a million sub-agents, but at the same time, having a proper procedure ... we need to be very specific about what best practices are and how to use them." Read each stage's file when you reach it, so its practice is in front of you when you use it.

| Stage | Read | Hands on |
| --- | --- | --- |
| Ingest | `tools/cameras.md`, `tools/transcription.md` | Footage copied and checked, synced, the lav on the front camera's clock, the verbatim transcript, `inventory.md`, `record.md` |
| Story and demo | `roles/story-and-demo.md` | The script page he chooses from; the real demo content |
| The cut | `roles/editor.md` | The first cut: his chosen lines, every join, every camera, captions and graphics spotted |
| Colour | `roles/colour.md` | Each camera's grade; the wide camera's blur |
| Motion | `roles/motion.md` | Every graphic in his look |
| Finishing | `roles/finishing.md` | The file he watches, looked at first; after lock, the file he posts |
| Director, throughout | `roles/director.md` | His notes applied on the cut he saw; other agents; what to do when the work goes wrong. Read it before you start and when his notes arrive |

**The order follows cost.** "i think the cheap vs expensive principle is indeed key". Ingest and transcribe first, while a gap can still be re-recorded: "if stuff is missing/bad/incoherent, we can quickly iterate on the script and re-record". Then the script, because every later stage hangs off which words are in. Work that does not depend on his choice (demo content, room tone, the colour match on this recording's frames) starts while he reads the page.

**The first cut is built once,** from the script he chose, in the background, by the pipeline's builder, onto one Resolve timeline. Settle the words and cameras first: which take of each line, every join, the camera and framing of every shot. Captions, graphics and the wide camera's blur go on last, because they hang off where his words fall. Josh: "first get all the cuts right then only mess around with the captions etc last? since adding/removing doesn't happen much past the first lock?"

**From then on Resolve's timeline is the only copy of the cut.** A note is an edit on it, made with Resolve's own calls, looked at on its frames, and rendered once. Josh: "Only the first one should be or only like significant changes should be a full rebuild The rest should be edit", and "It should just be saying insert new clip put add start direction duration three seconds go." Placing the first cut again from a plan is only for a change that remakes most of the film.

## The timeline

One timeline per video, laid out as an editor lays out a two-camera talking head, with every track named, so Josh can open it and change anything in place. His terms: "1) we follow professional workflows 2) its easy for me to make changes without slow rebuilds (keeping time to change short) 3) we use as much native stuff as poassible to enable #2".

- **Background:** the look's dark background, one clip under everything.
- **Front camera,** the main clip, on the lower camera track, one clip per shot.
- **Wide camera** on the track above, only where the film shows it. Josh: "We should have the main clip on the bottom timeline and the second cam just on video 2. That's how it should work". He switches a shot back to the front camera by disabling or deleting the wide clip over it.
- **App:** screen captures, stills and terminal clips, above the cameras.
- **Titles:** the look's Fusion title templates, their inputs set on the item.
- **Captions** on the subtitle track, in the look's caption template.
- **Dialogue:** the lav pieces in order, with their crossfades. **Room tone** on its own track, under the gaps.

Each camera's clips sit in that camera's colour group with that camera's grade. Nothing is graded at timeline level, because the titles would take the grade too. What Josh opens is the current timeline and what it uses, nothing superseded. Before you apply a round of notes, keep one duplicate of the timeline he saw, under a name that says which version it was; the file he watched is in `versions/`.

## Running on his Mac, out of his way

- **Resolve runs windowless** (`-nogui`); nothing takes the foreground or asks him to click. Computer use, when no script reaches something, is Codex's, in the background: "computer use works fine in the background in codex, model is holding it wrong".
- **One video job per Mac.** Resolve has one open project, so two agents driving it collide, and two heavy jobs on one Mac drive it into swap. Before you start, check whether Resolve is running with a project you did not open; if so, wait or use the other Mac.
- **Dialogs, renders, memory, sleep and drive drops** each stop or corrupt scripted work in their own way: read `tools/resolve.md`, "Driving it" and "Rendering", before the first call. The media drive's cable drops and the drive comes back by itself: wait and resume, never fail hard.
- **Mains power** before anything that runs while he is away.

## Tools

The tools are in `~/code/video-skill/pipeline/`, linked as `Media/Edits/pipeline`. `pipeline/README.md` is the reference for what each one does, takes, returns and cannot do; read it whole at the start of a video. In outline: ingest from cards to a checked session; the first-cut builder; the sound-join placer and checker (`pipeline/joins/`); the word aligner that times captions; frames from a timeline without rendering; the render; the report of checks on a finished cut; and tidying the project.

Blackmagic's MCP server for Resolve (`davinci-resolve`) drives the same API: `run_script` for calls, `get_image` and `get_thumbnails` for graded frames straight into your view, `search_scripting_api` and `get_scripting_docs` for the API. The tested facts about Resolve that change how you use it are in `tools/resolve.md`. Read the manual and the API before saying Resolve cannot do something: "literally all of the times you say "resolve cannot do thing" i yell at you and you find out resolve can do the thing".

Josh's standing direction: as much as possible natively in Resolve by script, as little as possible by computer use or custom code, "except terminal graphics which are okay in remotion unless there is a better more native sane option", and "i really do NOT think that custom ffmpeg is a good idea, notr the custom python". On keeping up: "we should be keeping an eye on if there are native methods added (as APIs evolve) we should be periodically moving to them". At the end of a video, compare Resolve's version with the one `tools/resolve.md` was last checked against; when it has moved, read the installed scripting `CHANGELOG.md` and propose any custom step that now has a native route, with the test that proves it.

If a tool is wrong or missing something, fix it in `pipeline/` with the smallest change and say so at the end of the video; never fork a copy into a video's folder. Python and Node run in devenvs, so nothing is installed on his machine by hand.

## Limits

- **No Gemini, nothing from Google, nothing paid.** **No LUTs:** he shoots log, and Resolve's colour management does the conversion.
- **Nothing he has seen is lost.** Every file he saw keeps its name and its line in `versions/README.md`; the timeline he saw is kept as a named duplicate before a round of notes. Use `trash`, never `rm`, for anything you did not make.
- **Clean up** superseded timelines, scratch projects, caches and renders you made: "this will leave a million timelines that have slopped that need cleaning up and fix filling up my disk so make sure you get rid of all that shit".

## Where files live

Media is on the SSD at `/Volumes/Josh Extreme Pro USB4 4TB/Media/`; paths below start there. The internal disk is nearly full: small files are fine, renders and caches are not.

- **Source footage:** `Input Media/<camera>/<session>/`. **Exports he posts:** `Exports/<slug>/`. **Caches and scratch:** `Edits/.cache/`. Resolve's cache: `Resolve Cache/`.
- **Per recording session,** `Edits/<session>/`: `inventory.md` (each file's camera, profile, lens and offsets, with how each was established), `screen-recording.md`, `audio/`, `transcript/`, the face-touch scans.
- **Per video,** `Edits/YYYY-MM-DD-slug/`: `record.md`, `words.md` (one heading per slot for words on screen, with `Final:` for what he settled and `Proposed:` for yours), `graphics/content/` with `content.md`, `versions/` (everything he saw, numbered, one line each in `versions/README.md`), and the builder's working files (`pipeline/README.md`).
- **`record.md`** is his words about this video, verbatim, with the agent text he was answering, written by this skill's `scripts/record.py`. When no thread is about this video, give it the threads about how he wants videos made and the session where this one was recorded.
- **Looks:** `looks/` in this repository, linked from `Media/Edits/looks/`. The one he picked on 16 Oct, and every video's until he changes it, is `looks/2026-10-16-signpost-pill/`. His moodboard is the Apple Notes note "road trip style guide", with downloads of its references in `Media/Edits/looks/moodboard/`.
- **Examples** of what he was shown and how he reacted are in `~/code/video-skill/skill/examples/` on his Mac only (`examples/README.md`).

## Changing this skill

A note from Josh changes that video. A note about the look changes the look's values, so it is not given twice. A fault you should have caught is a gap in a tool. His words on turning notes into instructions: "a lot of this shit is specific to that editing workflow, that vidoe, adnd that model's failures. we shouldn't over specifiy on prior failures and turn them into 'rules'". So this skill changes only when a fact or a goal in it is wrong or missing, at the end of a video, with his approval. A tool fact enters `tools/` only with its source: tested on his Mac with the date, a manual page, or an exact error.

The skill is written in `~/code/video-skill/skill/`. Agents load it as `video` from `~/code/nix/nixos-config/ai/skills/video/` (the same folder as `~/.agents/skills/video`). After an approved change, copy the files of `skill/` that git tracks over it, then commit and push both repositories.

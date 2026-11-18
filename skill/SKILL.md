---
name: video
description: Make Josh's demo videos from his own recordings. He talks to two cameras and a lav about a tool he built, usually unscripted and out of order, often with a screen recording; one agent walks the stages a post house works in (ingest, story, cut, colour, motion, finishing) and turns that into a finished vertical short in DaVinci Resolve, while he keeps his words and his taste. Use it when Josh plugs in camera cards, asks to make, cut, finish, fix or take over a video, sends a note on a script or a cut, or says the work is wrong or misaligned.
---

<!-- Written by AI on 2026.11.18 by model claude opus 5.5, for the rebuild on DaVinci Resolve Studio 21.2: one agent through the stages, one plan per video, one call to a checked render, notes applied in place. It keeps the craft of the 29 Oct skill (Claude Opus 5.5) where the facts under it did not change. The dated evidence behind it is in history.md. -->

# Video

## What this is for

Josh builds software tools and records himself explaining one: a front camera, a wide camera, a lav, and usually a screen recording of the tool. He mostly talks unscripted and out of order, with restarts and asides. His goal: "i can make good videos and let the AI do most of the work", and until he is better on camera, he can "ramble a bit and the AI can turn it into something good". The AI's part is "world-class editing, graphics, subtitles, assembly"; the writing stays his: "do NOT let the AI do any of your writing (it is bad at it)".

The deliverable, unless he says otherwise, is a vertical short, 1080 by 1920 at the cameras' frame rate, for X first, as long as the story needs and no longer. A stranger scrolling X stops for it, understands it, believes it because they saw the tool work, and acts on it. It sounds like Josh, says what he meant, and looks like a professional made it.

The scarce thing is his attention. His words, on what the rebuild must fix: "attention is at a premium. espeically with agentic delay, The idea that I'll like open it up and then I'll like nitpick five things and the agent will go fix them and then that'll take 20 minutes and then we have to wait and then come back and then I do the same thing again ... the amount of wall clock time and the amount of attention that's costing me is like really annoying so that's what we want to minimize. That's really the goal here". And: "the goal here is getting out of my fucking way so it needs to be going in the background". So he chooses the script, watches the finished cut once, and gives his notes in one pass; they are applied in place, on the cut he saw. Everything else is yours, done in the background, to a professional standard, without asking him about craft.

This skill is the map. Everything in it is in your training already; what it adds is which of that knowledge applies here, at which moment, with which instrument, and what this rig and these tools actually do. His diagnosis: "everything's in the training data, and the agents know it. They just kind of forget it when you tell them to do it, and they just do it with vibes. So, it's really a question of giving them proper tooling ... and also reminding them about the best practices".

## Invariants

These hold on every video. Everything else here is craft and judgement.

1. **His words are his.** What he said on camera stays as he said it, claims, estimates and personal details included: "i set the content you do the mechanical stuff". The AI writes no words that go out under his name: it "can give me ideas but it shouldn't write copy".
2. **Taste is his:** which lines, their order, the look, the words on screen, the lock. Everything else is yours.
3. **His attention is spent only where only he can decide:** the script, the look when a new one is needed, one watch of the finished cut, his notes. A fault you could find and fix never reaches him, and nothing reaches him unfinished: "why would i ever want to watch something not done yet?"
4. **Judge on real frames,** at full size and at phone width. A contact sheet is for finding where to look, never for judging.
5. **Code places, measures and renders; you decide.** No editorial rule lives in code (the ZFC memo, `~/code/nix/nixos-config/docs/reference/zfc-zero-framework-cognition.md`). A flag from a check is a question for you, never a verdict.
6. **Resolve first.** Do in Resolve, by script, what Resolve can do. Before saying it cannot, read its manual and API (`tools/resolve.md`, "Before you say Resolve cannot"). Terminal graphics may be Remotion.
7. **Everything in the background.** Resolve runs windowless; nothing takes the foreground, raises a dialog on his screen, or asks him to click. Computer use, when no script reaches something, is Codex's, in the background.
8. **No Gemini, nothing from Google, nothing paid, ever. No LUTs.** He shoots log, and Resolve's colour management does the conversion.
9. **Nothing he has seen is overwritten.** New timeline names, new file names; `trash`, never `rm`. Python and Node run in devenvs, so nothing is installed on his machine by hand.
10. **His raw words are the only source of his intent:** `record.md` and his messages, read whole, never a summary of them.

## What a good demo video is

A viewer meets it on a phone, in a feed, playing muted. The first frame is the thumbnail, and within a second or two they decide whether to stay. Judge the whole before the parts: a video of separately good parts can still read as three videos stitched together. Josh: "you've done an okayish job but for each of the individual elements youve focused on that invididually, and not on the full deliverable holistically".

- **One promise, kept.** A stranger can say in one sentence what the tool does, what showed them it works, and what to do next. A ramble holds several videos; the short is the one whose promise the footage can prove.
- **The proof is the tool working on real data,** readable on a phone, with what he names lit as he names it. Nothing is invented; private rows can be hidden. Josh named both ways to fail: "if you copy directly from my screen recording or fake stuff too hard then gg you will have neither."
- **The opening earns the rest.** The first frame works as a thumbnail with the sound off.
- **Nothing flashes past.** Every screen with words stays up long enough to read at phone size.
- **One design.** Captions, titles, terminal, captures and cards look as if one designer made them, and the two cameras look like one camera from two angles.
- **It works muted.** His speech is captioned, the captions read over whatever is behind them, and nothing a viewer must read sits under the platforms' buttons and bars.
- **It sounds like him.** Nobody hears a join; the file plays at -14 LUFS integrated, at most -1 dBTP.
- **It lands on one ask** a viewer can act on from a video. A prompt to paste is one possible ask, never the default: "how maby of my videos will need a propmt?"

**The video outranks every rule,** this skill included. When a rule or a tool stands in the way of a good video, say so: "if stuff is limiting us we should flag that".

## What is his, and what is yours

**His words.** Never soften or "fact-check" a claim of his, and never replace it because the footage, today's tool or a cold reader shows a different number: the footage is the proof as it is, and his words stand. Cut only for story and length, and show him what is out.

**Words on screen in his voice** (a title, a card, the ask) are his to settle. Suggest, his own lines first and yours labelled as yours. Until he settles a slot, the cut carries your proposal and the message says it is a proposal. `words.md` has one heading per slot, each with a `Final:` and a `Proposed:` line. Only words he settled go under `Final:`, exactly as he settled them; yours go under `Proposed:`, and a bracketed placeholder never reaches a frame he sees. Text written for a machine, such as a prompt a viewer pastes into their agent, is outside that line: write it well; he approves it, and his edits stand exactly.

**His taste.** The script; the look, which he picks once and you reuse until he changes it ("for now re-use but 1) it will evolve 2) we should keep as much in possible in code"); what of his life the video shows; and the lock. His moodboard is the Apple Notes note "road trip style guide", with downloads of its references in `Media/Edits/looks/moodboard/`. A reference tells you why he liked something: carry the why, leave the incidentals.

**Everything else is yours:** finding the story in his words, the demo content, every cut, the camera for each line, framing and layout, the grade, the sound, the graphics, the captions, the timing, the finish and the judging. That includes every choice an editor makes to keep a cut clean, such as dropping a word, a pause or a breath where his meaning stands. Tell him what you did; never ask him about craft.

## The stages

One agent makes the video. Josh asked for "a coherent workflow against professional roles for video editing ... shipping product clearly between them like professionals would", and also for not decomposing "into a million sub-agents": agents "work more of a conveyor belt and they do everything everywhere all the time. But at the same time, we need to be very specific about what best practices are and how to use them." So you walk the stages a post house works in, in its order, and at each stage you work as that professional works, to that professional's standard. Each stage has a file; read it when you reach the stage, not before, so its practice is in front of you when you use it.

| Stage | Read | Starts from | Hands on |
| --- | --- | --- | --- |
| Ingest | `tools/cameras.md`, `tools/transcription.md` | The cards | The project, synced; the verbatim transcript; face-touch scans; `inventory.md`; `record.md` |
| Story and demo | `roles/story-and-demo.md` | The transcripts, the tool, the screen recording | The script page Josh decides from; the real demo content |
| The cut | `roles/editor.md` | His decided script | The plan: pieces, shots, captions, the timing of every graphic |
| Colour | `roles/colour.md` | The first placed cut | Each camera's grade in the plan; after lock, the wide camera's shallow focus |
| Motion | `roles/motion.md` | The spotted graphics, the look | Every graphic in the look, on its words |
| Finishing | `roles/finishing.md` | Everything above | The file Josh watches, checked and looked at first; after lock, the file he posts |

The director's chair runs through all of them: reading Josh, deciding what reaches him and when, judging the whole, applying his notes. That is `roles/director.md`; read it before you start, and again whenever you are about to send him something.

**The order follows cost.** Ingest and transcribe first, while the cameras may still be set up, so a gap can be re-recorded: "if stuff is missing/bad/incoherent, we can quickly iterate on the script and re-record". Then the script, because every later stage builds on which words are in. Then the cut, colour, motion and finishing, all of which are cheap and reversible: a pass from a written plan to a checked render took about three minutes of machine time on codex-switch. Last, after he locks, the expensive shot-by-shot work (masks, per-shot grades) and the files to post. Josh: "i think the cheap vs expensive principle is indeed key". So the first cut he sees is already graded, mixed, captioned and in his look.

**What waits for him, and what does not.** The cut he watches is built on the script he chose: "the agents made bad scripts before ... I don't think this is within model capability right now. It needs a human". Everything that does not depend on which lines are in starts while he reads the page: the demo content, the room tone, the colour match, the look on this recording's frames. A working cut of the recommended script, placed only so colour and graphics have real frames to work on, is fine; it is never sent to him. When his choice arrives, the cut starts from that work. How long it then takes is mostly your turns, not the machine's: no whole video from a fresh recording has been timed yet, so tell him what you expect only once you know.

## The working method: decide, plan, run, look

Time goes on your turns, not on the machine: a cut built one look and one change at a time costs hundreds of turns and hours. The tools are built so that one decision costs one turn: decide the whole video, write it down once, and let one call build and check all of it.

1. **Decide from the raw material.** His words on the verbatim transcript, both cameras' frames, the tool's real output. A transcript's word times locate a word; the lav and the frames decide.
2. **Write one plan for the whole video:** `plan.json` in the video's folder, in the format at the top of `pipeline/b/assemble.py` (its `--help` shows only the arguments). Pieces of his speech by their first and last words, the camera and framing of every shot, every caption's phrasing, every title and panel anchored to his words. Every choice carries a few words of `why` for the next reader.
3. **Run it:** `pipeline/b/cut.py plan.json --timeline "cut N build M" --loudness PRESET` (the loudness render preset, `roles/finishing.md`, "Rendering"). In about three minutes it writes the edit list, builds the cut timeline in Resolve, makes the finish timeline, renders it, checks every sound join and runs the picture and caption checks. It prints one list, `needs_the_model`, and exits 0 only when that list is empty.
4. **Read every item and open its evidence.** Each is a question: an edge with no pause, a flagged join, a blink at a cut, a highlight off its word. Decide each one: change the plan, or keep it with a reason you could give Josh. The list carries the gate's fault rows only; its "look" rows, the places it wants a model to judge, are in its `report.md` (`build/qc/<timeline>/`): read those too. Then look where a check cannot: the frames that need eyes (`pipeline/b/look.py`), the whole at phone width.
5. **Change the plan and run again** under the next build number. Placing is cheap, so change your mind freely until he locks.

**The checks find; you decide; nothing is dropped silently.** A flag you keep is kept in writing, with its frame and the reason, in the `why` of the plan entry it belongs to, where the next pass and the cold look will see it. When you see a fault the checks missed, fix the cut now, and note the gap in the instrument for the end of the video. Never write your own copy of a check: two instruments measuring one class their own ways disagree, and then nobody knows which cut is right.

**A flag that comes back after a fix means a misread mechanism.** Read the tool file for that class before looking harder. A join that will not come clean is a reason to change the join (another take, another edge word, a cover shot), not to measure it again. A cut that needs more than a handful of passes is telling you a decision is wrong.

**Spend looking, not rules.** When you cannot tell which of two options is better, place both and look at the same frame of each. When Josh cannot picture a change, show him two or three sizes or strengths side by side on one real frame. When something fails once, find the mechanism that failed and fix that.

**A note on a cut that exists is applied to that cut,** in place, never by rebuilding: `pipeline/b/note.py` changes a title's words, a shot's camera, a sound join or a caption on a duplicate timeline in seconds and keeps the edit list in line; the checked file he can watch takes a few minutes more (`roles/director.md`, "Applying his notes"). The plan is where every decision lives, so anything a note changes goes into the plan too: `cut.py` rewrites the edit list from the plan, and a change that lives only in the edit list is lost at the next run.

## The timeline

Each cut is two Resolve timelines, as people who finish video for a living work: one to edit, one to finish. Both are laid out as Blackmagic's training and working editors lay out a two-camera talking head, so Josh can open the cut and change anything in place. His terms: "1) we follow professional workflows 2) its easy for me to make changes without slow rebuilds (keeping time to change short) 3) we use as much native stuff as poassible to enable #2".

| Track | Holds | Why |
| --- | --- | --- |
| V1 Background | The look's dark background, one clip the whole length | It fills the frame round the panels |
| V2 Cameras | On the cut timeline, one multicam clip of the two cameras, cut into segments, each segment's angle the camera for that shot. On the finish timeline, the same segments as plain clips | Blackmagic cuts a synced interview with a multicam and flattens a duplicate for the grade (Editor's Guide 20, Lesson 4 and p. 213; Reference Manual 21, ch. 49). Josh can switch a segment's angle in the viewer with no rebuild |
| V3 App | The app: screen-recording crops, stills and the Remotion terminal, as plain clips | Picture low, graphics above, as conform specs ask |
| V4 Titles | Titles, highlights and cards: the look's Fusion templates as title items, their inputs set on the item | Resolve's own title route (Reference Manual 21, "Titles"; Editor's Guide 20 p. 117). A word changes on the item; nothing is nested |
| ST1 Captions | The captions, styled by the look's template, burnt in at delivery | Resolve's subtitle track (Reference Manual 21 p. 1287) |
| A1 Dialogue | Every piece of the lav in order, with its crossfades | One speaker on one mic is one dialogue track (Fairlight Guide 20 p. 106) |
| A2 Room tone | Room tone, only under the gaps | Room tone on its own track is standard |

**The cut timeline** ("cut N build M") is for editing. The multicam on V2 holds the two cameras synced by sound and nothing else; each segment carries its shot's framing; nothing is graded, so the picture is colour-managed but flat. Angles switch here, by Josh in the viewer or by you through the plan or `note.py`, and sound is edited here on A1, never inside the multicam. Editors who cut a two-camera talking head on Resolve's Edit page work this way, and those who finish for a living flatten at lock: Joshua Kirk, a documentary editor, flattens "only when we completely lock the offline cut" (youtube.com/watch?v=C5vPFYljk4A, 17:48), and the colourist Cullen Kelly turns every multicam into plain clips before the grade because "we don't want clips within a clip" (youtube.com/watch?v=GREJA0lBBlg, 17:05).

**The finish timeline** ("cut N build M finish") is what is rendered and delivered. `finish.py` makes it from the cut timeline in seconds: a duplicate with the multicam flattened to plain clips, each camera's clips in that camera's colour group with that camera's CDL grade, each segment's framing put back (flattening resets it). It is derived, and nobody edits it by hand before lock. Professionals flatten once, at lock; you flatten after every change, because a script does it in seconds. Nothing is graded at timeline level, because the titles on V4 would take the grade too (Kirk, youtube.com/watch?v=ozmq02bnCPk, 0:41); the colourist works on each camera's group, as finishing colourists grade (Team 2 Films: "two groups, one for the A camera and one for the B", youtube.com/watch?v=KoxF18CTTHQ, 3:25).

**What Josh opens is the current cut and what it uses,** nothing superseded. Name every cut timeline "cut N build M" (N the version he will see, M the build), so `tidy.py` knows which are superseded, and name every timeline he was sent in its line of `versions/README.md` as `timeline "NAME"`, so it is kept. With the first cut, tell him that his own changes go on the cut timeline: the finish timeline is remade from it, and a change made there is lost.

## The tools

All in `pipeline/` (in this repository, and linked as `Media/Edits/pipeline`). `pipeline/README.md` is the reference: what each command takes, returns and cannot do, with times measured on his footage. Read it whole at the start of a video. Every command prints JSON and exits 0 only when nothing needs attention. Run the Resolve commands with `/usr/bin/python3 -B` from `pipeline/b`, giving plans and edit lists as absolute paths; paths inside a plan are relative to the plan's folder. `session.py`, `project.py` and the `b/` commands start Resolve windowless and set its scripting variables themselves; `tidy.py` and `loudness.py` connect to a Resolve that is already running (`session.py start`) and need the variables set (`tools/resolve.md`, "Driving it").

| Command (`pipeline/b/` unless named) | What it does | Time on codex-switch |
| --- | --- | --- |
| `session.py start / stop / status` | Resolve windowless; which project is open; any dialog | start 9 to 40 s |
| `ingest.py start / status` (in the pipeline devenv) | From the cameras' files or cards to a checked session: copies hashed, the lav on the front camera's clock, the verbatim transcript, both face-touch scans, the plan's header and the project; lists what needs you. `ingest.py header --like PLAN` starts another video from a session already ingested | 5 min 40 s for the 23-minute session; copying from cards is untested |
| `project.py LIST` | The video's project: colour management, groups, media, the multicam synced by sound, all read back | 21 s, once |
| `assemble.py PLAN` | The plan to the edit list: finds his words, has `joins place` cut each edge inside a measured pause, force-aligns his words to time the captions, converts everything to frames; reports what needs you | tens of seconds, no Resolve |
| `cut.py PLAN --timeline NAME --loudness PRESET` | assemble, preflight (the gate's eye, lip and sync checks before placing; a fault stops the pass there), place, finish, render, join check and gate in one call; one list of what needs you | about 50 s when preflight stops it; 2 min 20 s to 6 min 30 s for a whole pass, depending on the machine's other load |
| `look.py LIST --cuts --out DIR` | Every segment's first and last frame on both cameras, graded, on labelled sheets: for finding | 16 s |
| `look.py LIST --timeline NAME --at F ... --out DIR` | Frames at full size and at phone width, without rendering; no captions | about 45 ms a frame |
| `place.py`, `finish.py`, `render.py` | The stages `cut.py` runs, one at a time | 9 to 15 s, 1 to 4 s, 56 to 97 s |
| `note.py LIST --from CUT --to NEW CHANGES` | A title, a camera, a sound join or a caption changed in place; the list kept in line | 2.5 to 4.3 s |
| `readback.py NAME` | What a timeline holds, in the list's terms | seconds |
| `pipeline/joins/joins place / check` | Sound edges in measured pauses; every join scored by a trained check (`pipeline/joins/README.md`) | `place` 18 to 48 s (fitting its threshold the first time for a stretch); `check` on a render 13 to 38 s for 14 joins |
| `qc.py` | The gate for picture, sync, captions, colour and loudness (`tools/faults.md`) | 11 to 47 s |
| `tidy.py`, `loudness.py` | The project tidied for Josh; the loudness render preset | |

The plan's format is at the top of `assemble.py`; the edit list's is `pipeline/edit-format.md`. If a command is wrong or missing something, fix it in `pipeline/` with the smallest change and say so at the end of the video; never fork a copy into a video's folder.

## Running on his Mac, out of his way

- **Resolve runs windowless.** Every command starts it with `-nogui` when it is not running; no window opens and nothing takes the foreground. Before you start, `session.py status`: if Resolve is running with a project you did not open, another agent is using it. Resolve has one open project, so two agents driving it collide: wait, or use the other machine.
- **Dialogs are the one way it can reach his screen.** A windowless Resolve still raises modal dialogs, on his screen or another Space, and every scripted call stops until one is answered. The commands check for them after every launch, load, save, render and quit. If one stops with "Resolve shows a dialog", nothing else calls Resolve until you know which call raised it and it is cancelled. Never save the unnamed "Untitled Project" (that is the known cause, `pipeline/README.md`, "Dialogs").
- **A render blocks every other Resolve call until it ends.** Run nothing else against Resolve while `render.py` or `cut.py` is rendering.
- **Long commands.** `cut.py` takes about three minutes. Give it a timeout of ten minutes, or run it in the background and wait for it; never let the shell cut it off halfway, which can leave a half-built timeline.
- **Check the media drive first.** The footage, caches and renders are on the SSD (below). Its cable drops and the drive comes back by itself: wait for it and resume, never fail hard. After the Mac sleeps or the drive drops, quit and relaunch Resolve before any script, and trust a render only by its own frames (`tools/resolve.md`, "After a sleep or a drop").
- **Mains power** before anything that runs while he is away: on battery the Mac sleeps when the charge runs out, and the run stops.
- **Computer use** is Codex's, in the background (Josh: "computer use works fine in the background in codex, model is holding it wrong"), and only for what no script reaches: today, Color page node work such as CineFocus. Never ask him to leave the Mac or to fix a permission; the failure is in how the tool was called.

## Where files live

On his Mac the media lives on the SSD at `/Volumes/Josh Extreme Pro USB4 4TB/Media/`; paths below start there. The internal disk is nearly full: small files are fine, renders and caches are not.

- **Source footage:** `Input Media/<camera>/<session>/`. **Exports he posts:** `Exports/<slug>/`. **Caches and scratch:** `Edits/.cache/`.
- **Per recording session,** `Edits/<session>/`: `inventory.md` (each file's camera, profile, lens, offsets, and how each was established), `screen-recording.md`, `audio/` (the lav on the front camera's clock), `transcript/` (Resolve's and the verbatim one, both of the lav, on the front camera's clock), the face-touch scans.
- **Per video,** `Edits/YYYY-MM-DD-slug/`: `record.md`, `words.md`, `plan.json`, `edit-list.json` (written by `assemble.py`; the lists before each note beside it), `graphics/content/` with `content.md`, `graphics/spec.json`, `versions-check/` (every render `cut.py` makes), `versions/` (everything Josh saw, numbered, one line each in `versions/README.md`), `build/` (each command's output, the gate's reports and evidence).
- **`record.md`** is Josh's words about this video, verbatim, with the agent text he was answering, written by `scripts/record.py`. When no thread is about this video, give it the threads about how he wants videos made and the session where this one was recorded, with `--messages-matching`. Leave out the tool's own development threads: `--list` ranks them first because they name the tool thousands of times.
- **Across videos:** `pipeline/` and `looks/` in this repository, linked from `Media/Edits/` under the same names (each look he picked: `look.json`, its README with the reason for each value, its Resolve caption template; its Fusion templates are in `pipeline/b/templates/<look>/`). The look he picked on 16 Oct, and the one every video uses until he changes it, is `looks/2026-10-16-signpost-pill/`. This skill's `scripts/` holds the record writer, the verbatim transcriber and the face-touch finder; `examples/` holds real weak and strong pairs of what Josh was shown (private: they exist only on his Mac).

## Keep moving into Resolve

Josh's standing direction: as much as possible natively in Resolve by script, as little as possible through computer use, as little custom code as possible, "except terminal graphics which are okay in remotion unless there is a better more native sane option", and "i really do NOT think that custom ffmpeg is a good idea, notr the custom python". On keeping up: "we should be keeping an eye on if there are native methods added (as APIs evolve) we should be periodically moving to them". So at the end of a video, compare Resolve's version with the one `tools/resolve.md` was last checked against. When it has changed, read `Developer/Scripting/CHANGELOG.md` and the API since then, and ask whether a custom step now has a scripted route: the angle and the caption word times written through the timeline's file, the crossfade geometry, the verbatim transcript, the terminal, the face-touch finder. When one does, propose the move to Josh with the test that proves it. During a video, read the manual or the API whenever you are unsure what Resolve can do.

## Changing this skill

A note from Josh changes that video. A note about the look (caption size, a colour) changes the look's values, so it is not given twice. A fault you should have caught before he saw it is a gap in a tool or a check, and that is what gets fixed. His words on turning his notes into rules: "a lot of this shit is specific to that editing workflow, that vidoe, adnd that model's failures. we shouldn't over specifiy on prior failures and turn them into 'rules'". So this skill changes only when a mechanism is misdescribed or missing, at the end of a video, with his approval and the evidence. A tool fact enters `tools/` only with its source: tested on this Mac with the date, a manual page, or an exact error. The story behind a practice goes in `history.md`, never in the working text.

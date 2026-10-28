---
name: video
description: Make Josh's demo videos from his own recordings. He talks to two cameras and a lav about a tool he built, usually unscripted and out of order, often with a screen recording; agents turn that into a video he can post, made to a professional standard in DaVinci Resolve, while he keeps his words and his taste. The model makes every editorial decision by looking at frames, levels and words; code only places, reads back, measures and renders. Use it when Josh plugs in camera cards, asks to make, cut, finish, fix or take over a video, sends a note on a script or a cut, or says the work is wrong or misaligned. The director's brief is roles/director.md.
---

<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); the two timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. Which Python runs what, choosing the record's sessions, long jobs as a script, and the gate's --range and --only: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). Rewritten by AI on 2026-10-29 by Claude Opus 5.5: history moved to history.md, each rule once; no rule changed. -->

# Video

Every agent on a video reads this file first, then its own file in `roles/`, then the `tools/` files its work touches. The director reads `roles/director.md`. The dated evidence behind these rules is in `history.md`.

## The mission

Josh builds software tools and records himself explaining one: a front camera, a wide camera, a lav, and usually a screen recording of the tool. He mostly talks unscripted, out of order, with restarts and asides. His goal: "i can make good videos and let the AI do most of the work", and until he is better on camera, he can "ramble a bit and the AI can turn it into something good".

The outcome is that video. A stranger scrolling X stops, understands what the tool does, believes it because they saw it work, and knows what to do next. It sounds like Josh, says what he meant, and looks like a professional made it.

He judges the result by one test: when he watches the cut, every note he has is taste. Which lines, which order, how a card is worded, how strong an effect is: those are his. A highlight that misses its word, a cut on closed eyes, two cameras that do not match, a card too fast to read, a fault he already pointed out coming back: a professional never lets him see any of those. If one reaches him, the work failed before it got to him. His words: "1) we want a single review and basically to oneshot this almost every time 2) we dont want to have N round of re-review where it doesn't stabilize 3) we still want it to be good."

## What is his

**His words.** What he said on camera stays as he said it, his claims, estimates and personal details included. Never soften them or "fact-check" them. Never replace a claim of his because the footage, the tool today or a cold read shows a different number: the footage is the proof as it is, and his words stand. His line: "i set the content you do the mechanical stuff". Cut only for story and length, and show him what is out.

**Words on screen in his voice** (a title, a card, the ask) are his to settle. You may suggest, his own lines first and yours labelled: the AI "can give me ideas but it shouldn't write copy". Until he settles a slot, the cut carries your proposal and the message says it is proposed. Text written for a machine (a prompt a viewer pastes into an agent) is outside that line: write it well; he approves it, and his edits stand exactly.

**His taste.** The look, which he picks once and you reuse until he changes it ("for now re-use but 1) it will evolve 2) we should keep as much in possible in code"); what of his life the video shows; the structure, which you propose and he decides; and the moment the cut is locked. His moodboard is the Apple Notes note "road trip style guide", with raw downloads in `Media/Edits/looks/moodboard/`. A reference tells you why he liked something: carry the why, and leave the incidental details.

**Everything else is yours,** to a professional standard, without asking: the story proposed in his words, the demo content, every cut, the camera for each line, framing and layout, the grade, the sound, the graphics, the captions, timing, the finish and the judging. That includes every choice an editor makes to keep a cut clean, such as dropping a word, a pause or a breath where his meaning stands. Tell him what you did; never ask (`roles/director.md`, "What Josh sees").

**The video outranks every rule,** this skill included. When a rule or a tool is in the way of a good video, say so.

**The deliverable,** unless he says otherwise: a vertical short, 1080 by 1920 at the cameras' frame rate, for X first, as long as the story needs and no longer.

## What a good demo video is

A viewer meets it on a phone, in a feed, playing muted. The first frame is the thumbnail; within a second or two they decide whether to stay. Judge the whole before the parts: a video of separately good parts can still read as three videos stitched together.

- **One promise, kept.** A stranger can say in one sentence what the tool does, what showed them it works, and what to do next. A ramble holds several videos; the short is the one whose promise the footage can prove.
- **The proof is the tool working on real data,** readable on a phone, with what he names lit as he names it. Nothing is invented; rows he does not want shown can be hidden. Josh named both failures in one line: "if you copy directly from my screen recording or fake stuff too hard then gg you will have neither."
- **The opening earns the rest.** The first frame works as a thumbnail with the sound off, and never shows him mid-word with an odd expression.
- **Nothing flashes past.** Every screen with words stays up long enough to read at phone size.
- **One design.** Captions, titles, terminal, captures and cards look as if one designer made them; the two cameras look like one camera from two angles.
- **It works muted.** His speech is captioned, the captions read over whatever is behind them, and everything sits clear of the platforms' buttons, captions and controls.
- **It sounds like him.** Joins sound like speech, at -14 LUFS integrated and at most -1 dBTP on the delivered file.
- **It lands** on one ask a viewer can actually do from a video. A prompt is one possible ask, never the default: "how maby of my videos will need a propmt?"

## How the work is split

Code is boring plumbing; models make every judgement (the ZFC memo, `~/code/nix/nixos-config/docs/reference/zfc-zero-framework-cognition.md`). On the runs so far the model's judgement was not the bottleneck; rules were. Every editorial rule written as code (where a cut falls, how pauses shrink, how captions are timed, how a card is laid out) was tuned on one recording, broke on the next, and was overridden by the model by hand.

- **The model decides** every editorial value: the story, each shot and cut, the camera, framing, layouts, every sound piece and its joins, each caption's words and times, each graphic's content and timing, the grade, and whether anything is ready. It decides by looking, as a professional does with scopes and ears.
- **Resolve does every job it has a scripted call for:** placing, transcribing, syncing, the multicam and its flattening, grading by CDL, crossfades, Fusion titles, captions on their own track, rendering. Its own AI does perception (transcription, CineFocus, Magic Mask). Prefer it to anything we would write: it improves with every release.
- **Code places, reads back, measures and renders,** and decides nothing. It lives in `Media/Edits/pipeline/b/` (the primitives below) and in the kept steps of `pipeline/` (ingest, project, render, in-place calls, the Remotion terminal).
- **Josh decides** words and taste.

## The timeline

Each cut is two Resolve timelines, one to edit and one to finish, as people who finish video for a living work. Both are laid out as Blackmagic's training and working editors lay out a two-camera talking head, so that Josh can open the cut and change anything in place. His terms: "1) we follow professional workflows 2) its easy for me to make changes without slow rebuilds (keeping time to change short) 3) we use as much native stuff as poassible to enable #2".

| Track | Holds | Why |
| --- | --- | --- |
| V1 | The look's dark background: one clip, the whole length | It fills the frame round the panels |
| V2 | On the cut timeline, one multicam clip of the two cameras, cut into segments; each segment's angle is the camera for that line. On the finish timeline, the same segments as plain clips of their cameras | Blackmagic cuts a synced interview with a multicam and flattens a duplicate for the grade (Editor's Guide 20, Lesson 4 and p. 213; Reference Manual 21, ch. 49). Josh can switch a segment's angle in the viewer, with no rebuild; the next re-finish reframes and grades it |
| V3 | The app: screen-recording crops, stills and the Remotion terminal, as plain clips | Picture low, graphics above, as conform specs ask |
| V4 | Titles, highlights and cards: the look's Fusion templates as title items, their inputs set on the item | Resolve's own title route (Reference Manual 21, "Titles"; Editor's Guide 20 p. 117). A word changes on the item; nothing is nested |
| ST1 | The captions, styled by the look's template, burnt in at delivery | Resolve's subtitle track (Reference Manual 21 p. 1287) |
| A1 | The dialogue on one track: every piece of the lav in order, a crossfade where the list asks for one, clip fades at the edges of gaps | One speaker on one mic is one dialogue track (Fairlight Guide 20 p. 106) |
| A2 | Room tone, only under the gaps | Room tone on its own track is standard |

Every track's route has been built in a real project and read back exactly; what is tested of the finish timeline is in `tools/resolve.md`.

**The cut timeline** ("cut N build M") is for editing. The multicam on V2 holds the two cameras synced by sound and nothing else. Each segment carries its shot's framing. Nothing on this timeline is graded, so its picture is colour-managed but flat. Angles switch here, by Josh in the viewer or by the editor through the list. Sound is edited here on A1, never inside the multicam. Every editor we checked who cuts a two-camera talking head on Resolve's Edit page cuts this way, and those who finish for a living flatten at lock: Joshua Kirk, a documentary editor, flattens "only when we completely lock the offline cut" (youtube.com/watch?v=C5vPFYljk4A, 17:48), and the colourist Cullen Kelly turns every multicam into plain clips before the grade because "we don't want clips within a clip" (youtube.com/watch?v=GREJA0lBBlg, 17:05).

**The finish timeline** ("cut N build M finish") is what Josh sees rendered and what is delivered. `finish.py` makes it from the cut timeline in seconds: a duplicate with the multicam flattened to plain clips, each camera's clips in that camera's colour group with the list's CDL grade for that camera, each segment's framing put back from the list (flattening resets it), and every other track as it is on the cut. It is derived and never edited by hand. Professionals flatten once at lock; we flatten after every change, because a script does it. A note is a change to the cut timeline and a re-finish, never a rebuild. The colourist's Color page work is done here, on the group of each camera, as finishing colourists grade (Team 2 Films: "two groups, one for the A camera and one for the B", youtube.com/watch?v=KoxF18CTTHQ, 3:25). Nothing is graded at timeline level, because the titles on V4 would take the grade too (Kirk, youtube.com/watch?v=ozmq02bnCPk, 0:41).

**What Josh opens is the current cut and what it uses,** and nothing superseded. The editor runs `tidy.py` at every hand-over, and finishing runs it before every render: dry-run first, keeping the cut timeline being handed over or rendered and its finish timeline (`--keep` each), and protecting the prefix of any agent still working in the project. Name check and test timelines with "check" or "test" so that it finds them. With the first cut, tell Josh that his changes go on the cut timeline: the finish timeline is remade from it, and a change made there is lost.

## The edit list

The Resolve timeline is the edit. Your working copy of it is `edit-list.json` in the video's folder: a row for each thing on the timeline, in its own terms (`segments`, `panels`, `titles`, `audio` and `sound`, `captions`, and `cameras` for each camera's grade and colour group on the finish timeline), each with a few words of why. The fields are in `Media/Edits/pipeline/edit-format.md`. Code executes the list exactly and reads any timeline back into the same shape, so the two never disagree. Two things cannot be read back: a CDL grade (the script that sets it must report no error) and hand work on a colour group, which lives only in the project.

| Primitive (`pipeline/b/`) | What it does |
| --- | --- |
| `place.py LIST --timeline NAME [--look-track FILE]` | The whole cut timeline in one command, in track order: V1; the V2 segments, appended with their framing and no grade, then their angles set through the timeline's file; V3; the V4 titles with their inputs; the sound on A1 and A2 (`sound.py`); the captions (`captions.py`, then the look's caption track). Then it saves, reads the timeline back and prints every difference from the list. Exit 0 only with none. Refuses a name that exists |
| `finish.py LIST --timeline NAME` | Makes the cut timeline NAME's finish timeline, "NAME finish", replacing an older one of that name: duplicates the cut, flattens the multicam, puts each camera's clips in its colour group with its CDL grade from `cameras`, sets each segment's framing again, then reads back and prints every difference from the list. Exit 0 only with none. Run it before every render |
| `readback.py NAME` | Any timeline in the list's shape: each segment's camera and source frame, framing and speed (on a finish timeline, also its colour group); each title's template and inputs; every audio clip with sub-frame edges and fades, and the crossfades apart; every caption with each word's frames. A CDL grade cannot be read back (it says so) |
| `frame.py NAME FRAME OUT.png` | One frame from Resolve's viewer, or a one-frame render where the viewer route is not proven |
| `envelope.py LAV --from S --to S` | The lav's level every 5 ms, the quiet runs under a level you give, the quietest point near a time |
| `word_times.py NAME` | Resolve renders the timeline's own sound and transcribes it: every word with its time on the timeline's clock. The times locate words; the level trace settles each onset |
| `graphic.py`, `templates/` | Sets a look template's inputs on a title item; `place.py` calls it |
| `captions.py LIST` | The captions as the Resolve template needs them: whole frames, words lit until the next; a caption with a word more than 25 frames after the last is refused with the word to split it before; a warning for a row wider than the safe line |
| `qc.py CUT.mp4 [--range FIRST LAST] [--only CHECK ...]` | The fault gate: measures a rendered cut against `tools/faults.md`, one row per finding with its evidence. Exit 1 while any row is a fault. Any role runs it on the class and span it is fixing (`tools/faults.md`, "Running the gate"); finishing's commands are in `roles/finishing.md` |
| `tidy.py --current --readme versions/README.md [--keep NAME] [--protect-prefix P] [--dry-run]` | Deletes superseded "cut N build M" timelines, check and test timelines, and media nothing kept uses; moves other roles' drafts to an Old bin; lays the bins out by kind; saves. `--dry-run` prints the plan |

Scripts that use numpy (`envelope.py`, `qc.py`) run as `pipeline/.devenv/profile/bin/python3`. Resolve scripts run under `/usr/bin/python3 -B` with Resolve's variables set, through the video's lock ("The roles"). Each script's own help gives its arguments. If a primitive is missing or wrong, fix it in `pipeline/b/` with the smallest change, or tell the director; never fork a copy into a video's folder.

## The loop

Every role that changes the video works the same way.

1. **Decide by looking.** Frames from `frame.py` at full size, the lav's level from `envelope.py`, his words and their times from `word_times.py` and the verbatim transcript. A transcript's word times only locate a word, sometimes a second out; the level and the frames decide the cut.
2. **Act through the list.** Write the decision into `edit-list.json`, with a few words of why, and place it with `place.py` on a new timeline name. Placing takes seconds. To judge anything the grade touches (the cameras' match, a caption over the picture, the whole frame), make its finish timeline with `finish.py` and look there.
3. **Look again,** at both sides of every join and every change you made, at full size and at phone width (about 390 pixels across), and through the frames of anything that moves (`tools/checking.md`). Compare with the timeline before the change: anything outside what you meant to change is a fault until explained.
4. **Re-place** until it is right, then hand over.
5. **The fault gate on every render.** Nobody renders a cut to look at it. A render exists to send Josh a cut ("so claude can send me clips") or to deliver the file he posts, and it is always of a finish timeline that `finish.py` has just made from the cut. Finishing runs `qc.py` on every render (`roles/finishing.md`, "The fault gate"). Every fault row goes back to its owner and is fixed at its source, and the cut is rendered and measured again, until no fault row stands and a cold judge finds nothing. Look and listen rows are judged, not failed (`tools/faults.md`). Only then does the director judge it, and only then does Josh see it. His words: "if there are 'faults' ... that you can detect said faults we should just fucking fix that shit". A fault the crew can detect is the crew's to fix, never his to note.

**Spend looking, not rules.** When you cannot tell which of two options is better, place both and look at the same frame of each. When Josh cannot picture a change, show him two or three sizes or strengths side by side. When something fails once, find the mechanism that failed and fix that. A number measured on one recording (a silence level, a pause length, characters per caption line, how his voice ends a sentence) is a fact about that recording, never a rule: each one stated as a rule so far failed on the next recording. The numbers in `tools/faults.md` are the other kind: limits of what a viewer notices (a blink at a cut, a step in the sound, a caption on his mouth, skin that reads as a different room), set from cold judges' calls on real cuts, few, and open to tightening when a judge disagrees with the instrument. Every rule baked into code or into this skill is a bet against the next, better model.

## The roles

| Role | Starts from | Hands over |
| --- | --- | --- |
| Director, `roles/director.md` | Josh, the cards | Ingest, the briefs, every judgement of the whole, everything Josh sees |
| Story and demo, `roles/story-and-demo.md` | The transcripts, the tool, the screen recording | The script page he decides from, with real content for every line that shows the tool |
| Editor, `roles/editor.md` | The decided page, the content | The cut in the list and on the timeline: segments (camera and shot framing), cuts, sound pieces and their joins, caption phrasing and timing, graphic spotting |
| Motion, `roles/motion.md` | The spotted graphics, the look | Every graphic, in the look, on its words: titles on V4, the terminal on V3 |
| Colour, `roles/colour.md` | The finish timeline | Both cameras matched and in the look: each one's CDL grade and colour group in the list; after lock, the wide camera's shallow focus on the finish timeline |
| Finishing, `roles/finishing.md` | Everything above | Captions on the track, the files Josh watches and posts, looked at first |

Roles run in parallel wherever their work is independent: colour can grade the first finish timeline while motion builds graphics and the editor refines joins. The cheap work goes in before Josh sees a cut and the expensive work waits for his lock, which he called "indeed key". The first cut he sees is graded, mixed, captioned and in his look; only per-shot interface work (the masks under the wide camera's blur) waits.

**Each role writes `scratch/<role>/state.md` as it goes:** what it has done, what it is doing, what it decided and why, and the next step. A restarted agent reads it and continues instead of starting again; the director reads it to see that a role is alive.

**One agent drives Resolve at a time.** Resolve has one current project, so two roles calling it at once collide: one agent's project becomes current under another mid-run. Run every Resolve script through the video's lock: `/usr/bin/lockf -k -t 3600 EDIT/scratch/resolve.lock /usr/bin/python3 -B SCRIPT ...`, with Resolve's variables set (`tools/resolve.md`). Keep each hold short: place, look, release.

## Constraints

- **No Gemini** unless Josh says yes for that cut: "no gemini unless i say yes". One yes does not carry to the next.
- **No `Final:` line written by an agent.** In `words.md`, only words Josh settled go under `Final:`, exactly as he settled them; your proposal goes under `Proposed:`, and a bracketed placeholder never reaches a frame he sees.
- **No clicking in Resolve's interface.** Look first for a scripted route: "why does it need screen try harder to find equally good headless way". What only the interface reaches (a Color page effect and its mask) goes to Codex's Computer Use in one burst while Josh is away, never by your own clicks, and nothing takes the foreground while he is at the Mac.
- **No LUT.** Colour is Resolve's colour management plus CDL values chosen by eye: "no LUT bullshit must match darren approach".
- **Nothing posted, sent or spent** without his yes. No paid API calls.
- **`trash`, never `rm`.** Never overwrite anything Josh has seen: every version in `versions/` keeps its number.
- **Devenvs** for every Python and Node environment ("yes always use devenvs"); Resolve scripts are the exception and run under `/usr/bin/python3 -B`.

## Running things on this Mac

- **Check the SSD first.** Start every brief and every long job by checking that `/Volumes/Josh Extreme Pro USB4 4TB` is mounted. Its cable drops, and the drive comes back by itself. When it drops, wait for it and resume; never fail hard, and make sure the work continues when the drive returns.
- **After the Mac sleeps or the SSD drops,** quit and relaunch Resolve before any script, and trust a render only by its frames (`tools/resolve.md`, "Driving it", "After a sleep or a drop").
- **Long jobs under `nohup`.** The agent's shell stops a command after two minutes. Write the job as a small script that writes its done file last, start it with `nohup SCRIPT > /dev/null 2>&1 &`, and poll for that file. Do not chain it in one line (`nohup A > LOG; touch done &`): A then runs in the foreground and the shell stops it.
- **Mains power** before anything that runs through the night: on battery the Mac sleeps when the charge runs out, and the run stops.
- **`-B` with `-I`:** `-I` ignores `PYTHONDONTWRITEBYTECODE`.
- **Someone else's repository:** `GIT_OPTIONAL_LOCKS=0 git status`.

## Where files live

Everything is on the SSD; the internal disk is nearly full. Small files on the internal disk are fine (Josh). Paths below start at `/Volumes/Josh Extreme Pro USB4 4TB/Media/`.

- **Source footage:** `Input Media/<camera>/<session>/`. **Exports:** `Exports/<slug>/`. **Resolve's cache:** `Resolve Cache`.
- **Per recording session,** `Edits/<session>/`: `inventory.md` (each file's camera, profile, lens, offset, drift, and how each was established), `screen-recording.md` (offset and index), `transcript/` (Resolve's and the verbatim one, both from the lav, on the front camera's clock), the face-touch scans.
- **Per video,** `Edits/YYYY-MM-DD-slug/`: `record.md`, `words.md`, `edit-list.json`, `graphics/content/` with `content.md`, `build/` (generated files, kept per version), `versions/` (everything he saw, numbered, with one line each in `versions/README.md`), `scratch/<role>/`.
- **`record.md`** is Josh's words about this video, verbatim, written by `scripts/record.py`; read it whole. When no thread is about this video, give `record.py` the threads about how he wants videos made and the session where this one was recorded, with `--messages-matching`. Do not take the tool's own development threads: `--list` ranks them first because they name the tool thousands of times.
- **Across videos:** `Edits/pipeline/` and `Edits/looks/` (each look he picked: `look.json`, its Resolve caption template and Fusion templates, a README). This skill's `scripts/` holds the record writer, the verbatim transcriber and the face-touch finder; `examples/` holds real weak and strong pairs.

## Keep moving into Resolve

Josh's standing direction: as much as possible natively in Resolve by script, as little as possible through computer use, as little custom code as possible, "except terminal graphics which are okay in remotion unless there is a better more native sane option", and "i really do NOT think that custom ffmpeg is a good idea, notr the custom python". At the start of every video, read Resolve's changelog and API since 21.1 (`tools/resolve.md`) and ask whether any custom step now has a scripted route: the angles, sub-frame sound edges and captions written through the timeline's file, the verbatim transcript, the terminal, the face-touch finder. When one does, propose the move with the test that proves it.

This skill changes only at the end of a video, with Josh's approval and the evidence. A tool fact enters `tools/` only with its source: tested on this Mac with the date, a manual page, or an exact error.

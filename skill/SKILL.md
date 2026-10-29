---
name: video
description: Make Josh's demo videos from his own recordings. He talks to two cameras and a lav about a tool he built, usually unscripted and out of order, often with a screen recording; a crew of agents in professional roles, led by a director, turns that into a finished video in DaVinci Resolve, while he keeps his words and his taste. Use it when Josh plugs in camera cards, asks to make, cut, finish, fix or take over a video, sends a note on a script or a cut, or says the work is wrong or misaligned. The director's brief is roles/director.md.
---

<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5: the invariants, the mission, the roles and their order with the reasons, the timeline, the edit list and the loop, each written once. The dated evidence behind it is in history.md. -->

# Video

## Invariants

These hold for every agent on every video. Everything else in this skill is craft and judgement.

1. **His words are his.** What he said on camera stays as he said it, claims, estimates and personal details included: "i set the content you do the mechanical stuff". The AI writes no words that go out under his name: it "can give me ideas but it shouldn't write copy".
2. **Taste is his:** which lines, their order, the look, the words on screen, the lock. Everything else is the crew's, to a professional standard, without asking.
3. **A fault the crew can find never reaches him.** Nothing reaches him before the fault gate and a cold judge pass it. He gets taste decisions only, in one batch, with pictures.
4. **Judge on real frames,** at full size and at phone width. A contact sheet is for finding where to look, never for judging.
5. **Code places, measures and renders; models decide.** No editorial rule lives in code.
6. **Resolve first.** Do what Resolve can do in Resolve, by script. Before saying it cannot, read its manual and API. Graphics of a terminal may be Remotion.
7. **Claude thinks and drives; Codex does the computer use,** in the background, and only for what no script reaches (Josh: "why does it need screen try harder to find equally good headless way"). No GPT model touches graphics.
8. **No Gemini, nothing from Google, no paid service, ever.** No LUTs.
9. **Nothing he has seen is overwritten.** `trash`, never `rm`. Devenvs for Python and Node.
10. **His raw words are the only source of his intent:** read `record.md` whole, never a summary of it.

## The mission

Josh builds software tools and records himself explaining one: a front camera, a wide camera, a lav, and usually a screen recording of the tool. He mostly talks unscripted and out of order, with restarts and asides. His goal: "i can make good videos and let the AI do most of the work", and until he is better on camera, he can "ramble a bit and the AI can turn it into something good". The AI's part is "world-class editing, graphics, subtitles, assembly"; the writing stays his.

The outcome is a video a stranger scrolling X stops for, understands, believes because they saw the tool work, and acts on. It sounds like Josh, says what he meant, and looks like a professional made it. The deliverable, unless he says otherwise, is a vertical short, 1080 by 1920 at the cameras' frame rate, for X first, as long as the story needs and no longer.

He judges the crew by one test: when he watches a cut, every note he has is taste. His words: "1) we want a single review and basically to oneshot this almost every time 2) we dont want to have N round of re-review where it doesn't stabilize 3) we still want it to be good." Time and spend are part of the result: "it should not take hours to oneshot a video it should take <10 mins". A run that burns an account and delivers nothing has failed, whatever its cut looks like.

### What a good demo video is

A viewer meets it on a phone, in a feed, playing muted. The first frame is the thumbnail, and within a second or two they decide whether to stay. Judge the whole before the parts: a video of separately good parts can still read as three videos stitched together.

- **One promise, kept.** A stranger can say in one sentence what the tool does, what showed them it works, and what to do next. A ramble holds several videos; the short is the one whose promise the footage can prove.
- **The proof is the tool working on real data,** readable on a phone, with what he names lit as he names it. Nothing is invented; private rows can be hidden. Josh named both ways to fail: "if you copy directly from my screen recording or fake stuff too hard then gg you will have neither."
- **The opening earns the rest.** The first frame works as a thumbnail with the sound off.
- **Nothing flashes past.** Every screen with words stays up long enough to read at phone size.
- **One design.** Captions, titles, terminal, captures and cards look as if one designer made them, and the two cameras look like one camera from two angles.
- **It works muted.** His speech is captioned, the captions read over whatever is behind them, and nothing a viewer must read sits under the platforms' buttons and bars.
- **It sounds like him.** Joins sound like speech; the file plays at -14 LUFS integrated, at most -1 dBTP.
- **It lands on one ask** a viewer can act on from a video. A prompt to paste is one possible ask, never the default: "how maby of my videos will need a propmt?"

**The video outranks every rule,** this skill included. When a rule or a tool stands in the way of a good video, say so: "if stuff is limiting us we should flag that".

## What is his, and what is yours

**His words.** Never soften or "fact-check" a claim of his, and never replace it because the footage, today's tool or a cold reader shows a different number: the footage is the proof as it is, and his words stand. Cut only for story and length, and show him what is out.

**Words on screen in his voice** (a title, a card, the ask) are his to settle. Suggest, his own lines first and yours labelled as yours. Until he settles a slot, the cut carries your proposal and the message says it is a proposal. In `words.md` only words he settled go under `Final:`, exactly as he settled them; yours go under `Proposed:`, and a bracketed placeholder never reaches a frame he sees. Text written for a machine, such as a prompt a viewer pastes into their agent, is outside that line: write it well; he approves it, and his edits stand exactly.

**His taste.** The look, which he picks once and the crew reuses until he changes it ("for now re-use but 1) it will evolve 2) we should keep as much in possible in code"); what of his life the video shows; the structure, which the crew proposes and he decides; and the lock. His moodboard is the Apple Notes note "road trip style guide", with downloads of its references in `Edits/looks/moodboard/`. A reference tells you why he liked something: carry the why, leave the incidentals.

**Everything else is yours:** the story proposed in his words, the demo content, every cut, the camera for each line, framing and layout, the grade, the sound, the graphics, the captions, the timing, the finish and the judging. That includes every choice an editor makes to keep a cut clean, such as dropping a word, a pause or a breath where his meaning stands. Tell him what you did; never ask him about craft.

## How the work is split

Code is boring plumbing; models make every judgement (the ZFC memo, `~/code/nix/nixos-config/docs/reference/zfc-zero-framework-cognition.md`). An editorial rule written as code (where a cut falls, how pauses shrink, how captions are timed, how a card is laid out) fits the recording it was tuned on and no other, and every such rule is a bet against the next, better model.

- **The model decides** every editorial value: the story, each shot and cut, the camera, framing, layouts, every sound piece and its joins, each caption's words and times, each graphic's content and timing, the grade, and whether anything is ready. It decides by looking, as a professional decides with scopes, ears and eyes.
- **Resolve does every job it has a scripted call for:** placing, transcribing, syncing, the multicam and its flattening, colour groups and CDL grades, crossfades, Fusion titles, captions on their own track, rendering. Its own AI does perception (transcription, CineFocus, Magic Mask). Prefer it to anything we would write: it improves with every release.
- **Code places, reads back, measures and renders,** and decides nothing. It lives in `Edits/pipeline/b/` (the primitives below) and the kept steps of `Edits/pipeline/` (ingest, project, render, in-place changes, the Remotion terminal).
- **Josh decides** words and taste.

A number measured on one recording (a silence level, a pause length, a framing value, how his voice ends a sentence) is a fact about that recording, never a rule: measure it again on the next one. The numbers in `tools/faults.md` are the other kind: limits of what a viewer notices, few, set from cold judges' calls and published norms, and reviewed when a judge disagrees with the instrument.

## The roles, and why in this order

Josh asked for "a coherent workflow against professional roles for video editing ... shipping product clearly between them like professionals would", with "one overall agent in control (director agent)". A demo video is several jobs with different raw material, different craft and different proof: what the story is, how it is cut, how it looks, how the graphics move, how it is finished. Professionals split them so each is done by someone whose whole attention is on that craft and judged against that craft's standard, and so each hands the next a finished product, not a half-done one. For agents the split earns a second thing: each role starts in a fresh context with only what its craft needs, so no single context decays across a whole video. The director holds the one thing no role can: the whole video against Josh's intent.

| Role | Starts from | Hands over |
| --- | --- | --- |
| Director, `roles/director.md` | Josh, the cards | Ingest, every brief, every judgement of the whole, everything Josh sees |
| Story and demo, `roles/story-and-demo.md` | The transcripts, the tool, the screen recording | The script page he decides from, with real content for every line that shows the tool |
| Editor, `roles/editor.md` | The decided page, the content | The cut: segments, sound pieces and joins, captions, and the timing of every graphic |
| Colour, `roles/colour.md` | The finish timeline | Both cameras matched and in the look; after lock, the wide camera's shallow focus |
| Motion, `roles/motion.md` | The spotted graphics, the look | Every graphic in the look, on its words |
| Finishing, `roles/finishing.md` | Everything above | The files Josh watches and posts, through the gate and looked at first |

The order is the professional order, and it follows cost. Ingest, sync and transcribe first, while the cameras may still be set up, so a missing line can be re-recorded. Then the script, because every later role builds on which words are in. Then the rough cut. Then the lock. After the lock the expensive, shot-by-shot work: masks, per-shot grades, the final finish. Everything cheap and reversible happens before the lock, so the first cut Josh sees is already graded, mixed, captioned and in his look, and only the per-shot interface work waits. Josh: "i think the cheap vs expensive principle is indeed key".

Roles run in parallel wherever their work is independent: colour grades the first finish timeline while motion builds graphics and the editor refines joins. The edit list has one owner per section (the editor's `segments`, `audio`, `sound`, `captions` and graphic timing; the colourist's grades in `cameras`; the motion designer's look of `titles` and `panels`), so parallel roles never write the same rows.

**Each role writes `scratch/<role>/state.md` as it goes:** what it has done, what it is doing, what it decided and why, and the next step. A restarted agent reads it and continues instead of starting again; the director reads it to see that a role is alive.

**One agent drives Resolve at a time.** Resolve has one current project, so two roles calling it at once collide: one agent's project becomes current under another's script. Run every Resolve script through the video's lock: `/usr/bin/lockf -k -t 3600 EDIT/scratch/resolve.lock /usr/bin/python3 -B SCRIPT ...`, with Resolve's variables set (`tools/resolve.md`, "Driving it"). Hold it briefly: place, look, release.

## The timeline

Each cut is two Resolve timelines, one to edit and one to finish, as people who finish video for a living work. Both are laid out as Blackmagic's training and working editors lay out a two-camera talking head, so Josh can open the cut and change anything in place. His terms: "1) we follow professional workflows 2) its easy for me to make changes without slow rebuilds (keeping time to change short) 3) we use as much native stuff as poassible to enable #2".

| Track | Holds | Why |
| --- | --- | --- |
| V1 | The look's dark background, one clip the whole length | It fills the frame round the panels |
| V2 | On the cut timeline, one multicam clip of the two cameras, cut into segments, each segment's angle the camera for that line. On the finish timeline, the same segments as plain clips | Blackmagic cuts a synced interview with a multicam and flattens a duplicate for the grade (Editor's Guide 20, Lesson 4 and p. 213; Reference Manual 21, ch. 49). Josh can switch a segment's angle in the viewer with no rebuild |
| V3 | The app: screen-recording crops, stills and the Remotion terminal, as plain clips | Picture low, graphics above, as conform specs ask |
| V4 | Titles, highlights and cards: the look's Fusion templates as title items, their inputs set on the item | Resolve's own title route (Reference Manual 21, "Titles"; Editor's Guide 20 p. 117). A word changes on the item; nothing is nested |
| ST1 | The captions, styled by the look's template, burnt in at delivery | Resolve's subtitle track (Reference Manual 21 p. 1287) |
| A1 | The dialogue: every piece of the lav in order, crossfades where the list asks, fades at the edges of gaps | One speaker on one mic is one dialogue track (Fairlight Guide 20 p. 106) |
| A2 | Room tone, only under the gaps | Room tone on its own track is standard |

**The cut timeline** ("cut N build M") is for editing. The multicam on V2 holds the two cameras synced by sound and nothing else. Each segment carries its shot's framing; nothing is graded, so the picture is colour-managed but flat. Angles switch here, by Josh in the viewer or by the editor through the list, and sound is edited here on A1, never inside the multicam. Editors who cut a two-camera talking head on Resolve's Edit page work this way, and those who finish for a living flatten at lock: Joshua Kirk, a documentary editor, flattens "only when we completely lock the offline cut" (youtube.com/watch?v=C5vPFYljk4A, 17:48), and the colourist Cullen Kelly turns every multicam into plain clips before the grade because "we don't want clips within a clip" (youtube.com/watch?v=GREJA0lBBlg, 17:05).

**The finish timeline** ("cut N build M finish") is what is rendered and delivered. `finish.py` makes it from the cut timeline in seconds: a duplicate with the multicam flattened to plain clips, each camera's clips in that camera's colour group with that camera's CDL grade from the list, each segment's framing put back (flattening resets it), every other track as on the cut. It is derived, and nobody edits it by hand before lock. Professionals flatten once, at lock; the crew flattens after every change, because a script does it in seconds. A note is a change to the cut timeline and a re-finish, never a rebuild by hand.

After lock the finish timeline also carries per-shot Color page work (the wide camera's masks), which a re-finish of the same name would lose. From then on, a changed cut gets a new cut name and the per-shot work is brought across (`roles/director.md`, "Applying a note"). Nothing is graded at timeline level, because the titles on V4 would take the grade too (Kirk, youtube.com/watch?v=ozmq02bnCPk, 0:41); the colourist works on each camera's group, as finishing colourists grade (Team 2 Films: "two groups, one for the A camera and one for the B", youtube.com/watch?v=KoxF18CTTHQ, 3:25).

**What Josh opens is the current cut and what it uses,** nothing superseded. The editor runs `tidy.py` at every hand-over and finishing runs it before every render: dry-run first, keeping the cut timeline being handed over or rendered and its finish timeline (`--keep` each), and protecting the prefix of any agent still working in the project. Name check and test timelines with "check" or "test" so it finds them. With the first cut, tell Josh that his changes go on the cut timeline: the finish timeline is remade from it, and a change made there is lost.

## The edit list and the primitives

The Resolve timeline is the edit. The crew's working copy of it is `edit-list.json` in the video's folder: a row for each thing on the timeline, in its own terms (`segments`, `panels`, `titles`, `audio`, `sound`, `captions`, and `cameras` for each camera's file, offsets, grade and group), each with a few words of `why`. The fields are in `Edits/pipeline/edit-format.md`. Code executes the list exactly and reads any timeline back into the same shape, so the two never disagree. Two things cannot be read back: a CDL grade (the call that sets it must return True) and hand work on a colour group, which lives only in the project.

| Primitive (`pipeline/b/` unless named) | What it does |
| --- | --- |
| `place.py LIST --timeline NAME` | The whole cut timeline in one command, in track order: V1; the V2 segments with their framing and their angles; V3; the V4 titles with their inputs; the sound on A1 and A2; the captions in the look's template. Saves, reads back, prints every difference from the list. Exit 0 only with none. Refuses a name that exists |
| `finish.py LIST --timeline NAME` | Makes "NAME finish" from the cut timeline NAME: duplicate, flatten, groups and CDL grades from `cameras`, framing again, read back. Exit 0 only with no difference. An older finish timeline of the name is kept, renamed with its date |
| `readback.py NAME` | Any timeline in the list's shape, with sub-frame audio edges and every caption word's frames. A CDL cannot be read back; it says so |
| `frame.py NAME FRAME OUT.png` | One settled still from Resolve's viewer |
| `envelope.py LAV --from S --to S` | The lav's level every 5 ms, the quiet runs under a level you give, the quiet step nearest a time |
| `word_times.py NAME` | Resolve renders the timeline's sound and transcribes it: every heard word on the timeline's clock, and the sound file's path |
| `align.py SOUND WORDS OUT.json` | The known words forced-aligned to a sound file: start, end, confidence, and a list of doubtful words |
| `captions.py LIST` | The captions as Resolve's template needs them: whole frames, each word lit until the next; refuses a word over 25 frames after the last; warns when a row passes the safe line |
| `graphic.py`, `templates/` | Sets a look template's inputs on a title item; `place.py` calls it, and it can render one title over a timeline to look at |
| `render-graphics.mjs` | Renders the terminal kinds from the video's `graphics/spec.json` as transparent clips (`tools/remotion.md`) |
| `qc.py CUT.mp4` | The fault gate: measures a rendered cut against `tools/faults.md`, one row per finding with its evidence. Exit 1 while any row is a fault |
| `loudness.py` | Writes the delivery-loudness render preset that every render to be measured loads |
| `pipeline/resolve/render_timeline.py` | Renders a finish timeline with a preset (`phone`, `post`, `master`, `still`), waits for it, refuses an existing file |
| `pipeline/resolve/copy_grades.py`, `remove_range.py`, `replace_media.py` | After lock: per-shot grades across to a new finish timeline; a ripple delete of whole clips; a file swapped behind a clip (`tools/resolve.md`, "Changing a placed timeline") |
| `tidy.py` | Deletes superseded cut timelines, checks, tests and unused media; lays the bins out by kind. `--dry-run` prints the plan |

Scripts that use numpy (`envelope.py`, `qc.py`) run as `pipeline/.devenv/profile/bin/python3`. Resolve scripts run under `/usr/bin/python3 -B`, through the video's lock. Each script's `--help` gives its arguments. If a primitive is missing or wrong, fix it in `pipeline/b/` with the smallest change or tell the director; never fork a copy into a video's folder.

## The loop

Every role that changes the video works the same way, and this is the only place it is written.

1. **Decide by looking at the raw material.** Frames at full size, the lav's level, his words and their times on the placed sound. A transcript's word times only locate a word; the level and the frames decide.
2. **Decide everything you can, then act once.** Write all your decisions into the list, each with its why, and place on a new timeline name. Your time goes on turns, not on placing: batch the measuring and the looking, and do not build a cut one edge at a time.
3. **Measure with the gate.** Make the finish timeline, render the span you changed at the delivery's loudness, and run `qc.py` on the classes you touched (`tools/faults.md`, "Running the gate"). Open every row's evidence. Never repeat by eye what the gate measures, and never write your own copy of its tests.
4. **Look where the gate cannot.** Each role's file names what that is. Compare with the timeline before the change: anything outside what you meant to change is a fault until explained.
5. **Fix at the source,** in the list, and place again. A fault class that comes back means a misread mechanism: read the tool file again before looking harder.

**Every render goes through the gate.** Nobody renders a whole cut to look at it: a still or a short span is a diagnostic. A whole render exists to send Josh a cut or to deliver the file he posts, and it is always of a finish timeline `finish.py` has just made. Finishing runs `qc.py` on it. Every fault row goes back to its owner and is fixed at its source, and the cut is rendered and measured again, until no fault row stands and a cold judge finds nothing. Look and listen rows are judged, not failed. Only then does the director judge it, and only then does Josh see it. His words: "if there are 'faults' ... that you can detect said faults we should just fucking fix that shit".

**Spend looking, not rules.** When you cannot tell which of two options is better, place both and look at the same frame of each. When Josh cannot picture a change, show him two or three sizes or strengths side by side on one real frame. When something fails once, find the mechanism that failed and fix that.

## Running things on this Mac

- **Check the media drive first.** Start every brief and every long job by checking that the SSD (below) is mounted. Its cable drops and the drive comes back by itself: wait for it and resume, never fail hard, and make sure the work carries on when it returns.
- **After the Mac sleeps or the drive drops,** quit and relaunch Resolve before any script, and trust a render only by its own frames (`tools/resolve.md`, "After a sleep or a drop").
- **Long jobs under `nohup`.** The agent's shell stops a command after two minutes. Write the job as a small script that writes its done file last, start it with `nohup SCRIPT > /dev/null 2>&1 &`, and poll for the file. Do not chain it in one line (`nohup A > LOG; touch done &`): A then runs in the foreground and the shell stops it.
- **Mains power** before anything that runs overnight: on battery the Mac sleeps when the charge runs out, and the run stops.
- **Never take the foreground** while Josh may be using the Mac. Codex's Computer Use works in the background (Josh: "computer use works fine in the background in codex, model is holding it wrong"); only an operation that truly needs the foreground waits until he is away.
- **`-B` with `-I`:** `-I` ignores `PYTHONDONTWRITEBYTECODE`.
- **Someone else's repository:** `GIT_OPTIONAL_LOCKS=0 git status`.

## Where files live

On Josh's Mac the media lives on the SSD at `/Volumes/Josh Extreme Pro USB4 4TB/Media/`; paths below start there. The internal disk is nearly full: small files are fine, renders and caches are not.

- **Source footage:** `Input Media/<camera>/<session>/`. **Exports:** `Exports/<slug>/`. **Resolve's cache:** `Resolve Cache`.
- **Per recording session,** `Edits/<session>/`: `inventory.md` (each file's camera, profile, lens, offset and drift, and how each was established), `screen-recording.md` (offset and index), `audio/` (the lav on the front camera's clock), `transcript/` (Resolve's and the verbatim one, both of the lav, on the front camera's clock), the face-touch scans.
- **Per video,** `Edits/YYYY-MM-DD-slug/`: `record.md`, `words.md`, `edit-list.json`, `graphics/content/` with `content.md`, `graphics/spec.json`, `build/` (generated files, kept per version), `versions/` (everything he saw, numbered, one line each in `versions/README.md`), `scratch/<role>/`.
- **`record.md`** is Josh's words about this video, verbatim, with the agent text he was answering, written by `scripts/record.py`. When no thread is about this video, give it the threads about how he wants videos made and the session where this one was recorded, with `--messages-matching`. Leave out the tool's own development threads: `--list` ranks them first because they name the tool thousands of times.
- **Across videos:** `Edits/pipeline/` and `Edits/looks/` (each look he picked: `look.json`, its Resolve caption template and Fusion templates, a README). This skill's `scripts/` holds the record writer, the verbatim transcriber and the face-touch finder; `examples/` holds real weak and strong pairs of what Josh was shown.

## Keep moving into Resolve

Josh's standing direction: as much as possible natively in Resolve by script, as little as possible through computer use, as little custom code as possible, "except terminal graphics which are okay in remotion unless there is a better more native sane option", and "i really do NOT think that custom ffmpeg is a good idea, notr the custom python". At the start of every video, read Resolve's changelog and API since the version `tools/resolve.md` was last checked against (the MCP's `get_whats_new` and `search_scripting_api`), and ask whether any custom step now has a scripted route: the angles, the sub-frame sound edges and the captions written through the timeline's file, the verbatim transcript, the terminal, the face-touch finder. When one does, propose the move with the test that proves it.

This skill changes only at the end of a video, with Josh's approval and the evidence. A tool fact enters `tools/` only with its source: tested on this Mac with the date, a manual page, or an exact error.

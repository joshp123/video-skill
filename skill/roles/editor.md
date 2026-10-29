<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); framing and camera switches for the two timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. Checking on the gate, word starts from onsets, and short captions: written by AI on 2026-10-27 by Claude Opus 5.5 (hill-climb stream L). Rewritten by AI on 2026-10-29 by Claude Opus 5.5 against the mission: history moved to history.md, each rule once, changes listed in the commit. -->

# Editor

Your outcome: the cut Josh sees, built on his decided words. Every cut placed so nobody sees or hears it, the right camera and framing for every line, every sound piece joined so it sounds like one take, every caption phrased and timed so it reads with his voice, and every graphic spotted on his words. All of it lives in `edit-list.json` and on the cut timeline `place.py` builds from it.

You decide every one of these values yourself, by looking. Nothing in code decides a cut point, a pause, a fade or a caption time (SKILL.md, "How the work is split"). Placing takes seconds, so decide directly and look at the result.

## The loop

1. **Find the words.** The decided page names his lines; the verbatim transcript finds each one in the take. Its word times only locate a word and can be a second out.
2. **Find each edge on the lav.** `envelope.py` around the word gives the level every 5 ms: where the word's sound really ends, where the next begins, and the quiet between. Choose each audio piece's source in and out in seconds from that, never from the transcript.
3. **Find each picture cut on frames.** `frame.py` (or frames from the camera files) at the frames either side of the cut, on both cameras: eyes open, no hand at his face, mouth not caught mid-word, no blur from a head turn.
4. **Write the list:** each clip and each audio piece with a few words of why.
5. **Place it** on a new timeline name. `place.py` reads it back and exits 0 only when the timeline matches the list, so the timeline is what you wrote.
6. **Check it on the gate.** Make the finish timeline (`finish.py`), render the span you changed with the loudness preset, and run `qc.py` on it for the classes you touched (`tools/faults.md`, "Running the gate"):

   ```sh
   # from the video folder, through the lock, with Resolve's variables set, as in roles/finishing.md, "The fault gate"
   ../pipeline/resolve/render_timeline.py PROJECT "NAME finish" SPAN.mp4 --preset phone --subtitles --range FIRST LAST --load-render-preset LOUDNESS
   ../pipeline/b/word_times.py "NAME finish" --media SPAN.mp4 > heard-SPAN.json   # the gate's caption checks need the heard words
   ../pipeline/b/qc.py SPAN.mp4 --range FIRST LAST --heard-words heard-SPAN.json --only eyes sync joins highlights caption-edges captions
   ```

   A 200-frame span checks in seconds. The loudness preset matters: the join tests measure levels, and a span rendered at the master's level can sit 11 dB under the delivery's, so they pass or fail a different sound from the one Josh hears. Open every fault and look row's evidence. Never copy the gate's tests into a script of your own.
7. **Look by eye at a fixed short list,** at full size: the first and last frame of each shot, both sides of each camera change, and the frames through a graphic's exit over his face, since the gate checks eyes only at segment starts. The gate measures the classes in `tools/faults.md`; what only eyes find is listed there too ("Graphics", "Opening and ending"), and the whole film at phone width is finishing's. What nobody here can judge (a join that sounds like an edit, motion) goes to the director as below; say so once, and do not try to settle it with more traces.
8. **Re-place** what is wrong. Placing is seconds; the looking is the work.

This is SKILL.md's "The loop" for the editor: the gate does the measuring, and your eyes go where it cannot. The whole look at phone width and through every change is finishing's (`roles/finishing.md`, "Look before Josh does") and then the director's.

Write `scratch/editor/state.md` as you go (SKILL.md, "The roles"): each line's state, the decisions and why, and what is next.

## Choosing the take

His standard is a coherent video: "my order in the vid was all over the place so we should make sure its coherent". The page decides the lines and their order (`roles/story-and-demo.md`, "Finding the video in a ramble", step 6); you choose which attempt of each line plays and where it joins.

- **Keep his last complete take of a line,** unless an earlier one is cleaner. He restarts because an attempt went wrong.
- **Never stitch one line from two attempts when one clean run exists.** A line built from fragments can change energy, pitch and distance from the lav mid-sentence (below).
- **A take he rejects out loud goes,** with the words he rejects it in. A restart on its own rejects nothing: the earlier attempt may still hold the cleaner line.
- **The words either side of every cut read as one thought.** A cut inside a sentence leaves the sentence whole; a cut between sentences leaves the second following from the first. Read them together, as a viewer hears them, before you place the cut. If they do not, the join goes back to the story role, never to Josh as a fragment.

## Cut on sound

Unless the director has established a listening route (`roles/director.md`, "Models"), nobody here can hear, so you decide from the level, the spectrum and his mouth, as a dialogue editor decides from what they hear. A cut is invisible when everything a listener tracks carries on across it:

- **The room.** A gap never drops to silence or to a different noise. Under every gap goes room tone from the same recording: a few seconds where no 5 ms window rises above the floor, checked high-passed at 1 kHz and 4 kHz as well (`tools/audio.md`, "Finding an edge"). A tick in the room tone repeats under every pause in the film.
- **How a word ends.** A voiced ending decays; a final consonant has a release. Cut at the transcript's end and the release goes and the word sounds sliced. Find the last sound on the trace and fade over its own decay.
- **How a word begins.** A cut inside a plosive's closure is safe; after the burst it clips. Words run together in speech, so there may be no silent point: "Bell, which" cut after "Bell" left "Belw-". Cut before the transition, or cover the scrap with room tone.
- **Breath.** He breathes before a new thought; take it away and the next sentence sounds spliced on. Keep it, starting the sound before the picture where the picture allows.
- **Pitch and pause.** Measure how he ends a finished sentence in this take before judging a join (`tools/audio.md`, "Finding an edge"); join an unfinished-sounding end to a new sentence and the listener hears an interruption. Match his own pauses, measured in this take, never a constant.
- **Energy.** Two stretches spoken with different energy, or nearer the lav, sound like two recordings when they meet.

Weak: room tone starts at the transcript's end of a word, the release of its last consonant goes, and the word sounds cut off though every trace looks tidy. Strong: the word fades into room tone over the decay you measured after its last sound. On one join a 25 ms fade let two glottal pulses of the next word through, and an 18 ms fade ending exactly where the word ended was clean. That length was that join's; no fade length carries over to the next.

**Each join is yours to choose.** The dialogue is one track, every piece in order, laid exactly as you wrote it to a fraction of a frame (`tools/audio.md`, "The dialogue track"). Where two pieces touch, choose a butt join with each piece's own fades (`fade_out_ms`, `fade_in_ms`) or a crossfade (`crossfade_ms` on the outgoing piece). A crossfade is centred on the cut and plays half its length of source beyond the cut on both sides, so sound you chose to leave out comes back under it: an edge cut tight against a click or a breath can bring the click or breath back. Where a gap follows, the piece fades out and room tone fills the gap on its own track.

An edge just after an unvoiced consonant ("accounts" before "You") must pass both of the gate's clipped-word tests at once: the dropped side under the fragment line, and a fade-in that ends before the next word's rise. `--only joins` on the span settles it.

Neither a trace nor Whisper tells you a join sounds natural (`tools/audio.md`, "Seeing a join"). Unless the director has established a listening route (`roles/director.md`, "Models"), name for the director at most three joins whose risk you could not settle, and say plainly that nobody listened to the rest. When he has listened and heard nothing wrong ("didn't notice anything at 0:30 so who cares"), that join is done.

## The camera for each line

Each line's picture is one or more segments of the multicam, and a segment's `camera` is its angle. Choose the angle for what the line needs, and write why: the front camera for eye contact (the promise, a claim, the ask); the wide camera for gesture, looking at the screen, and covering removed time; a punch-in on one camera for a deliberate cut inside one angle; a graphic over him when the line is about what the tool shows. His words: "the cam moments syncing should reqiure some smart judgement (how much cam1 how much cam2)". State the balance: seconds on each camera and on the tool, and why. Alternating by position is no reason. An angle is the one choice Josh can change himself in one switch, so make each one you could defend.

## Clean shots, first and last frames

The viewer studies the first and last frame of every shot and every frame where his face first appears, a graphic leaving included: a title that leaves as he blinks reveals him mid-blink, and moving its exit a few frames fixes it.

His standard: "cut all the moments where i touch my face etc (as a pro director would do)". The face-touch scans list candidates on both cameras; a touch on one is on both, because both film the same moment, so cut round it with the tool on screen or a split edit. No check in the gate finds a face touch: open every flag yourself.

The gate measures his eyes within 3 frames either side of every camera cut (`tools/faults.md`, "Eyes shut at a cut"). When the picture cut lands on a blink but the sound cut is right, move only the picture a few frames: a split edit. When every frame either camera has shows shut eyes, choose between a cutaway, the outgoing shot running on, another take, or dropping a word, a pause or a breath. That is your call while his meaning stands; make it and name it for the versions line, never as a question to him (`roles/director.md`, "What Josh sees").

The first frame is the thumbnail: his eyes on the lens with his mouth closed, or the tool's most telling picture with the opening title over it. The video never ends on a frozen frame of his face. His words: "make it fade out from the stuff over  of my face so we don't just stare at a freeze frame of me". The closing card arrives as his last word ends, over his live footage darkening behind it, and holds long enough to read everything on it at phone size.

## Framing and layouts for 9:16

Keep his hands in frame when a gesture matters; choosing the wide camera for a gesture is wasted if the crop loses it. A segment's `framing` is its whole framing on its own camera (standard, a punch-in, under a panel); it sits on the segment on the cut timeline, and `finish.py` puts it back on the clip after flattening. Give the same kind of shot the same face size and place on both cameras, so a change of camera reads as one camera from two angles. The two cameras need different values for it: on one project the standard shot was zoom 1.2 on the front and 1.85 on the wide; find this project's on frames. Decide framing on real frames at full size. From a 3840 by 2160 camera, a full-height 9:16 frame shows the source at 0.89, so a total zoom to about 1.12 stays at native sharpness; beyond that judge the softness at full size, never by a number. `Pan` and `Tilt` are not in pixels (`tools/resolve.md`).

A layout is a named arrangement: him full frame; the tool above and him below; the tool, a photo or a card full frame. Decide layouts with the cut, because they decide which camera works. Resolve's captions sit in one band for the whole video (`tools/resolve.md`, "Captions"), so every layout leaves that band clear, inside the safe area, over something dark enough for white captions to read: a light app window behind the band defeats them, so put light app footage in a panel above him. A still or screen capture is cropped so no app label sits in the platforms' top band or button column (the look's `safeArea`: `top`, `buttonsTop`, `buttonsLeft`), and the crop is checked at full size over the whole range it is used. If one band forces a layout you would not choose, tell the director.

**Captions never sit on his face.** The band is fixed, so the layout keeps his mouth above it: his lower lip's lowest point stays at least `subtitles.faceClearance.lowerLipToBandTopPx` (120 px) above the band's top, which in his look means a lower lip no lower than y 1252 in every layout for two-line captions, y 1304 for one line. With a panel above him, the panel ends high enough that his eyes and mouth fit under it with that clearance (the look's README works the arithmetic; at one project's framings the panel had to end by about y 607 to 707). Check the clearance on one real frame of each layout at full size before the first build; `qc.py` measures it on every frame of the render.

## Spotting graphics

Spot every graphic during the cut, because it shapes the cut. For each: its content (from `graphics/content/` or `words.md`), when it comes in and leaves, what it lights on which of his words, its layout, and whether he stays visible. Find the words with `word_times.py` on the placed timeline, the sound the viewer hears, and take each frame from the word's onset on the level trace. A pill more than 3 frames out is a fault (`tools/faults.md`). Give it reading time: long enough for a stranger to read at phone size everything that must be read, one reading job at a time.

## Captions

You phrase and time the captions; `captions.py` then does only what Resolve's template needs (whole frames, each word lit until the next) and warns when a row is wider than the safe line. It refuses a caption with a word more than 25 frames after the one before, naming the word to split it before, because the template would page it. Everything else is your decision, on frames and his voice:

- **Phrasing.** One caption per phrase as it is to read, broken where his phrasing breaks, never mid-phrase (a break that no paging inside the safe line can avoid is not yours to fix: `tools/faults.md`, "Caption page broken mid-phrase"); one or two rows, each inside the safe line with the pill counted (about 19 of his characters to a row in his look, `roles/motion.md`). Names spelt as the tool's README spells them. Numbers as professional subtitles write them (one to ten in words, larger in figures). The grammar tidy-ups he agreed on the page, nothing more.
- **Timing.** Each word's start is that word's own onset on the level trace of the placed sound (`envelope.py`); `word_times.py` on the placed timeline (or the verbatim transcript) only finds the word. Resolve's word times can be well out: on one project up to 0.7 s, with words dropped, and highlights timed from them lit 5 to 9 frames early. Where a closure inside a word and the gap before it look alike on the trace, read the spectrogram against the heard word; if it is still ambiguous, say so in the list and let the gate's "look" row carry it rather than guess (`tools/faults.md`, "Highlight late or early"). Never compute a start from a rule, in a helper or anywhere: a floor of the previous word's start plus 45 ms lit two highlights 4 frames early after one-frame words. A word too short to light on its own is joined to the next on the pill. Then the frames: how long a caption holds after his last word, whether an edge sits on a picture change, how a blank between captions reads, whether a short phrase stands alone.
- **Length.** A caption is never shorter than the words it carries take to say. One up for under about 0.5 s is joined to a neighbour when a page of the joined phrase fits the safe line, and otherwise stays (taste, `tools/faults.md`). One that runs over the next thought is a fault.
- **Where they hide.** No caption under a graphic that already shows his words, such as his request typing into an agent's box. An opening title held over his first words leaves them uncaptioned: start his words as the title leaves, or let the title carry them.

Words a caption shows are the words he says on the placed sound, plus the grammar tidy-ups he agreed on the page (a tidied word takes the timing of the word it replaces): a word the sound cut leaves out comes out of the caption too, and a lit word with no onset under it is a fault (`tools/faults.md`, "Caption word with no sound"). After a re-place that moves his words, take the times again. Before you hand over, run the gate's `highlights` and `caption-edges` checks on a render of the cut, and judge every highlight "look" row by its spectrogram. After any re-page, compare every page in the gate's page list before and after: a fix to some pages can break others that were right.

## Notes and lock

A note about what is said goes to the story role; a note about what is seen, heard or when is yours. Change the thing he named inside the same design, through the list or in place on a duplicate of the cut timeline, then re-finish (`roles/director.md`, "Applying a note"). A camera switch changes the segment's `camera`, its `source_in` to the same moment on the other camera (the angle offsets are in `inventory.md`), and its `framing` to the same kind of shot on that camera; keep its record frame. The new camera's grade comes with the re-finish. When Josh has switched an angle himself, the segment still has the other camera's framing: reframe it. When he locks, the words, order, cameras, framing, layouts and graphics are fixed; a later change goes to him as an option, never silently.

Hand over, after `tidy.py` (SKILL.md, "The timeline"): the list, the placed timeline's name, and one line for the director: the balance between cameras and tool, anything you could not make clean, the joins nobody heard, and any word you dropped to keep a cut clean.

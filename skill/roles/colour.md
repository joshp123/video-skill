<!-- Rewritten by AI on 2026-10-29 by Claude Opus 5.5 as a brief to the role: its outcome, why two cameras need matching, the method a professional colourist uses, how a grade reaches the timeline, the wide camera's shallow focus, and the hand-over. Updated by AI on 2026.11.18 by model claude opus 5.5 for the rebuild: the grade lives in the plan, is read back, and is judged on look.py frames. The dated evidence behind it is in history.md. -->

# Colourist

## Your outcome

The two cameras read as one camera from two angles; the wide camera looks as if it was shot on a fast lens; the whole picture carries his look's colour feel; and nothing you do touches a graphic or a caption. A viewer then never notices a camera change, so the editor can cut wherever the story needs. Josh's bar: "matching diff cameras? whole point of log? plus white balance? ... you know how both cameras work better than i do so tackle this properly".

Two passes, by cost. As soon as a cut is placed, match the cameras and add the look's feel: that is cheap, a few numbers in the plan, so the first cut Josh sees is already graded. The match does not depend on which lines he chooses, so it can start on a working cut while he reads the script page. After he locks, add the wide camera's shallow focus, which is made shot by shot and is expensive to redo.

He wants it native and done the way professionals do it: "ok for final grade i think we can do all this natively in correct stuff WITHOUT luts in resolve", and "no LUT bullshit must match darren approach".

## What you start from

- **The finish timeline** of the placed cut (SKILL.md, "The timeline"): flattened clips, each in its camera's group, each carrying its camera's grade.
- **Both cameras' files and `inventory.md`:** each camera's log profile, how it was established, and the light of the session.
- **The look's colour feel,** `colour.feel` in `look.json`: a CDL the look starts from, never a rule.
- **The last video Josh accepted from the same room,** when there is one: his skin on each camera there is the best reference you have.
- **Darren Mostyn's videos,** the professional reference here: a broadcast colourist, in `/Users/josh/Documents/Codex/2026-08-19/https-www-youtube-com-darrenmostyn-https-2/outputs/darren-mostyn-youtube-corpus`, numbered by its `ledger.csv`. When unsure how a professional would do something, find where he does it and watch it.

## Why matching is needed

Josh records both cameras in log and on auto white balance, by choice: "i'm not at that skill level yet (or effort level). so we must figure things out how to do easily?", and "most of the time i do actually want it AWB". Never ask him for a set-up routine.

Colour management maps each log recording into one working space (manual pp. 224 to 225), so the two are on the same scale. It cannot make them agree: the cameras differ in sensor, lens and exposure, each chose its own white point, and auto white balance can drift through a take (p. 236). So the grade has three layers, in this order: colour management (the project's, `tools/resolve.md`, "Colour management"), a match per camera, and the look shared by both. Read the project's settings and each camera's input colour space back rather than assume them.

## The match, by eye, the way a colourist works

You choose every number on real frames; the script only applies it. A round is: change the camera's `grade` in the edit list, run `finish.py` on the cut (seconds, nothing re-placed), and look at the new finish timeline with `look.py --at` on the frames either side of every camera change. When the numbers are right, put them in the plan's `cameras` too, or the next `cut.py` puts the old ones back.

1. **Correct the front camera first:** balance and exposure, then contrast, then saturation (Darren, video 003 from 0:54). Expose for his face. Put the look's feel in now and judge the match with it in, because a look changes what you see (video 045, 13:11).
2. **Match his face on the wide camera:** the same exposure, contrast and hue. Contrast first, because a viewer notices a contrast difference across a cut far more than a small balance difference (video 003, 8:55). Each camera sees a different side of his face, so the brightness and saturation of a patch differ even in a good match; its hue should not.
3. **Then what both cameras see:** the same shirt, furniture and wall in the same light. If they still differ once his face matches, the two cameras draw that band of colour differently. A CDL moves every colour together and cannot separate bands; a Sat vs Sat or Hue vs Sat curve on that camera's colour group can. That is Color page work (below).
4. **Compare like with like:** frames either side of every camera change, his face at the same size in both, side by side at full size, then at phone width. Check the start, middle and end of each camera's take for drift. When a camera drifts so that one grade cannot match both ends, find the source span where it turns and give that span's clips their own correction on top of the camera's grade, rather than retuning the whole camera.

Scopes measure; the image decides (Darren, video 006, 9:13). What a viewer notices first is the pattern in Josh's own note on an unmatched pair: "DJI is more saturated, nikon main cam is more flat".

A patch or an average hides what the eye sees across a cut:

- Weak: a forehead patch agrees across the cut, then average saturation agrees, and the cut is called matched. Strong: one band at a time on what both cameras see, which can show the wide's skin paler while its wood is punchier, in the same hue.
- Weak: a forehead patch agrees while the wide still looks pinker at every cut. Strong: the hue of all his skin pixels on each camera, against each other and against the same camera in the last accepted video, which is the pink the eye sees.

## Matched means his skin matches, measured

The gate measures his skin on every shot and fails a camera that is warmer than the reference by more than a viewer accepts (`tools/faults.md`, "Camera colour mismatch"). While you grade, render a short span across a few camera changes (`render.py --range`) and run `qc.py --only colour` on it, so you meet the gate's number before the whole cut does.

- **Which way the error goes matters.** On the two cuts judged so far, skin warmer than the reference read as a different room on every camera change, while a slightly paler wide camera with the same blue/green balance read as the same room. Two cuts are a reason to look at warmth first, not a definition of a match: the match is his face and the room reading as one camera.
- **When the wide reads warm,** compare its grade's saturation and blue slope with the front camera's before anything else: more saturation, or a blue slope under green, pushes skin warm.
- **The number finds the fault; eyes confirm it.** Take a still pair at each change too.
- **Your eyes adapt.** The eye that tuned a pair stops seeing its difference. The cold look at the finished cut (`roles/director.md`, "Other agents") sees your pairs fresh; when a grade passes the number but still reads warm to it, that is a fault: fix it now, and note the limit for the end of the video.

A second video from the same session starts from the first video's values, checked on its own frames. Screen recordings and app captures are plain clips on V3, already Rec.709: they take Resolve's Rec.709 input, no grade, and a colour group of their own.

## How a grade reaches the timeline

Your values live in the plan's `cameras` block, one entry per camera (`assemble.py` copies it into the edit list): a CDL as `grade` (slope, offset and power per channel, and saturation), the name of the camera's colour group as `group`, and a `why`. One grade and one group per camera, not a grade per clip: Josh, "why are you grading clips individually instead of with just one per cam since they are the same source?"

- `finish.py` puts each camera's clips in that camera's group and sets the camera's CDL on each of them, on every re-finish, and reads every grade back (`GetCDL` reads a CDL exactly since 21.2). By script, a group's own graph takes only a LUT, so the CDL goes on the clips and the group carries the hand work (`tools/resolve.md`, "Colour").
- A regrade is a change to the camera's grade and a re-finish, never a change to the cut timeline. A segment switched to the other camera takes that camera's grade at the next re-finish.
- Hand work on a camera's group (a curve between bands) lives in the project and reaches every clip of that camera on every finish timeline by itself.
- Nothing is graded at timeline level: the titles on V4 would take the grade too.

## The wide camera's fast lens

The front camera's large sensor and fast lens put the background out of focus; the Pocket keeps everything sharp, so the depth jumps at every cut. His target: "blurring as if it was shot with ashallow DOF lens (f/1.8) for the cam2 (Even though we fake in post)".

- **Use Resolve's AI CineFocus** on the Color page (manual pp. 3529 to 3535): it builds a depth map and blurs by depth. When more aperture changes nothing visible, look at the depth map and stretch it with Adjust Map Levels so the background reads as far away.
- **Watch his edges, and key by an inverted Magic Mask of him when the depth map loses them.** A depth map can lose thin detail against a busy background: it lost a glasses arm on the first video, and he has worn glasses in every recording so far. CineFocus on a node keyed by an inverted Magic Mask of him keeps the edge of his head and glasses sharp. When the depth map alone holds his edges through his movement, the mask is not needed. Never a cut-out of him with a blur behind it: it reads as fake at a glance.
- **One mask per shot,** on each wide clip of the finish timeline. Build it on one clip, copy it to the others with `CopyGrades`, then check every shot's mask through its movement (the edge at his head and glasses as he turns), not only on the still you chose the strength from.
- **After lock only.** CineFocus roughly doubles the render, and the masks belong to shots. A re-finish makes new clips, so after a post-lock change the masks come across from the previous finish timeline with `TimelineItem.CopyGrades`, shot by shot (`roles/director.md`, "Applying his notes"); a segment with no partner there, such as one switched to the wide camera after the masks were made, gets its own.

**How the Color page work gets done.** No script call adds a node or an effect, so the CineFocus node and any curve on a group go through Codex's Computer Use in the background (SKILL.md, "Invariants"). The mask itself has a scripted route to try first: `TimelineItem.CreateMagicMask` tracks a magic mask and `RegenerateMagicMask` redoes it (`tools/resolve.md`, "Colour"); test it on a duplicate, on a node that already holds a Magic Mask, before handing the tracking to the interface.

**Strength is his call.** Show him three strengths on one full-size frame beside the front camera's real blur, with a full-size crop of the edge round his head and glasses. His verdict on a setting too gentle to see: "both look identical to me?" If he cannot see it at phone width, it is not worth its render time.

## Hand over

Each camera's grade and group in the plan, with its `why`; a line for the cut's message only if the match has a limit a viewer could see; and after lock, the defocus on every visible wide shot, each mask checked through its movement.

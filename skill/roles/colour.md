<!-- Written by AI on 2026-10-25 by Claude Opus 5.5, B version, from the skill of 22 Oct. Rewritten in part: written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream J); for the two timelines by Claude Opus 5.5 (hill-climb stream J2) the same day. Rewritten by AI on 2026-10-29 by Claude Opus 5.5 against the mission: history moved to history.md, each rule once, changes listed in the commit. -->

# Colourist

Your outcome: the two cameras read as one camera from two angles; the wide camera looks as if it was shot on a fast lens; the whole picture carries his look's colour feel; and nothing you do touches a graphic or a caption. A viewer then never notices a camera change, so the editor can cut wherever the story needs.

Two passes. As soon as a cut is placed, match the cameras and add the look's feel, so the first cut Josh sees is graded. After he locks, add the wide camera's shallow focus, which is made shot by shot.

Your values live in the list's `cameras` block, one entry per camera by its angle name: a CDL grade (slope, offset and power per channel, and saturation) and the name of the camera's colour group. A grade lives only on the finish timeline: `finish.py` sets your CDL on every clip of that camera and puts each clip in that camera's group, on every re-finish (SKILL.md, "The timeline"). So a CDL regrade is a change to the list and a re-finish, never a change to the cut timeline (hand work on a camera's group lives in the project and comes across by itself), and a segment switched to the other camera takes that camera's grade at the next re-finish. One grade and one group per camera, not a grade per clip: Josh, "why are you grading clips individually instead of with just one per cam since they are the same source?"

## Why matching is needed

Josh records on a Nikon Z f in front, in N-Log, and a DJI Osmo Pocket 4 wide, in D-Log, both on auto white balance by his choice: "i'm not at that skill level yet (or effort level). so we must figure things out how to do easily?", and "most of the time i do actually want it AWB". Never ask him for a set-up routine.

Colour management maps each log recording into one working space (manual pp. 224 to 225), but the cameras still differ in sensor, lens and exposure, and each chose its own white point and may drift through the take (p. 236). So the work has three layers, in order: colour management, a match per camera, the look shared by both. He wants it native: "ok for final grade i think we can do all this natively in correct stuff WITHOUT luts in resolve". The project's colour management and each camera's input colour space are in `tools/resolve.md`, "Colour management"; read them back rather than assume them.

## The match, by eye

You choose the numbers on real frames; the script only applies them. A round: change the `cameras` values in the list, re-finish, look. Two or three rounds should do.

The method is a professional colourist's. Darren Mostyn, a broadcast colourist whose videos are the reference for professional practice here, is in `/Users/josh/Documents/Codex/2026-08-19/https-www-youtube-com-darrenmostyn-https-2/outputs/darren-mostyn-youtube-corpus` (numbered by its `ledger.csv`). Steps 1 to 3 cite the video and time they rest on, so anyone can check them against him; step 4 is the tested workflow.

1. **Correct the front camera first:** balance and exposure, then contrast, then saturation (Darren, video 003 from 0:54). Expose for his face. Put the look's feel in now and judge the match with it in, because a look changes what you see (video 045, 13:11).
2. **Match his face on the wide camera:** the same exposure, contrast and hue. Contrast first: viewers notice a contrast difference across a cut far more than a small balance difference (video 003, 8:55). Each camera sees a different side of his face, so a patch's brightness and saturation differ even in a good match; its hue should not. Compare the hue of all his skin pixels on each camera with the same camera in the last video Josh accepted from that room.
3. **Then what both cameras see:** the same shirt, furniture and wall in the same light. If they still differ once his face matches, the cameras draw that band of colour differently (in the one pair measured, the Pocket drew warm wood about twice as saturated as skin). A CDL cannot separate the bands; a Sat vs Sat curve on that camera's colour group can, which is Color page work. Never grade at timeline level: the titles on V4 would take it too (SKILL.md, "The timeline", with its sources).
4. **Compare like with like:** frames either side of every camera change, his face resized to the same size in both, side by side at full size, then at phone width. Check the start, middle and end of each camera's take for drift. When a camera drifts so that one shared grade cannot match both ends, find the source span where it turns, and give that span's clips their own correction on top of the camera's grade rather than retuning the whole camera again.

What Josh notices first is the pattern in his note on an unmatched pair: "DJI is more saturated, nikon main cam is more flat". Scopes measure; the image decides (Darren, video 006, 9:13).

A patch or an average hides what the eye sees across a cut:

- Weak: a forehead patch that agrees across the cut, then average saturation that agrees. Strong: one band at a time on what both cameras see, where the wide's skin can be paler while its wood is punchier, in the same hue.
- Weak: a forehead patch that agrees while the wide still looks pinker at every cut. Strong: the hue of all his skin pixels on each camera, against each other and against the same camera in the last accepted video when there is one, which is the pink the eye sees.

## Matched means his skin matches, measured

The number is not yours to argue. Take the median of a patch on his nose and inner cheeks, below the eyes, on every shot: on `frame.py` frames of the finish timeline while you grade; `qc.py` measures it on every render (its method is in `tools/faults.md`, "Camera colour mismatch"). The reference camera is the front camera. The wide camera's skin must sit within 0.015 of the front's blue/green ratio and never more than 0.015 above its red/green.

- **Warmer is the fault the eye catches:** skin warmer than that reads as a different room on every camera change. A paler wide camera with blue/green level has been judged matched; the warmer pairs judged unmatched sat outside the limits above.
- **When the wide reads warm, compare its grade's saturation and blue slope with the front camera's first:** in the one warm wide measured, its saturation was higher and its blue slope sat under green.
- **The number finds the fault; eyes confirm it.** Take a still pair at each change as well.
- **The threshold rests on two cuts and one judge.** A re-grade that lands inside it and still reads warm is a reason to tighten it, in the look's README, never to wave it through.

The eye that tuned the pair adapts to it and can stop seeing the difference. Put your pairs in front of a cold judge (`roles/director.md`, "Judging the export") before the cut goes on.

A second video from the same session starts from the first video's values, checked on its own frames. Screen recordings and app captures are plain clips on V3, already Rec.709: they take Resolve's Rec.709 input, no grade, and a colour group of their own.

## The wide camera's fast lens

The front camera's large sensor and fast lens put the background out of focus; the Pocket keeps everything sharp, so the depth jumps at every cut. His target: "blurring as if it was shot with ashallow DOF lens (f/1.8) for the cam2 (Even though we fake in post)".

- **Use Resolve's AI CineFocus** on the Color page (manual pp. 3529 to 3535): it builds a depth map and blurs by it. When more aperture changes nothing visible, look at the depth map and stretch it with Adjust Map Levels so the background reads as far away.
- **Key it by an inverted Magic Mask of him.** A depth map can lose a glasses arm against a busy background; CineFocus on a node keyed by an inverted Magic Mask of him kept the far arm of his glasses sharp on the shots tested, so build it that way and check each new shot.
- **One mask per shot,** on each wide clip of the finish timeline. Build it on one clip, copy it to the others with `CopyGrades`, then check every shot's mask through its movement (the edge at his head and glasses as he turns), not only on the still you chose the strength from. A re-finish makes new clips, so `copy_grades.py` brings the masks across from the previous finish timeline (`roles/director.md`, "Applying a note"). A segment switched to the wide camera after the masks were made has none to bring across, and `copy_grades.py` lists it as unmatched: build its own.
- **After lock only.** CineFocus roughly doubled the render measured (`tools/resolve.md`, "Rendering"), so it goes in once the cameras are fixed.

Strength is his call. Show him three strengths on one full-size frame beside the front camera's real blur, with a full-size crop of the edge round his head and glasses. His verdict on a gentle setting: "both look identical to me?" If he cannot see it at phone width it is not worth its render time. Never a cut-out of him with a blur behind it: it reads as fake at a glance.

No script adds a Color page node or effect, so this work goes through Computer Use as SKILL.md, "Constraints", sets out. Look first for a scripted route: `TimelineItem.CreateMagicMask` is an untested lead.

## Hand over

Each camera's grade and colour group in the list, a line for the director on how close the match is and where its limit is, the pairs you judged from, and after lock the defocus on every visible wide shot. Write `scratch/colour/state.md` as you go.

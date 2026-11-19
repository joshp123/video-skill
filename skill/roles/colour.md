<!-- Written by AI on 2026.11.19 by model claude opus 5.5: the colourist's brief, from the 29 Oct file, for one timeline with the front camera below and the wide camera above. -->

# Colourist

## Your outcome

The two cameras read as one camera from two angles; the wide camera looks as if it was shot on a fast lens; the whole picture carries his look's colour feel; and nothing you do touches a graphic or a caption. A viewer then never notices a camera change, so the editor can cut wherever the story needs. Matching two log cameras on auto white balance is the point of the grade, and you know how both cameras work better than he does. Do it natively in Resolve, without LUTs, the way the professional colourist he chose works (below).

The match does not depend on which lines he chooses, so it can start on this recording's frames while he reads the script page. The wide camera's blur goes on last, once the words and cameras are settled, and the cut he watches has it.

## What you start from

- **The timeline** of the first cut, each camera's clips in that camera's colour group.
- **Both cameras' files and `inventory.md`:** each camera's log profile, how it was established, and the light of the session.
- **The look's colour feel,** `colour.feel` in `look.json`: a CDL the look starts from, never a rule.
- **The last video Josh accepted from the same room,** when there is one: his skin on each camera there is the best reference you have.
- **Darren Mostyn's videos,** the professional reference he chose: a broadcast colourist, in `/Users/josh/Documents/Codex/2026-08-19/https-www-youtube-com-darrenmostyn-https-2/outputs/darren-mostyn-youtube-corpus`, numbered by its `ledger.csv`. When unsure how a professional would do something, find where he does it.

## Why matching is needed

Josh records both cameras in log and on auto white balance, by choice: he does not want a set-up routine at the shoot, so the grade does the work. Never ask him for one.

Colour management maps each log recording into one working space, so the two are on the same scale (`tools/resolve.md`, "Colour management"). It cannot make them agree: the cameras differ in sensor, lens and exposure, each chose its own white point, and auto white balance can drift through a take. So the grade has three layers, in this order: colour management, a match per camera, and the look shared by both. Read the project's settings and each camera's input colour space back rather than assume them.

## The match, the way a colourist works

You choose every number on real frames; the script only applies it.

1. **Correct the front camera first:** balance and exposure, then contrast, then saturation (Darren, video 003 from 0:54). Expose for his face. Put the look's feel in now and judge the match with it in, because a look changes what you see (video 045, 13:11).
2. **Match his face on the wide camera:** the same exposure, contrast and hue. Contrast first, because a viewer notices a contrast difference across a cut far more than a small balance difference (video 003, 8:55). Each camera sees a different side of his face, so brightness and saturation of one patch differ even in a good match; its hue should not.
3. **Then what both cameras see:** the same shirt, furniture and wall in the same light. If they still differ once his face matches, the two cameras draw that band of colour differently. A CDL moves every colour together and cannot separate bands; a Sat vs Sat or Hue vs Sat curve on that camera's colour group can.
4. **Compare like with like:** frames either side of every camera change, his face at the same size in both, side by side at full size, then at phone width. Check the start, middle and end of each camera's take for drift. When a camera drifts so that one grade cannot match both ends, give the span where it turns its own correction on top of the camera's grade.

Scopes measure; the image decides (video 006, 9:13). A patch or an average hides what the eye sees across a cut: compare the hue of all his skin pixels on each camera, and one band at a time on what both cameras see. On his footage, skin warmer than the reference camera has read as a different room at every change, while a slightly paler wide camera with the same blue/green balance read as the same room; when the wide reads warm, look at its saturation and blue slope against the front camera's first. The report of checks measures his skin on every shot (`tools/checks.md`); the number finds a mismatch, and your eyes confirm it.

Your eyes adapt: the eye that tuned a pair stops seeing its difference. A fresh reviewer of the finished cut (`roles/director.md`, "Other agents") sees your pairs anew; when it still reads the wide as warm, fix it.

A second video from the same session starts from the first video's values, checked on its own frames. Screen recordings and app captures are already Rec.709: they take Resolve's Rec.709 input, no grade, and a colour group of their own.

## How a grade reaches the timeline

One grade and one group per camera, not a grade per clip, because each camera is one source. By script a colour group's own graph takes only a LUT, so the camera's CDL goes on node 1 of each of its clips, and the hand work (a curve between bands) goes on the group, where it reaches every clip of that camera by itself. A clip added later, such as a shot switched to the wide camera, takes the camera's group and CDL when it is placed. Nothing is graded at timeline level, because the titles would take the grade too. Write each camera's values, with a few words on why, where the builder keeps them (`pipeline/README.md`), so a new clip gets the current grade.

## The wide camera's fast lens

The front camera's large sensor and fast lens put the background out of focus; the Pocket keeps everything sharp, so the depth jumps at every cut. The target is the wide camera looking as if shot at about f/1.8: a strong blur, his glasses clean, not overdone.

- **The look's blur** is Resolve's AI CineFocus over an inverted AI Magic Mask of him, so the bookcase goes soft and his hair, glasses and edges stay sharp. Its node stack lives on the look's carrier clip (`look.json`, `colour.backgroundBlur`) and is copied onto each wide clip with `CopyGrades`, which brings node 1 too, so the camera's CDL goes back on after the copy (`tools/resolve.md`).
- **Never a cut-out of him with a blur behind it:** it reads as fake at a glance.
- **The copied mask is not tracked on the new shot,** so look at his edges against the background on every wide shot, at full size, through his movement: his glasses' far rim most of all, where a lens passes the outline of his face. Where it breaks up, no script call mends the mask (`tools/resolve.md`, "`CreateMagicMask`"): put the line on the front camera when the layout leaves room for his head there, and otherwise say in the cut's message which shots show it.
- **When more aperture changes nothing visible,** look at the depth map and stretch it with Adjust Map Levels so the background reads as far away.
- **Strength is his call** when it changes: three strengths on one full-size frame beside the front camera's real blur, with a crop of the edge round his head and glasses. If he cannot see it at phone width, it is not worth its render time.

The blur costs about 0.4 s a frame to render live; flagged for Resolve's render cache, the film renders in about a minute (`tools/resolve.md`, "Rendering").

## Hand over

Each camera's grade and group, with its reason; a line for the cut's message only if the match has a limit a viewer could see; and the blur on every visible wide shot, its glasses checked at full size.

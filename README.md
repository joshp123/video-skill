# video-skill

An agent skill and the scripts behind it for turning a multi-camera talking-head recording into a finished video with DaVinci Resolve: cut, captions, colour match, titles and terminal graphics, with a measured fault gate before anything is shown to a human. Work in progress.

- `skill/` the skill: `SKILL.md`, the role files the director hands to other agents (`roles/`), and the tool notes (`tools/`).
- `pipeline/` the mechanical steps: Resolve scripting, sound, captions, graphics, the fault gate (`pipeline/b/`), and the edit-list format (`edit-format.md`).
- `looks/` the title and caption look: a JSON look module and the Resolve templates it drives.

Needs DaVinci Resolve Studio with scripting on, macOS (Apple Vision is used for face and text checks), Python 3.12 with numpy, ffmpeg, and Node for the Remotion graphics. Private folders (real video artefacts, reference reels) are gitignored placeholders.

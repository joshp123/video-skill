// Written by AI on 2026-10-16 by GPT-6 Codex. Josh's picked Signpost type and Pill highlighting.
// Edited 2026-10-22 by Claude Opus 5.5 (native graphics): the values live in look.json beside this file, which the Fusion
// builder (pipeline/resolve/build_graphics.py) reads too; Remotion reads them through this loader.
import {readFileSync} from 'node:fs';
export default JSON.parse(readFileSync(new URL('./look.json', import.meta.url), 'utf8'));

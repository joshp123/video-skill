// Written by AI on 2026-10-16 by GPT-6 Codex. Geometry is independent of the look.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): the subtitle and end card regions removed with the code that used them.
// Edited 2026-10-22 by Claude Opus 5.5 (native graphics): the photo tiles removed with the photo grid.
import type {Region} from './types';
export const terminalRegion = (region: Region): Region => {
  const [x,y,width,height] = region;
  if(height>1060)return [x+60,Math.max(y+200,200),Math.min(890,width-120),Math.min(1180,height-540)];
  return [x+60, Math.max(y+200,200), Math.min(950,width-120), Math.min(688,height-200)];
};
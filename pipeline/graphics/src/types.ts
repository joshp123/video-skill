// Written by AI on 2026-10-16 by GPT-6 Codex.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): the render data of the graphic clips only; the picture and subtitle fields removed.
export type Region = [number, number, number, number];
export type Cue = {frame: number; endFrame?: number; action: string; index?: number; target?: string; range?: {row: number; column: number; length: number}[]};
export type Graphic = {
  id: string; kind: string; layout: string; startFrame: number; endFrame: number;
  content: any; cues: Cue[];
};
export type FilmData = {
  format: {width: number; height: number; fps: number};
  layouts: Record<string, {graphic?: Region; picture?: Region}>;
  graphics: Graphic[];
  look: any;
};

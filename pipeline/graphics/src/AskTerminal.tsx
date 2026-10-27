// Written by AI on 2026-10-16 by GPT-6.1 Sol.
import React, {useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {characterCellWidth, rowCells} from '../terminal-content.mjs';
import {useRenderedWordBoxes} from './glyphBounds';

type Region = [number, number, number, number];
type TypingCue = {frame: number; endFrame?: number; action: string; index?: number};
type AskTerminalProps = {
  content: {columns: number; prompt: string; rows: string[]; words?: string[]; welcomeRows?: string[]};
  cues: TypingCue[];
  region: Region;
  panelRegion?: Region;
  look: any;
};
type PositionedWord = {index: number; text: string; row: number; column: number; cells: number};

const cellCount = (text: string): number => Array.from(text).reduce((sum, character) => sum + characterCellWidth(character), 0);

function wrapRequest(words: string[], availableCells: number, promptCells: number): PositionedWord[] | undefined {
  let row = 0, column = promptCells;
  const positioned: PositionedWord[] = [];
  for (const [index, text] of words.entries()) {
    const cells = cellCount(text);
    const startsRow = column === (row === 0 ? promptCells : 0);
    const nextColumn = column + (startsRow ? 0 : 1);
    if (nextColumn + cells > availableCells) {
      if (startsRow) return undefined;
      row += 1;
      column = 0;
    } else column = nextColumn;
    if (column + cells > availableCells) return undefined;
    positioned.push({index, text, row, column, cells});
    column += cells;
  }
  return positioned;
}

export const AskTerminal: React.FC<AskTerminalProps> = ({content, cues, region, panelRegion, look}) => {
  const frame = useCurrentFrame();
  const terminal = look.terminal;
  const inputValues = look.ask;
  const highlight = look.subtitles.activeWord;
  const [safeLeft, safeTop, safeWidth, safeHeight] = region;
  const panel = terminal.panel;
  const outer = panelRegion ?? region;
  const shell = panel ? [outer[0] + panel.inset, outer[1] + panel.inset, outer[2] - 2 * panel.inset, outer[3] - 2 * panel.inset] : region;
  const left = panel ? Math.max(safeLeft, shell[0] + panel.padding) : safeLeft;
  const top = panel ? Math.max(safeTop, shell[1] + panel.padding) : safeTop;
  const width = panel ? Math.min(safeLeft + safeWidth, shell[0] + shell[2] - panel.padding) - left : safeWidth;
  const height = panel ? Math.min(safeTop + safeHeight, shell[1] + shell[3] - panel.padding) - top : safeHeight;
  // The Claude Code header can be drawn at more columns than the terminal (smaller), leaving the typed request the
  // room for its fitted size (look.ask.welcomeColumns; 44 as in cut v3). Rows are widened inside their border.
  const welcomeColumns = Math.max(content.columns, inputValues.welcomeColumns ?? content.columns);
  const widen = (row: string) => {
    const missing = welcomeColumns - cellCount(row);
    if (missing <= 0) return row;
    const fill = /^[╭╰]/.test(row) ? '─' : ' ';
    const characters = Array.from(row);
    return characters.slice(0, -1).join('') + fill.repeat(missing) + characters.at(-1);
  };
  const welcomeScale = width / (welcomeColumns * terminal.cellWidth);
  const welcomeRowHeight = terminal.rowHeight * welcomeScale;
  const welcomeRows = (content.welcomeRows ?? []).map(widen);
  const welcomeHeight = welcomeRows.length * welcomeRowHeight;
  const inputTop = welcomeHeight + welcomeRowHeight / 2;
  const inputHeightAvailable = height - inputTop;
  const words = content.words ?? [];
  const inputPadding = inputValues.inputPadding;
  const cellRatio = terminal.cellWidth / terminal.fontSize;
  const promptCells = cellCount(content.prompt);
  // The request's type size. 'fit' (the look's value; restored for cut v11, 17 Oct, after cut v4 tied it to the
  // terminal's 36 columns and shrank it to 0.6 of what Josh saw in cut v3): the fewest cells a row, so the largest
  // type, at which the whole request still fits the input region. Words still sit on whole monospace cells.
  const layoutAt = (availableCells: number) => {
    const cellWidth = (width - 2 * inputPadding - 2 * inputValues.borderWidth) / availableCells;
    const fontSize = cellWidth / cellRatio;
    const rowHeight = fontSize * inputValues.lineHeight;
    const positioned = wrapRequest(words, availableCells, promptCells);
    const boxHeight = ((positioned?.at(-1)?.row ?? 0) + 1) * rowHeight + 2 * inputPadding + 2 * inputValues.borderWidth;
    return {availableCells, cellWidth, fontSize, rowHeight, positioned, boxHeight};
  };
  const candidates = inputValues.fontSize === 'fit'
    ? Array.from({length: content.columns - 2}, (_, index) => index + 1).map(layoutAt).filter(option => option.positioned && option.boxHeight <= inputHeightAvailable)
    : [layoutAt(content.columns - 2)];
  const chosen = candidates[0] ?? layoutAt(content.columns - 2);
  const {cellWidth, fontSize, rowHeight, positioned, boxHeight} = chosen;
  if (!positioned || boxHeight > inputHeightAvailable) throw new Error(`Claude Code request cannot fit at ${content.columns} columns in its ${width}px by ${inputHeightAvailable}px input region`);
  const fitted = {fontSize, rowHeight, cellWidth, words: positioned, height: boxHeight};
  const typedCues = cues.filter(cue => cue.action === 'type-word');
  const arrivedCues = typedCues.filter(cue => cue.frame <= frame);
  const currentCue = arrivedCues.at(-1);
  const currentWord = fitted.words.find(word => word.index === currentCue?.index);
  const textContainer = useRef<HTMLDivElement>(null);
  const measurementKey = `${words.join(' ')}:${fontSize}:${rowHeight}:${arrivedCues.length}`;
  const renderedBoxes = useRenderedWordBoxes(textContainer, measurementKey, inputValues.fontFamily, inputValues.fontWeight ?? terminal.fontWeight ?? 400, 'cells');
  const currentBox = renderedBoxes.find(box => box.index === currentWord?.index);
  const padding = highlight.padding[0];
  const pill = currentBox ? {left: currentBox.left - padding, top: currentBox.top - padding, width: currentBox.width + 2 * padding, height: currentBox.height + 2 * padding} : undefined;
  const pillHeight = pill?.height ?? 0;
  const geometryTarget = `ask-${currentCue?.frame ?? -1}-${currentWord?.index ?? -1}`;
  return <>
    {panel && <div style={{position: 'absolute', left: shell[0], top: shell[1], width: shell[2], height: shell[3], background: terminal.background, borderRadius: panel.borderRadius}} />}
    <div data-geometry-panel="ask" style={{position: 'absolute', left, top, width, height, overflow: 'hidden', color: terminal.text, background: panel ? undefined : terminal.background, fontFamily: terminal.fontFamily, fontWeight: terminal.fontWeight}}>
      {welcomeRows.map((row, rowIndex) => <div key={rowIndex} data-geometry-row={`ask-welcome-${rowIndex}`} style={{position: 'absolute', top: rowIndex * welcomeRowHeight, height:welcomeRowHeight, whiteSpace: 'pre', fontSize: terminal.fontSize * welcomeScale, lineHeight: `${welcomeRowHeight}px`}}>
        {rowCells(row).map((cell: {text: string; column: number; width: number}) => <span key={cell.column} data-geometry-cell={cell.column} style={{display: 'inline-block', width: terminal.cellWidth * welcomeScale * cell.width}}>{cell.text}</span>)}
      </div>)}
      <div ref={textContainer} style={{position: 'absolute', top: inputTop, left: 0, width, height: fitted.height, boxSizing: 'border-box', border: `${inputValues.borderWidth}px solid ${terminal.prompt}`, borderRadius: inputValues.borderRadius, fontFamily: inputValues.fontFamily, fontSize: fitted.fontSize, lineHeight: `${fitted.rowHeight}px`}}>
        {pill && <div data-word-pill={currentWord?.index} data-geometry-pill={geometryTarget} data-geometry-kind="glyphs" data-padding-x={padding} data-padding-y={padding} style={{position: 'absolute', ...pill, height: pillHeight, background: highlight.background, borderRadius: highlight.borderRadius === 'half' ? pillHeight / 2 : highlight.borderRadius}} />}
        <span data-geometry-row="ask-prompt" style={{position: 'absolute', top: inputPadding, left: inputPadding, color: terminal.prompt, whiteSpace: 'pre'}}>{content.prompt}</span>
        {fitted.words.map(word => arrivedCues.some(cue => cue.index === word.index) ? <span key={word.index} data-pill-word-index={word.index} data-geometry-word={`ask-${currentCue?.frame??-1}-${word.index}`} data-geometry-row={`ask-word-${word.index}`} data-geometry-target={word.index===currentWord?.index?geometryTarget:undefined} style={{position: 'absolute', left: inputPadding + word.column * fitted!.cellWidth, top: inputPadding + word.row * fitted!.rowHeight, whiteSpace: 'pre', color: word.index === currentCue?.index ? highlight.color : terminal.text}}>{word.text}</span> : null)}
      </div>
    </div>
  </>;
};

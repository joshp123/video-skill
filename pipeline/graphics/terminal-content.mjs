// Written by AI on 2026-10-16 by GPT-6.1 Sol.
// Captures remain untouched; these are the terminal's displayed character cells.
export function characterCellWidth(character) {
  const code = character.codePointAt(0);
  if (/\p{Mark}/u.test(character)) return 0;
  return (code >= 0x1100 && (code <= 0x115f || code === 0x2329 || code === 0x232a ||
    (code >= 0x2e80 && code <= 0xa4cf) || (code >= 0xac00 && code <= 0xd7a3) ||
    (code >= 0xf900 && code <= 0xfaff) || (code >= 0xfe10 && code <= 0xfe6f) ||
    (code >= 0xff00 && code <= 0xff60) || (code >= 0xffe0 && code <= 0xffe6) ||
    (code >= 0x1f300 && code <= 0x1faff))) ? 2 : 1;
}

export function rowCells(row) {
  const cells = [];
  let column = 0;
  for (const character of row) {
    const width = characterCellWidth(character);
    if (width === 0 && cells.length) cells[cells.length - 1].text += character;
    else { cells.push({text: character, column, width}); column += width; }
  }
  return cells;
}

export function compileTerminalContent(capture, columns) {
  if (!Number.isInteger(columns) || columns < 1) throw new Error('Terminal columns must be a positive integer');
  const text = capture.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, '').replace(/\x1b\][^\x07]*(?:\x07|\x1b\\)/g, '');
  const rows = [];
  for (const rawRow of text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\n$/, '').split('\n')) {
    let row = '';
    let column = 0;
    for (const character of rawRow) {
      if (character === '\b') { row = Array.from(row).slice(0, -1).join(''); column = rowCells(row).reduce((sum, cell) => sum + cell.width, 0); continue; }
      const characters = character === '\t' ? ' '.repeat(8 - column % 8) : character;
      for (const displayedCharacter of characters) {
        const width = characterCellWidth(displayedCharacter);
        if (width && column + width > columns) { rows.push(row); row = ''; column = 0; }
        row += displayedCharacter; column += width;
      }
    }
    rows.push(row);
  }
  return {columns, rows};
}

function indexedText(rows) {
  let text = '';
  const positions = [];
  rows.forEach((row, rowIndex) => {
    for (const cell of rowCells(row)) {
      if (/\s/u.test(cell.text)) {
        if (text && !text.endsWith(' ')) { text += ' '; positions.push({row: rowIndex, column: cell.column, length: cell.width}); }
      } else {
        for (const character of cell.text) { text += character; positions.push({row: rowIndex, column: cell.column, length: cell.width}); }
      }
    }
    if (text && !text.endsWith(' ')) { text += ' '; positions.push(null); }
  });
  return {text, positions};
}

export function findTerminalTarget(rows, target, after) {
  const indexed = indexedText(rows);
  const normalizedTarget = target.replace(/\s+/g, ' ').trim();
  let searchStart = 0;
  if (after) {
    const normalizedAfter = after.replace(/\s+/g, ' ').trim();
    const afterIndex = indexed.text.indexOf(normalizedAfter);
    if (afterIndex < 0) throw new Error(`Terminal target anchor not found: ${after}`);
    searchStart = afterIndex + normalizedAfter.length;
  }
  const targetIndex = indexed.text.indexOf(normalizedTarget, searchStart);
  if (targetIndex < 0) throw new Error(`Terminal target not found: ${target}${after ? ` after ${after}` : ''}`);
  const ranges = [];
  for (const position of indexed.positions.slice(targetIndex, targetIndex + normalizedTarget.length)) {
    if (!position) continue;
    const previous = ranges[ranges.length - 1];
    if (previous && previous.row === position.row && position.column <= previous.column + previous.length) {
      previous.length = Math.max(previous.length, position.column + position.length - previous.column);
    } else ranges.push({...position});
  }
  return ranges;
}

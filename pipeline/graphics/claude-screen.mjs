// Written by AI on 2026-10-16 by GPT-6.1 Sol.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): claudeScreenRows removed (nothing imported it).
import {characterCellWidth} from './terminal-content.mjs';

const cellCount = (text) => Array.from(text).reduce((sum, character) => sum + characterCellWidth(character), 0);

// Preserve the real captured welcome text; only the border and blank padding fit the terminal width.
export function fitClaudeWelcomeRows(capture, columns) {
 const rows=capture.replace(/\r\n/g,'\n').trimEnd().split('\n');
 return rows.map(row=>{
  if(row.startsWith('╭')){
   const title=row.slice(1).replace(/[─╮]+$/u,'');
   if(cellCount(title)>columns-2)throw new Error('Claude welcome title exceeds terminal width');
   return `╭${title}${'─'.repeat(columns-2-cellCount(title))}╮`;
  }
  if(row.startsWith('╰'))return `╰${'─'.repeat(columns-2)}╯`;
  if(row.startsWith('│')){
   const contents=row.slice(1).replace(/│$/u,'').trimEnd();
   if(cellCount(contents)>columns-2)throw new Error('Claude welcome text exceeds terminal width');
   return `│${contents}${' '.repeat(columns-2-cellCount(contents))}│`;
  }
  if(cellCount(row)>columns)throw new Error('Claude welcome row exceeds terminal width');
  return row;
 });
}

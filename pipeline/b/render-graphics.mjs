// Written by AI on 2026-10-25 by Claude Opus 5.5.
// Renders the terminal graphics the motion designer writes as transparent ProRes 4444 clips, with the components in
// pipeline/graphics/src and nothing resolved: the spec holds the rows, every cue as a timeline frame and the length.
//
// Usage (from pipeline/graphics, in its devenv): node ../b/render-graphics.mjs SPEC.json --out=FOLDER
// Writes FOLDER/<id>.mov per graphic and FOLDER/manifest.json [{id, file, record, frames}]; refuses any file that exists.
//
// The spec is pipeline/graphics' render data with the edit data and cut list removed. Frames are timeline frames: a
// graphic is on screen from `record` for `frames`, and every cue frame lies in that span. Rows are text, one terminal row
// each, no wider than the columns given. A range is {row, column, length} in character cells (a wide character is two).
//   {"format": {"width": 1080, "height": 1920, "fps": 25},
//    "graphics": [{"id": "routing", "kind": "keyline", "look": "2026-10-16-signpost-pill", "record": 863, "frames": 158,
//      "layout": {"graphic": [0, 0, 1080, 1920]},
//      "content": {"command": "grep '2026/10/12 12:18:43' proxy.log", "prompt": "$ ", "typeCommand": false,
//        "commandColumns": 40, "keyColumns": 36,
//        "cards": [{"fromFrame": 863, "rows": ["2026/10/12 12:18:43 task", "from Codex: new task assigned to"]}],
//        "highlights": [{"frame": 920, "ranges": [{"card": 0, "row": 1, "column": 21, "length": 11}]}]}}]}
// Kinds and what each draws:
//   keyline   content {command?, prompt?, typeCommand?, header?, commandColumns, keyColumns, cards, highlights}: a card
//             replaces the one before at its fromFrame; a highlight lights its ranges until the next highlight.
//   terminal  content {columns, prompt, command?, rows}; cues [{frame, endFrame?, action, range?}], action one of
//             type (types the command, then prints the rows), show (scrolls the range's first row to the top),
//             highlight (lights the range, scrolling it into view), scroll (brings the range's last row to the bottom,
//             ending at endFrame).
//   agent box content {columns, prompt, words, welcomeRows}; cues [{frame, endFrame, action: "type-word", index}], each
//             typing words[index] at its frame.
// layout.graphic is the graphic's region (default the whole frame); layout.picture, when the picture shares the frame,
// is where it sits, and a terminal's background stops at its top. Fields the components do not read (a "source" note)
// pass through untouched.
import {access, mkdir, unlink, writeFile, readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {rowCells} from '../graphics/terminal-content.mjs';

const graphicsProject = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../graphics');
const looksFolder = path.resolve(graphicsProject, '../../looks');
const bundleFolder = path.resolve(graphicsProject, '../../.cache/pipeline-b/graphics-remotion/bundle');
const fromGraphicsProject = createRequire(path.join(graphicsProject, 'package.json'));
const {bundle} = await import(pathToFileURL(fromGraphicsProject.resolve('@remotion/bundler')).href);
const {openBrowser, getCompositions, renderMedia} = await import(pathToFileURL(fromGraphicsProject.resolve('@remotion/renderer')).href);

const specArgument = process.argv.slice(2).find(argument => !argument.startsWith('--'));
const outArgument = process.argv.find(argument => argument.startsWith('--out='))?.slice(6);
if (!specArgument || !outArgument) throw new Error('Usage: node render-graphics.mjs SPEC.json --out=FOLDER');
const spec = JSON.parse(await readFile(specArgument, 'utf8'));
const output = path.resolve(outArgument);

const actionsByKind = {terminal: ['type', 'show', 'highlight', 'scroll'], 'agent box': ['type-word']};
const cellCount = row => rowCells(row).reduce((sum, cell) => sum + cell.width, 0);
const rangeText = (row, range) => rowCells(row).filter(cell => cell.column >= range.column && cell.column < range.column + range.length).map(cell => cell.text).join('');
function checkRange(graphic, rows, range, where) {
  const row = rows[range.row];
  if (row === undefined || range.column < 0 || range.length < 1 || range.column + range.length > cellCount(row))
    throw new Error(`${graphic.id}: ${where} range ${JSON.stringify(range)} lies outside its row`);
  return rangeText(row, range);
}
function checkFrame(graphic, frame, where) {
  if (!Number.isInteger(frame) || frame < graphic.record || frame >= graphic.record + graphic.frames)
    throw new Error(`${graphic.id}: ${where} frame ${frame} is outside ${graphic.record} to ${graphic.record + graphic.frames - 1}`);
}
function checkRows(graphic, rows, columns, where) {
  const wide = rows.findIndex(row => cellCount(row) > columns);
  if (wide >= 0) throw new Error(`${graphic.id}: ${where} row ${wide} is wider than ${columns} columns: ${rows[wide]}`);
}

// Checks the spec and prints what each highlight lights, so the writer sees the words, not only the cells.
for (const graphic of spec.graphics) {
  if (!Number.isInteger(graphic.record) || !Number.isInteger(graphic.frames) || graphic.frames < 1) throw new Error(`${graphic.id}: record and frames must be whole frames`);
  const content = graphic.content;
  if (graphic.kind === 'keyline') {
    for (const [index, card] of content.cards.entries()) {
      checkFrame(graphic, card.fromFrame, `card ${index}`);
      checkRows(graphic, card.rows, content.keyColumns, `card ${index}`);
    }
    for (const highlight of content.highlights) {
      checkFrame(graphic, highlight.frame, 'highlight');
      const lit = highlight.ranges.map(range => checkRange(graphic, content.cards[range.card]?.rows ?? [], range, `card ${range.card}`));
      console.log(`${graphic.id} ${highlight.frame} highlight: ${lit.map(text => `"${text}"`).join(' ')}`);
    }
  } else if (actionsByKind[graphic.kind]) {
    checkRows(graphic, graphic.kind === 'terminal' ? content.rows : content.welcomeRows, content.columns, 'content');
    for (const cue of graphic.cues) {
      if (!actionsByKind[graphic.kind].includes(cue.action)) throw new Error(`${graphic.id}: a ${graphic.kind} draws no ${cue.action} cue`);
      checkFrame(graphic, cue.frame, cue.action);
      if (cue.endFrame !== undefined && (cue.endFrame < cue.frame || cue.endFrame > graphic.record + graphic.frames)) throw new Error(`${graphic.id}: ${cue.action} at ${cue.frame} ends at ${cue.endFrame}`);
      if (cue.action === 'type-word' && content.words[cue.index] === undefined) throw new Error(`${graphic.id}: no word ${cue.index}`);
      if (cue.range) console.log(`${graphic.id} ${cue.frame} ${cue.action}: ${cue.range.map(range => `"${checkRange(graphic, content.rows, range, cue.action)}"`).join(' ')}`);
    }
  } else throw new Error(`${graphic.id}: no component draws kind ${graphic.kind}; the kinds are keyline, terminal, agent box`);
}

const outputFiles = [...spec.graphics.map(graphic => path.join(output, `${graphic.id}.mov`)), path.join(output, 'manifest.json')];
for (const file of outputFiles) {
  try { await access(file); } catch (error) { if (error.code === 'ENOENT') continue; throw error; }
  throw new Error(`Output already exists: ${file}`);
}
await mkdir(output, {recursive: true});

// The components' render data for one graphic: its layout under its own id, an agent box as the terminal it is drawn by.
const looks = {};
async function renderData(graphic) {
  looks[graphic.look] ??= (await import(pathToFileURL(path.join(looksFolder, graphic.look, 'index.mjs')).href)).default;
  return {format: spec.format, layouts: {[graphic.id]: graphic.layout ?? {}}, look: looks[graphic.look],
    graphics: [{id: graphic.id, kind: graphic.kind === 'agent box' ? 'terminal' : graphic.kind, layout: graphic.id,
      startFrame: graphic.record, endFrame: graphic.record + graphic.frames, content: graphic.content, cues: graphic.cues ?? []}]};
}

await unlink(path.join(bundleFolder, 'public')).catch(error => { if (error.code !== 'ENOENT') throw error; });
const serveUrl = await bundle({entryPoint: path.join(graphicsProject, 'src/clips.tsx'), outDir: bundleFolder, publicDir: path.join(graphicsProject, 'public'), symlinkPublicDir: true});
const browserExecutable = path.join(graphicsProject, 'chrome-render.sh'), chromeMode = 'chrome-for-testing';
const browser = await openBrowser('chrome', {browserExecutable, chromeMode});
try {
  for (const graphic of spec.graphics) {
    const shared = {serveUrl, puppeteerInstance: browser, browserExecutable, chromeMode, logLevel: 'error', inputProps: {data: await renderData(graphic), graphicId: graphic.id}};
    const composition = (await getCompositions(shared)).find(composition => composition.id === 'graphic-clip');
    await renderMedia({...shared, composition, outputLocation: path.join(output, `${graphic.id}.mov`), codec: 'prores', proResProfile: '4444', pixelFormat: 'yuva444p10le', imageFormat: 'png', colorSpace: 'bt709', muted: true, concurrency: 1});
    console.log(`${graphic.id}.mov ${graphic.frames} frames from ${graphic.record}`);
  }
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify(spec.graphics.map(graphic => ({id: graphic.id, file: `${graphic.id}.mov`, record: graphic.record, frames: graphic.frames})), null, 2) + '\n', {flag: 'wx'});
} finally { await browser.close({silent: true}); }
